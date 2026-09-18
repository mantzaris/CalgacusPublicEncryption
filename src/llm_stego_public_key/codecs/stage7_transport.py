"""Size-class F and adapted public arithmetic R; shared canonical admission."""
from .public_utf8_rank16 import PublicUtf8Rank16Codec,InvariantError
from .inferred_rank16 import InferredRank16Codec
from .arithmetic_core import PacketEncoder,PacketDecoder,frequencies
from ..profile import validate_stage7_profile
from ..errors import CapacityError,FramingError,TransportError

def wire_ids(model,raw,profile):
    if type(raw)!=bytes or len(raw)>profile['tokens']['max_transport_bytes']:raise FramingError('Invalid transport bytes')
    try:raw.decode('utf-8',errors='strict')
    except UnicodeError as exc:raise TransportError('Invalid UTF-8') from exc
    ids=model.tokenize(raw)
    if not 1<=len(ids)<=profile['tokens']['max_tokens']:raise FramingError('Invalid bounded carrier count')
    if model.detokenize(ids)!=raw:raise FramingError('Noncanonical received bytes')
    return ids

class FixedClassRank16Codec(InferredRank16Codec):
    def embed(self,envelope,public_profile,cover_context):
        validate_stage7_profile(public_profile,'F')
        if len(envelope)!=public_profile['public_size_class']['envelope_bytes']:raise FramingError('Wrong public size class')
        return super().embed(envelope,public_profile,cover_context)
    def extract(self,transmitted_utf8,public_profile,cover_context):
        validate_stage7_profile(public_profile,'F')
        ids=wire_ids(self.model,transmitted_utf8,public_profile)
        if len(ids)!=2*public_profile['public_size_class']['envelope_bytes']:raise FramingError('Public size-class token count mismatch')
        return super().extract(transmitted_utf8,public_profile,cover_context)

class Arithmetic16Codec(PublicUtf8Rank16Codec):
    def _start(self,profile,cover,direction):
        validate_stage7_profile(profile)
        if cover not in profile['cover_contexts']:raise FramingError('Unknown public context')
        self.trace={'direction':direction,'advanced_ids':[],'symbols':[],'candidate_steps':[],'arithmetic_steps':[]}
        self.model.begin(cover)
    def embed(self,envelope,public_profile,cover_context):
        validate_stage7_profile(public_profile,'R')
        if type(envelope)!=bytes or len(envelope)!=public_profile['public_size_class']['envelope_bytes']:raise FramingError('Wrong public size class')
        coder=PacketEncoder(envelope);self._start(public_profile,cover_context,'embed');ids=self.trace['advanced_ids']
        while not coder.done:
            if len(ids)>=public_profile['tokens']['max_tokens']:
                self.trace['terminal']=coder.state.snapshot();raise CapacityError('Arithmetic carrier ceiling before complete stable packet')
            eligible=self.candidates(ids);freq=frequencies(self.model.logits()[eligible]);symbol=coder.step(freq)
            self._advance(eligible[symbol],symbol)
            self.trace['arithmetic_steps'].append(dict(coder.state.snapshot(),frequencies=freq))
        self.trace['terminal']=coder.state.snapshot();raw=self.model.detokenize(ids)
        try:raw.decode('utf-8',errors='strict')
        except UnicodeError as exc:raise InvariantError('Arithmetic emission invalid UTF-8') from exc
        self.trace['retokenized_ids']=self.model.tokenize(raw)
        if self.trace['retokenized_ids']!=ids:raise InvariantError('Arithmetic emission retokenization drift')
        if len(raw)>public_profile['tokens']['max_transport_bytes']:raise CapacityError('Transport bytes exceed bound')
        return raw
    def extract(self,transmitted_utf8,public_profile,cover_context):
        validate_stage7_profile(public_profile,'R');ids=wire_ids(self.model,transmitted_utf8,public_profile)
        coder=PacketDecoder(public_profile['public_size_class']['envelope_bytes'])
        self._start(public_profile,cover_context,'extract');self.trace['received_ids']=ids;prefix=self.trace['advanced_ids']
        for token in ids:
            eligible=self.candidates(prefix)
            if token not in eligible:raise FramingError('Token outside public admissible support')
            symbol=eligible.index(token);freq=frequencies(self.model.logits()[eligible]);coder.step(symbol,freq)
            self._advance(token,symbol);self.trace['arithmetic_steps'].append(dict(coder.state.snapshot(),frequencies=freq))
        self.trace['terminal']=coder.state.snapshot()
        return coder.finish()
