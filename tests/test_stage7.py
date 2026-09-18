"""Focused entropy/receiver/accounting contracts; no model inference."""
from fractions import Fraction
import inspect
import json
from pathlib import Path
import pytest
from llm_stego_public_key.codecs.arithmetic_core import ArithmeticState,PacketEncoder,PacketDecoder,frequencies
from llm_stego_public_key.errors import FramingError


def reference_packet(data,tables,limit=10000):
    # Independent exact rational interval calculation, without finite-state
    # renormalization, pending bits, or production inverse code.
    n=8*len(data);value=int.from_bytes(data,'big');point=Fraction(2*value+1,2**(n+1))
    low,high=Fraction(0),Fraction(1);symbols=[]
    for i in range(limit):
        freq=tables[i%len(tables)];width=high-low;cumulative=0
        for symbol,f in enumerate(freq):
            a=low+width*Fraction(cumulative,sum(freq));cumulative+=f
            b=low+width*Fraction(cumulative,sum(freq))
            if a<=point<b:break
        else:raise AssertionError('Reference interval')
        low,high=a,b;symbols.append(symbol)
        if low>=Fraction(value,2**n) and high<=Fraction(value+1,2**n):return symbols
    raise AssertionError('Reference capacity')


def coded(data,tables,precision=32):
    coder=PacketEncoder(data,precision);symbols=[]
    for i in range(10000):
        if coder.done:return symbols
        symbols.append(coder.step(tables[i%len(tables)]))
    raise AssertionError('Capacity')

@pytest.mark.parametrize('data,tables',[(b'\x00',[[1]*16]),(b'\xff',[[1]*16]),(b'\x1f',[[1]*16]),(b'\x80',[[3,1]]),(b'\x01',[[3,1]]),(b'\xfe',[[1,3]]),(b'\xa5',[[1,1],[1,3],[3,1]]),(bytes.fromhex('00112233445566778899aabbccddeeff'),[[1]*16])])
def test_independent_rational_reference(data,tables):
    expected=reference_packet(data,tables)
    assert coded(data,tables)==expected
    inverse=PacketDecoder(len(data))
    for i,s in enumerate(expected):inverse.step(s,tables[i%len(tables)])
    assert inverse.finish()==data


def test_explicit_nibbles_and_interval_boundary():
    assert coded(bytes.fromhex('001f80ff'),[[1]*16])==[0,0,1,15,8,0,15,15]
    s=ArithmeticState(8)
    assert s.select(127,[1,1])==0 and s.select(128,[1,1])==1
    s.step(1,[1,1]);assert s.bits==[1] and (s.low,s.high)==(0,255)
    with pytest.raises(FramingError):s.bounds([256,1])


def test_incomplete_append_and_nonzero_filler():
    d=PacketDecoder(1);d.step(1,[1]*16)
    with pytest.raises(FramingError,match='Incomplete'):d.finish()
    d.step(15,[1]*16);assert d.finish()==b'\x1f'
    with pytest.raises(FramingError,match='Trailing'):d.step(0,[1]*16)
    d=PacketDecoder(1);d.state.bits=[0]*9
    with pytest.raises(FramingError,match='filler'):d.finish()
    for n in [0,197,-1,True]:
        with pytest.raises(FramingError):PacketDecoder(n)


def test_frequency_rounding_deterministic_positive():
    assert frequencies([0.0]*16)==[4096]*16
    f=frequencies([0.0]+[-1000.0]*15)
    assert f==[65521]+[1]*15 and sum(f)==65536
    assert frequencies(list(range(16)))==frequencies(list(range(16)))


def test_precision_crossing_and_public_canonical_inverse():
    data=bytes(range(196));tables=[[40000,20000,5536],[1]*16]
    symbols=coded(data,tables);d=PacketDecoder(len(data))
    for i,s in enumerate(symbols):d.step(s,tables[i%len(tables)])
    assert d.finish()==data
    with pytest.raises(FramingError):
        short=PacketDecoder(len(data))
        for i,s in enumerate(symbols[:-1]):short.step(s,tables[i%len(tables)])
        short.finish()


def test_actual_text_interfaces_and_class_boundaries():
    from test_stage6 import Toy
    from llm_stego_public_key.codecs.stage7_transport import Arithmetic16Codec,FixedClassRank16Codec
    from llm_stego_public_key.codecs.public_utf8_rank16 import PublicUtf8Rank16Codec
    from llm_stego_public_key.cryptography.hpke import generate_key_pair,seal,deserialize,ReplayCache
    from llm_stego_public_key.transport.envelope_receiver import receive_envelope_text
    from llm_stego_public_key.profile import Binding
    from llm_stego_public_key.errors import TransportError
    for method,cls in [('F',FixedClassRank16Codec),('R',Arithmetic16Codec)]:
      for n in [32,128]:
        p=json.loads(Path(f'configs/stage7/{method}{n}.json').read_text());cover=p['cover_contexts'][0]
        new=lambda:cls(Toy(),lambda t:4)
        sk,pk=generate_key_pair();payload=bytes(range(n));env=deserialize(seal(payload,pk,Binding.from_profile(p,cover)))
        wire=new().embed(env,p,cover)
        with_cache=ReplayCache()
        try:assert receive_envelope_text(wire,sk,p,cover,new(),with_cache)==payload
        finally:with_cache.close()
        assert cls.candidates is PublicUtf8Rank16Codec.candidates
        for bad in [wire[:-1],wire+b'A',b'',b'Q'+wire[1:]]:
            with pytest.raises(FramingError):new().extract(bad,p,cover)
        with pytest.raises(TransportError):new().extract(b'\xff',p,cover)
        with pytest.raises(FramingError):new().embed(bytes(68),p,cover)


def test_public_observer_no_private_inputs():
    from test_stage6 import Toy
    from llm_stego_public_key.evaluation.stage7_observer import observe_stage7
    assert list(inspect.signature(observe_stage7).parameters)==['transmitted_utf8','public_profile','cover_context','recipient_public_key','model','token_attributes']
    for method in ['F','R']:
        p=json.loads(Path(f'configs/stage7/{method}32.json').read_text())
        o=observe_stage7(b'A'*200,p,p['cover_contexts'][0],bytes(32),Toy(),lambda t:4)
        assert o['format_accepted'] and not o['authenticated'] and o['mean_nll_bits']==5
        assert o['body_region_scores'] is None


def test_accounting_extension_restart_lock_and_no_rollback(tmp_path):
    from llm_stego_public_key.evaluation.budget import BudgetLedger
    from llm_stego_public_key.errors import BudgetError
    auth=json.loads(Path('configs/stage7/authorization.json').read_text());old=auth['previous_checkpoint']
    raw=Path('artifacts/project_budget.jsonl').read_bytes()[:old['bytes']];p=tmp_path/'ledger.jsonl';p.write_bytes(raw)
    p.with_suffix('.checkpoint.json').write_text(json.dumps(old))
    b=BudgetLedger(p,authorization=auth);assert b.usage()==auth['baseline_usage']
    with pytest.raises(BudgetError):BudgetLedger(p,authorization=auth)
    aid=b.reserve(45,128,allocation_id=auth['allocation_id']);b.close()
    b=BudgetLedger(p,authorization=auth);assert b.usage()['tokens']==auth['baseline_usage']['tokens']+128
    b.settle(aid,10,32);b.close();assert p.read_bytes().startswith(raw)
    with pytest.raises(BudgetError):BudgetLedger(p,authorization=json.loads(Path('configs/stage6/authorization.json').read_text()))
    p.write_bytes(raw)
    with pytest.raises(BudgetError):BudgetLedger(p,authorization=auth)
