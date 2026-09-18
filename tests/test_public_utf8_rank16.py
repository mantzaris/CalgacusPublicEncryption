"""Focused new-codec contracts only. No model/backend initialization."""
import json
from pathlib import Path
import unittest
import numpy as np

from llm_stego_public_key.codecs.public_utf8_rank16 import PublicUtf8Rank16Codec, frame, nibbles
from llm_stego_public_key.errors import CapacityError, FramingError

PROFILE = json.loads((Path(__file__).resolve().parents[1] / 'configs/public_utf8_rank16_v1.json').read_text())
COVER = PROFILE['cover_contexts'][0]


class Alphabet:
    def begin(self, context): self.prefix = []
    def logits(self): return np.zeros(32, dtype=np.float32)
    def advance(self, token): self.prefix.append(token)
    def tokenize(self, raw): return [v - 65 for v in raw]
    def detokenize(self, ids): return bytes(65 + i for i in ids)


def codec(model=None, attributes=lambda token: 4):
    return PublicUtf8Rank16Codec(model or Alphabet(), attributes)


class NewCodecContracts(unittest.TestCase):
    def test_independent_nibble_and_wire_examples(self):
        self.assertEqual(nibbles(b'\x01\xaf\x80\xff'), [0,1,10,15,8,0,15,15])
        self.assertEqual(frame(b'\xab' * 68)[:4], b'\x00\x00\x00\x44')
        # Independent ASCII alphabet fixture: 0=A, 4=E, 10=K, 11=L.
        expected = b'AAAAAAEE' + b'KL' * 68
        self.assertEqual(codec().embed(b'\xab' * 68, PROFILE, COVER), expected)
        self.assertEqual(codec().extract(expected, PROFILE, COVER), b'\xab' * 68)

    def test_maximum_and_inverse_without_encoder(self):
        # 196 = 0xc4, 0xff = two nibble-15/P symbols: exactly 400 tokens.
        wire = b'AAAAAAME' + b'PP' * 196
        self.assertEqual(len(wire), 400)
        self.assertEqual(codec().extract(wire, PROFILE, COVER), b'\xff' * 196)

    def test_bounded_length_before_payload_allocation(self):
        for size in (0, 67, 197, 0xffffffff):
            wire = bytes(65 + int(h,16) for h in f'{size:08x}') + b'AA'*68
            with self.subTest(size=size), self.assertRaises(FramingError):
                codec().extract(wire, PROFILE, COVER)
        for size in (0,67,197):
            with self.assertRaises(FramingError): frame(bytes(size))

    def test_truncation_trailing_invalid_choice(self):
        valid = b'AAAAAAEE' + b'KL' * 68
        for wire in (valid[:7], valid[:-1], valid+b'A', valid[:8]+b'Q'+valid[9:]):
            with self.subTest(wire=wire[:10]), self.assertRaises(FramingError):
                codec().extract(wire, PROFILE, COVER)

    def test_equal_logits_and_exclusion_order(self):
        c = codec(attributes=lambda t: 8 if t in (0,2) else 4)
        c._start(PROFILE,COVER,'embed')
        self.assertEqual(c.candidates([]), [1]+list(range(3,18)))
        self.assertEqual(c.trace['candidate_steps'][0]['examined'],18)

    def test_prefix_admissibility_and_exhaustion(self):
        class Edges(Alphabet):
            def detokenize(self, ids):
                if ids and ids[-1]==0: return b''
                if ids and ids[-1]==1: return b'\xff'
                if ids and ids[-1]==2: return b'Z'  # canonicalizes to ID 25, not ID 2
                return super().detokenize(ids)
        c=codec(Edges());c._start(PROFILE,COVER,'embed')
        self.assertEqual(c.candidates([]),list(range(3,19)))
        c=codec(attributes=lambda t: 8 if t>=15 else 4);c._start(PROFILE,COVER,'embed')
        with self.assertRaises(CapacityError): c.candidates([])

    def test_unregistered_policy_rejected(self):
        altered=dict(PROFILE,selection=dict(PROFILE['selection'],candidate_pool=256))
        with self.assertRaises(ValueError): codec().embed(bytes(68),altered,COVER)

if __name__ == '__main__': unittest.main()
