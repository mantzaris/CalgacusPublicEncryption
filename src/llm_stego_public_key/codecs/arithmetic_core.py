"""Independent finite integer arithmetic implementation of the NLS mapping idea.

No upstream code copied (its inspected revision has no license). Inclusive
32-bit intervals with E1/E2/E3 rescaling; public midpoint extension and first stable
N-bit prefix termination. This is entropy coding, not a cryptographic primitive.
"""
import bisect
import math
import numpy as np
from ..errors import FramingError

PRECISION=32
TOTAL=65536

def frequencies(logits):
    values=np.asarray(logits,dtype=np.float64)
    if values.shape!=(16,) or not np.isfinite(values).all():
        raise ValueError('Sixteen finite conditional logits required')
    p=np.exp(values-values.max());p/=p.sum()
    scaled=p*(TOTAL-16);base=np.floor(scaled).astype(np.int64)
    left=TOTAL-16-int(base.sum())
    order=sorted(range(16),key=lambda i:(-(float(scaled[i])-int(base[i])),i))
    for i in order[:left]:base[i]+=1
    return [int(x)+1 for x in base]

def packet_bits(data):
    return [(b>>shift)&1 for b in data for shift in range(7,-1,-1)]

class ArithmeticState:
    def __init__(self, precision=PRECISION):
        if not 4<=precision<=32:raise ValueError('Invalid arithmetic precision')
        self.precision=precision;self.full=1<<precision
        self.low=0;self.high=self.full-1;self.pending=0;self.bits=[]
    def bounds(self,freq):
        if not freq or any(type(f)!=int or f<=0 for f in freq):raise ValueError('Positive integer frequencies required')
        total=sum(freq);width=self.high-self.low+1
        if width<total:raise FramingError('Arithmetic interval too narrow for frequency table')
        cumulative=[0]
        for f in freq:cumulative.append(cumulative[-1]+f)
        edges=[self.low+width*c//total for c in cumulative]
        if any(a>=b for a,b in zip(edges,edges[1:])):raise FramingError('Zero-width arithmetic interval')
        return edges
    def step(self,symbol,freq,code=None,read_bit=None):
        edges=self.bounds(freq)
        if type(symbol)!=int or not 0<=symbol<len(freq):raise FramingError('Invalid arithmetic symbol')
        self.low,self.high=edges[symbol],edges[symbol+1]-1
        before=len(self.bits);half=self.full//2;quarter=half//2
        while True:
            if self.high<half:bit=0;offset=0
            elif self.low>=half:bit=1;offset=half
            elif self.low>=quarter and self.high<3*quarter:
                self.pending+=1;bit=None;offset=quarter
            else:break
            if bit is not None:
                self.bits.append(bit);self.bits.extend([1-bit]*self.pending);self.pending=0
            self.low=(self.low-offset)*2;self.high=(self.high-offset)*2+1
            if code is not None:code=(code-offset)*2+read_bit()
        return code, self.bits[before:]
    def select(self,code,freq):
        edges=self.bounds(freq)
        if not self.low<=code<=self.high:raise FramingError('Arithmetic point outside interval')
        return bisect.bisect_right(edges,code)-1
    def snapshot(self):return {'low':self.low,'high_inclusive':self.high,'pending_underflow':self.pending,'stable_bits':len(self.bits)}

class PacketEncoder:
    def __init__(self,data,precision=PRECISION):
        self.target=8*len(data);self.source=packet_bits(data)+[1];self.position=0;self.state=ArithmeticState(precision)
        self.code=0
        for _ in range(precision):self.code=2*self.code+self.read_bit()
    def read_bit(self):
        bit=self.source[self.position] if self.position<len(self.source) else 0
        self.position+=1;return bit
    @property
    def done(self):return len(self.state.bits)>=self.target
    def step(self,freq):
        if self.done:raise FramingError('Trailing arithmetic symbol')
        symbol=self.state.select(self.code,freq)
        self.code,_=self.state.step(symbol,freq,self.code,self.read_bit)
        if self.state.bits!= (self.source+[0]*len(self.state.bits))[:len(self.state.bits)]:
            raise FramingError('Arithmetic inverse invariant violated')
        return symbol

class PacketDecoder:
    def __init__(self,length,precision=PRECISION):
        if type(length)!=int or not 1<=length<=196:raise FramingError('Invalid bounded packet length')
        self.length=length;self.state=ArithmeticState(precision);self.tables=[];self.symbols=[]
    @property
    def done(self):return len(self.state.bits)>=8*self.length
    def step(self,symbol,freq):
        if self.done:raise FramingError('Trailing arithmetic tokens')
        self.state.step(symbol,freq);self.tables.append(list(freq));self.symbols.append(symbol)
    def finish(self):
        if not self.done:raise FramingError('Incomplete arithmetic final interval')
        bits=self.state.bits;n=8*self.length
        if bits[n:] != ([1]+[0]*len(bits))[0:len(bits)-n]:raise FramingError('Invalid deterministic midpoint filler bits')
        data=bytes(sum(bits[i+j]<<(7-j) for j in range(8)) for i in range(0,n,8))
        # Public pure-integer replay verifies the midpoint-extended point, including
        # unread precision-window bits. No extra model calls or encoder trace.
        canonical=PacketEncoder(data,self.state.precision)
        for symbol,freq in zip(self.symbols,self.tables):
            if canonical.step(freq)!=symbol:raise FramingError('Noncanonical arithmetic termination')
        if not canonical.done:raise FramingError('Incomplete canonical termination')
        return data
