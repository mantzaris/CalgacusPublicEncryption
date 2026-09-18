import base64
import json
from pathlib import Path

import pytest

from llm_stego_public_key.cryptography.hpke import (
    MAX_PAYLOAD,
    ReplayCache,
    decode_record,
    deserialize,
    generate_key_pair,
    open_message,
    seal,
    serialize,
    suite,
)
from llm_stego_public_key.errors import AuthenticationError, FramingError, ReplayError
from llm_stego_public_key.profile import Binding


def test_rfc9180_appendix_a_2_1_and_published_sequence_vectors():
    """External expected bytes, not two sides agreeing with one another.

    CFRG vector set pinned in manifests/upstream_sources.json; the selected base
    suite matches RFC 9180 A.2.1, including sequence numbers through 256.
    """
    vector = json.loads(
        (Path(__file__).parent / "vectors" / "rfc9180_x25519_chacha20poly1305.json").read_text()
    )[0]

    def h(field):
        return bytes.fromhex(vector[field])

    s = suite()
    receiver_key = s.kem.derive_key_pair(h("ikmR"))
    ephemeral = s.kem.derive_key_pair(h("ikmE"))
    assert receiver_key.private_key.to_private_bytes() == h("skRm")
    assert receiver_key.public_key.to_public_bytes() == h("pkRm")
    assert ephemeral.private_key.to_private_bytes() == h("skEm")
    assert ephemeral.public_key.to_public_bytes() == h("pkEm")
    shared, enc = s.kem.encap(receiver_key.public_key, eks=ephemeral)
    assert shared == h("shared_secret")
    assert enc == h("enc")
    assert s.kem.decap(enc, receiver_key.private_key) == shared
    enc, sender = s.create_sender_context(receiver_key.public_key, info=h("info"), eks=ephemeral)
    receiver = s.create_recipient_context(enc, receiver_key.private_key, info=h("info"))
    assert sender._nonce == h("base_nonce")
    assert len(vector["encryptions"]) == 257
    for item in vector["encryptions"]:
        pt, aad, ct = (bytes.fromhex(item[k]) for k in ("pt", "aad", "ct"))
        assert sender.seal(pt, aad) == ct
        assert receiver.open(ct, aad) == pt  # Open published bytes independently.
    for item in vector["exports"]:
        for ctx in (sender, receiver):
            assert ctx.export(bytes.fromhex(item["exporter_context"]), item["L"]) == bytes.fromhex(
                item["exported_value"]
            )


@pytest.fixture
def keys():
    return generate_key_pair()


@pytest.fixture
def binding():
    return Binding.from_profile(
        {"cover_contexts": ["Public garden:"], "version": 1}, "Public garden:"
    )


@pytest.mark.parametrize(
    "payload", [b"", b"hello", b"\x00\xff\x80\r\n", "α🌲".encode(), bytes(range(MAX_PAYLOAD))]
)
def test_exact_payloads(payload, keys, binding):
    sk, pk = keys
    text = seal(payload, pk, binding)
    assert len(deserialize(text)) == len(payload) + 68
    assert open_message(text, sk, binding, ReplayCache()) == payload


def test_maximum_and_big_endian_lengths(keys, binding):
    with pytest.raises(FramingError):
        seal(b"x" * (MAX_PAYLOAD + 1), keys[1], binding)
    identifier = bytes(range(16))
    assert decode_record(identifier + b"\x00\x00\x00\x02\x00\xff") == (identifier, b"\x00\xff")


@pytest.mark.parametrize(
    "record",
    [
        b"",
        b"x" * 19,
        b"x" * 16 + b"\xff" * 4,
        b"x" * 16 + b"\x02\x00\x00\x00ab",
        b"x" * 16 + b"\0\0\0\0tail",
        b"x" * 16 + (129).to_bytes(4, "big") + b"x" * 129,
    ],
)
def test_invalid_record_lengths(record):
    with pytest.raises(FramingError):
        decode_record(record)


@pytest.mark.parametrize(
    "bad",
    ["", "!!!!" * 23, "A" * 1000, "é" * 92, "A" * 91, "A" * 91 + "\n", "-" * 92, "A" * 88 + "===="],
)
def test_malformed_base64(bad):
    with pytest.raises(FramingError):
        deserialize(bad)


def test_noncanonical_padding_bits():
    canonical = serialize(b"\0" * 68)
    # 68 bytes: one '='; changing final sextet's unused two bits preserves decoded bytes.
    alternate = canonical[:-2] + "B="
    assert base64.b64decode(alternate) == base64.b64decode(canonical)
    with pytest.raises(FramingError):
        deserialize(alternate)


@pytest.mark.parametrize("mutation", ["truncate", "tag", "enc", "zero_enc", "wrong_key"])
def test_authentication_failures(mutation, keys, binding):
    sk, pk = keys
    envelope = bytearray(deserialize(seal(b"synthetic secret", pk, binding)))
    if mutation == "truncate":
        envelope = envelope[:-1]
    elif mutation == "tag":
        envelope[-1] ^= 1
    elif mutation == "enc":
        envelope[0] ^= 1
    elif mutation == "zero_enc":
        envelope[:32] = b"\0" * 32
    else:
        sk = generate_key_pair()[0]
    cache = ReplayCache()
    with pytest.raises(AuthenticationError):
        open_message(serialize(bytes(envelope)), sk, binding, cache)
    assert cache.db.execute("SELECT count(*) FROM delivered").fetchone()[0] == 0


def test_wrong_info_and_aad(keys, binding):
    sk, pk = keys
    text = seal(b"research", pk, binding)
    with pytest.raises(AuthenticationError):
        open_message(text, sk, Binding(binding.encoded + b" "), ReplayCache())
    s = suite()
    enc, sender = s.create_sender_context(s.kem.deserialize_public_key(pk), info=binding.info)
    ct = sender.seal(b"x" * 16 + b"\0\0\0\1z", b"wrong associated data")
    with pytest.raises(AuthenticationError):
        open_message(serialize(enc + ct), sk, binding, ReplayCache())


def test_authenticated_invalid_record_is_not_delivered(keys, binding):
    sk, pk = keys
    s = suite()
    enc, sender = s.create_sender_context(s.kem.deserialize_public_key(pk), info=binding.info)
    text = serialize(enc + sender.seal(b"x" * 16 + b"\xff" * 4, binding.aad))
    cache = ReplayCache()
    with pytest.raises(FramingError):
        open_message(text, sk, binding, cache)
    assert cache.db.execute("SELECT count(*) FROM delivered").fetchone()[0] == 0


def test_persistent_replay_and_public_sender(keys, binding, tmp_path):
    sk, pk = keys
    text = seal(b"message", pk, binding)
    cache = ReplayCache(str(tmp_path / "replay.db"))
    assert open_message(text, sk, binding, cache) == b"message"
    cache.close()
    cache = ReplayCache(str(tmp_path / "replay.db"))
    with pytest.raises(ReplayError):
        open_message(text, sk, binding, cache)
    # A stranger can create a NEW valid ciphertext: base mode is not sender authentication.
    assert open_message(seal(b"stranger", pk, binding), sk, binding, cache) == b"stranger"


def test_randomness_and_cache_full(keys, binding):
    sk, pk = keys
    a, b = seal(b"same", pk, binding), seal(b"same", pk, binding)
    assert deserialize(a)[:32] != deserialize(b)[:32]
    cache = ReplayCache(max_entries=1)
    assert open_message(a, sk, binding, cache) == b"same"
    with pytest.raises(ReplayError):
        open_message(b, sk, binding, cache)
