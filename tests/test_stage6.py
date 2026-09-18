"""Focused Stage 6 contracts only; no real model inference or broad suite."""
import copy
import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from llm_stego_public_key.codecs.inferred_rank16 import InferredRank16Codec,inferred_length
from llm_stego_public_key.codecs.public_utf8_rank16 import PublicUtf8Rank16Codec
from llm_stego_public_key.cryptography.hpke import generate_key_pair,seal,deserialize,ReplayCache
from llm_stego_public_key.errors import FramingError,TransportError,AuthenticationError,BudgetError
from llm_stego_public_key.profile import Binding,validate_supported_profile
from llm_stego_public_key.transport.envelope_receiver import receive_envelope_text
from llm_stego_public_key.evaluation.budget import BudgetLedger
from llm_stego_public_key.evaluation.public_prefix import predict_public_prefix,choose_token
from llm_stego_public_key.evaluation.full_text_observer import observe_complete,parse_public_symbols,kem_representation
ROOT=Path(__file__).resolve().parents[1]
P={m:json.loads((ROOT/f'configs/stage6/{m}.json').read_text()) for m in ['L','F','Calgacus']};C=P['F']['cover_contexts'][0]

class Toy:
    def begin(self,c):self.prefix=[]
    def logits(self):return np.zeros(32,dtype=np.float32)
    def advance(self,t):self.prefix.append(t)
    def tokenize(self,b):return [v-65 for v in b]
    def detokenize(self,ids):return bytes(65+t for t in ids)

def codec():return InferredRank16Codec(Toy(),lambda t:4)

class FramingContracts(unittest.TestCase):
    def test_independent_nibble_inverse_and_bounds(self):
        self.assertEqual(codec().extract(b'KL'*68,P['F'],C),b'\xab'*68)
        self.assertEqual(codec().embed(b'\xff'*196,P['F'],C),b'PP'*196)
        self.assertEqual(inferred_length(136),68);self.assertEqual(inferred_length(392),196)
        for n in [0,134,135,137,393,394,512]:
            with self.assertRaises(FramingError):inferred_length(n)
    def test_invalid_utf8_noncanonical_and_rank(self):
        with self.assertRaises(TransportError):codec().extract(b'\xff'*136,P['F'],C)
        with self.assertRaises(FramingError):codec().extract(b'Q'+b'A'*135,P['F'],C)
        class Noncanonical(Toy):
            def tokenize(self,b):return [0]*len(b)
        with self.assertRaises(FramingError):InferredRank16Codec(Noncanonical(),lambda t:4).extract(b'B'*136,P['F'],C)
    def test_empty_max_and_profile_binding(self):
        sk,pk=generate_key_pair()
        for payload in [b'',bytes(range(128))]:
            env=deserialize(seal(payload,pk,Binding.from_profile(P['F'],C)))
            wire=codec().embed(env,P['F'],C)
            with ReplayCacheContext() as cache:self.assertEqual(receive_envelope_text(wire,sk,P['F'],C,codec(),cache),payload)
        wrong=deserialize(seal(b'x',pk,Binding.from_profile(P['L'],C)))
        with ReplayCacheContext() as cache,self.assertRaises(AuthenticationError):receive_envelope_text(codec().embed(wrong,P['F'],C),sk,P['F'],C,codec(),cache)
    def test_even_truncation_append_authentication_and_odd_rejection(self):
        sk,pk=generate_key_pair();wire=codec().embed(deserialize(seal(b'abc',pk,Binding.from_profile(P['F'],C))),P['F'],C)
        for bad in [wire[:-2],wire+b'AA']:
            with ReplayCacheContext() as cache,self.assertRaises(AuthenticationError):receive_envelope_text(bad,sk,P['F'],C,codec(),cache)
        for bad in [wire[:-1],wire+b'A',b'A'*394]:
            with self.assertRaises(FramingError):codec().extract(bad,P['F'],C)
    def test_unchanged_candidates_and_registered_profiles(self):
        m=Toy();f=InferredRank16Codec(m,lambda t:4);f._start(P['F'],C,'test')
        self.assertEqual(f.candidates([]),list(range(16)))
        self.assertIs(InferredRank16Codec.candidates,PublicUtf8Rank16Codec.candidates)
        for p in P.values():validate_supported_profile(p)
        with self.assertRaises(ValueError):validate_supported_profile(dict(P['F'],profile_id='arbitrary'))

class ReplayCacheContext:
    def __enter__(self):self.cache=ReplayCache();return self.cache
    def __exit__(self,*args):self.cache.close()

class ObserverContracts(unittest.TestCase):
    def test_public_inputs_independent_score_and_frame(self):
        names=list(inspect.signature(observe_complete).parameters)
        self.assertFalse(any(x in names for x in ['private_key','payload','encoder_trace','expected_length','label']))
        m=Toy();pred=predict_public_prefix(PublicUtf8Rank16Codec(m,lambda t:4),P['L'],C)
        o=observe_complete(b'AA'*68,P['F'],C,bytes(32),pred,P['L'],m,lambda t:4)
        self.assertTrue(o['format_accepted']);self.assertTrue(o['prefix']['prefix_match'])
        self.assertEqual(o['mean_nll_bits'],5);self.assertEqual(o['mean_log2_rank'],0)
        self.assertTrue(o['kem_canonical']);self.assertFalse(o['authenticated'])
        with self.assertRaises(TypeError):observe_complete(b'',P['F'],C,bytes(32),pred,P['L'],m,lambda t:4,private_key=b'x')
    def test_independent_representation_and_frame_failures(self):
        self.assertTrue(kem_representation((2**255-20).to_bytes(32,'little')+bytes(36)))
        self.assertFalse(kem_representation((2**255-19).to_bytes(32,'little')+bytes(36)))
        self.assertFalse(kem_representation(bytes(31)+b'\x80'+bytes(36)))
        self.assertEqual(parse_public_symbols([10,11]*68,'F'),b'\xab'*68)
        for symbols in [[0]*135,[0]*394,[None]*136]:
            with self.assertRaises(FramingError):parse_public_symbols(symbols,'F')
        self.assertEqual(parse_public_symbols([0,0,0,0,0,0,4,4]+[10,11]*68,'L'),b'\xab'*68)
    def test_sampling_policies_not_changed(self):
        class Probe:
            def choice(self,n,p):self.p=p;return 0
            def integers(self,n):return 15
        r=Probe();v=np.log(np.arange(1,33,dtype=float));eligible=list(range(16))
        choose_token(v,eligible,'A',r);np.testing.assert_allclose(r.p,np.arange(1,33)/528)
        choose_token(v,eligible,'B',r);np.testing.assert_allclose(r.p,np.arange(1,17)/136)
        self.assertEqual(choose_token(v,eligible,'C',r),(15,15))

class AllocationContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.p=Path(self.temp.name)/'project_budget.jsonl'
        self.auth=json.loads((ROOT/'configs/stage6/authorization.json').read_text())
        # Test a copy of the reviewed prefix even after a real authorized extension.
        self.raw=(ROOT/'artifacts/project_budget.jsonl').read_bytes()[:self.auth['previous_checkpoint']['bytes']]
        self.p.write_bytes(self.raw);self.p.with_suffix('.checkpoint.json').write_text(json.dumps(self.auth['previous_checkpoint']))
    def tearDown(self):self.temp.cleanup()
    def test_extension_prefix_lock_and_restart(self):
        b=BudgetLedger(self.p,authorization=self.auth)
        try:
            self.assertEqual(b.usage(),self.auth['baseline_usage'])
            with self.assertRaises(BudgetError):BudgetLedger(self.p,authorization=self.auth)
            aid=b.reserve(45,128,allocation_id=self.auth['allocation_id'],case_id='simulated')
        finally:b.close()
        b=BudgetLedger(self.p,authorization=self.auth)
        self.assertEqual(b.usage()['tokens'],23849+128);b.close()
        self.assertEqual(self.p.read_bytes()[:len(self.raw)],self.raw)
        with self.assertRaises(BudgetError):BudgetLedger(self.p) # old launcher fails closed
    def test_exact_additional_boundary_and_no_implicit_increase(self):
        b=BudgetLedger(self.p,authorization=self.auth)
        try:
            with self.assertRaises(BudgetError):b.reserve(1,1)
            b.reserve(14400,200000,160,allocation_id=self.auth['allocation_id'])
            with self.assertRaises(BudgetError):b.reserve(0,1,0,allocation_id=self.auth['allocation_id'])
        finally:b.close()
        altered=copy.deepcopy(self.auth);altered['additional_limits']['tokens']+=1
        with self.assertRaises(BudgetError):BudgetLedger(self.p,authorization=altered)
    def test_rollback_detected(self):
        b=BudgetLedger(self.p,authorization=self.auth);b.reserve(45,128,allocation_id=self.auth['allocation_id']);b.close()
        self.p.write_bytes(self.raw)
        with self.assertRaises(BudgetError):BudgetLedger(self.p,authorization=self.auth)

if __name__=='__main__':unittest.main()
