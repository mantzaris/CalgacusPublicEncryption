import numpy as np
import pytest

from llm_stego_public_key.codecs.calgacus import CalgacusCodec, first_difference, order_logits
from llm_stego_public_key.errors import CapacityError, RankError, TransportError
from llm_stego_public_key.evaluation.observer import public_format_test
from llm_stego_public_key.cryptography.hpke import ReplayCache, generate_key_pair, seal
from llm_stego_public_key.profile import Binding, canonical_json
from llm_stego_public_key.transport.receiver import receive


class TableModel:
    """Independent finite oracle: payload BCA has ranks 2,3,1; cover is DDB."""

    def tokenize(self, raw):
        return [b - ord("A") for b in raw]

    def detokenize(self, ids):
        return bytes(ord("A") + i for i in ids)

    def begin(self, context):
        self.context, self.previous = context, None

    def logits(self):
        if self.context == "source":
            return np.array([1, 4, 2, 3] if self.previous == 1 else [4, 3, 2, 1])
        return np.array([3, 4, 1, 2] if self.previous == 3 else [1, 2, 4, 3])

    def advance(self, token):
        self.previous = token


def test_independently_specified_transcoding():
    codec = CalgacusCodec(TableModel(), "source")
    assert codec.ranks([1, 2, 0], "source") == [2, 3, 1]
    assert codec.from_ranks([2, 3, 1], "cover") == [3, 3, 1]
    assert codec.encode("BCA", "cover") == b"DDB"
    # Start from fixed external bytes with a separate model, not the encoder's trace.
    receiver = CalgacusCodec(TableModel(), "source")
    assert receiver.extract(b"DDB", "cover") == "BCA"


def test_tie_order_and_inverse():
    assert order_logits(np.array([1.0, 1.0, 0.0, 1.0])).tolist() == [0, 1, 3, 2]
    model = TableModel()
    model.logits = lambda: np.array([1.0, 1.0, 0.0, 1.0])
    codec = CalgacusCodec(model, "source")
    assert codec.ranks([3, 0, 1, 2], "source") == [3, 1, 2, 4]
    assert codec.from_ranks([3, 1, 2, 4], "cover") == [3, 0, 1, 2]


@pytest.mark.parametrize("values", [[], [1.0, float("nan")], [float("inf")], [[1, 2]]])
def test_invalid_logits(values):
    with pytest.raises(RankError):
        order_logits(np.array(values))


@pytest.mark.parametrize("rank", [0, -1, 5])
def test_bad_rank(rank):
    with pytest.raises(RankError):
        CalgacusCodec(TableModel(), "source").from_ranks([rank], "cover")


def test_empty_and_capacity():
    codec = CalgacusCodec(TableModel(), "source", max_tokens=2)
    assert codec.encode("", "cover") == b""
    assert codec.extract(b"", "cover") == ""
    with pytest.raises(CapacityError):
        codec.encode("ABC", "cover")
    with pytest.raises(CapacityError):
        codec.extract(b"ABC", "cover")


def test_retokenization_failure_is_retained():
    class MergingModel(TableModel):
        def tokenize(self, raw):
            return [0] if raw == b"DDB" else super().tokenize(raw)

    codec = CalgacusCodec(MergingModel(), "source")
    carrier = codec.encode("BCA", "cover")
    assert carrier == b"DDB"
    assert codec.trace["first_transport_divergence"] == {"position": 0, "expected": 3, "actual": 0}
    with pytest.raises(TransportError):
        codec.extract(carrier, "cover")


def test_special_empty_rendering_and_invalid_utf8():
    model = TableModel()
    model.detokenize = lambda ids: b""  # Like a non-rendering special token.
    codec = CalgacusCodec(model, "source")
    assert codec.encode("BCA", "cover") == b""
    assert codec.trace["first_transport_divergence"]["position"] == 0
    model.detokenize = lambda ids: b"\xff"
    with pytest.raises(TransportError):
        codec.encode("BCA", "cover")
    assert codec.trace["carrier_bytes_hex"] == "ff"
    with pytest.raises(TransportError):
        codec.extract(b"\xff", "cover")


class ByteModel:
    """Finite 256-symbol oracle: every byte (including whitespace) has its own token."""

    def tokenize(self, raw):
        return list(raw)

    def detokenize(self, ids):
        return bytes(ids)

    def begin(self, context):
        pass

    def logits(self):
        return np.arange(256, dtype=np.float32)

    def advance(self, token):
        pass


def test_end_to_end_receiver_only_gets_text_key_and_public_settings():
    profile = {"cover_contexts": ["public"], "version": 1}
    binding = Binding.from_profile(profile, "public")
    sk, pk = generate_key_pair()
    payload = bytes(range(128))
    serialized = seal(payload, pk, binding)
    encoder = CalgacusCodec(ByteModel(), "source")
    wire = encoder.encode(serialized, "public")
    receiver = CalgacusCodec(ByteModel(), "source")
    assert receive(wire, sk, binding, "public", receiver, ReplayCache()) == payload
    assert public_format_test(serialized) == {
        "format_valid": True,
        "envelope_bytes": 196,
        "authenticated": False,
    }
    assert public_format_test("ordinary prose")["format_valid"] is False


@pytest.mark.parametrize("source", [" a \n", "<|end_of_text|>", "e\u0301", "é", "\0\r\n"])
def test_no_implicit_text_normalization(source):
    codec = CalgacusCodec(ByteModel(), "source")
    wire = codec.encode(source, "cover")
    assert wire == source.encode("utf-8")
    assert codec.extract(wire, "cover") == source


def test_binding_is_unambiguous_and_snapshot():
    p = {"cover_contexts": ["a", "a\0b"], "version": 1}
    b = Binding.from_profile(p, "a")
    original = b.info
    p["version"] = 2
    assert b.info == original
    assert b.info != Binding.from_profile(p, "a").info
    assert b.info != Binding.from_profile(p, "a\0b").info
    assert canonical_json({"b": 1, "a": 2}) == b'{"a":2,"b":1}'
    with pytest.raises(ValueError):
        Binding.from_profile(p, "unagreed")
    assert first_difference([1], [1, 2])["position"] == 1
