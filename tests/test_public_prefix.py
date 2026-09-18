"""Focused Stage 4 contracts, not a recovery or broad CPU test suite."""
import inspect
import json
import math
from pathlib import Path
import unittest
import numpy as np
from llm_stego_public_key.codecs.public_utf8_rank16 import PublicUtf8Rank16Codec, frame, nibbles
from llm_stego_public_key.evaluation.public_prefix import PublicPrediction, cache_key, observe_prefix, probabilities, choose_token, predict_public_prefix, generate_prefix
from llm_stego_public_key.profile import canonical_json
import hashlib
P=json.loads((Path(__file__).resolve().parents[1]/'configs/public_utf8_rank16_v1.json').read_text());C=P['cover_contexts'][0]

class Toy:
    def __init__(self): self.evaluated=[]
    def begin(self,context): self.evaluated=[]
    def logits(self): return np.zeros(32,dtype=np.float32)
    def advance(self,t): self.evaluated.append(t)
    def detokenize(self,ids): return bytes(65+t for t in ids)
    def tokenize(self,raw): return [v-65 for v in raw]

def codec(): return PublicUtf8Rank16Codec(Toy(),lambda t:4)
def prediction(): return PublicPrediction(hashlib.sha256(canonical_json(P)).hexdigest(),C,(0,)*6,cache_key(P,C))

class PrefixContracts(unittest.TestCase):
    def test_structural_six_zeros_all_supported_lengths(self):
        for n in range(68,197): self.assertEqual(nibbles(frame(bytes(n)))[:6],[0]*6)

    def test_observer_public_boundary_and_no_length_feature(self):
        self.assertEqual(list(inspect.signature(observe_prefix).parameters),['transmitted_utf8','public_profile','cover_context','prediction','tokenize'])
        t=Toy()
        for raw in (b'AAAAAA',b'AAAAAAB',b'AAAAAA'+b'Z'*900):
            self.assertTrue(observe_prefix(raw,P,C,prediction(),t.tokenize)['prefix_match'])
        self.assertFalse(observe_prefix(b'AAAAAB',P,C,prediction(),t.tokenize)['prefix_match'])
        with self.assertRaises(TypeError): observe_prefix(b'AAAAAA',P,C,prediction(),t.tokenize,private_key=b'x')

    def test_malformed_and_wrong_public_cache(self):
        for raw,status in [(b'\xff','invalid_utf8'),(b'AAAAA','insufficient_tokens'),('AAAAAA','invalid_input')]:
            self.assertEqual(observe_prefix(raw,P,C,prediction(),Toy().tokenize)['status'],status)
        with self.assertRaises(ValueError): observe_prefix(b'AAAAAA',P,P['cover_contexts'][1],prediction(),Toy().tokenize)

    def test_independent_probability_and_path_values(self):
        p,logs=probabilities(np.log([1.,2.,3.]));np.testing.assert_allclose(p,[1/6,2/6,3/6]);np.testing.assert_allclose(np.exp(logs),p)
        c=codec();r=predict_public_prefix(c,P,C)
        self.assertEqual(r['token_ids'],[0]*6);self.assertEqual(r['prefix_utf8'],'AAAAAA')
        self.assertAlmostEqual(r['A_log_probability_latent_sequence'],-6*math.log(32))
        self.assertAlmostEqual(r['B_log_probability_prefix_match'],-6*math.log(16))
        self.assertEqual(r['C_probability_prefix_match'],1/16777216)
        self.assertEqual(len(c.model.evaluated),6)

    def test_exact_sampling_policies(self):
        class Probe:
            def choice(self,n,p): self.n,self.p=n,p;return n-1
            def integers(self,n): self.n=n;return 3
        rng=Probe();v=np.log(np.arange(1,33,dtype=float));eligible=list(range(16,32))
        self.assertEqual(choose_token(v,[], 'A',rng),(31,None));np.testing.assert_allclose(rng.p,np.arange(1,33)/sum(range(1,33)))
        self.assertEqual(choose_token(v,eligible,'B',rng),(31,15));np.testing.assert_allclose(rng.p,np.arange(17,33)/sum(range(17,33)))
        self.assertEqual(choose_token(v,eligible,'C',rng),(19,3));self.assertEqual(rng.n,16)
        for family in 'ABC':
            c=codec();raw=generate_prefix(c,P,C,family,2026092101)
            self.assertEqual(len(c.model.evaluated),6);self.assertEqual(len(raw),6)

if __name__=='__main__':unittest.main()
