"""One-shot base-mode HPKE with bounded, authenticated inner records."""

import base64
import binascii
import secrets
import sqlite3

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from pyhpke import AEADId, CipherSuite, KDFId, KEMId, KEMKey
from pyhpke.exceptions import OpenError

from ..errors import AuthenticationError, FramingError, ReplayError
from ..profile import Binding

MAX_PAYLOAD = 128
MIN_ENVELOPE = 68
MAX_ENVELOPE = MAX_PAYLOAD + MIN_ENVELOPE
MAX_BASE64 = 4 * ((MAX_ENVELOPE + 2) // 3)


def suite():
    return CipherSuite.new(
        KEMId.DHKEM_X25519_HKDF_SHA256, KDFId.HKDF_SHA256, AEADId.CHACHA20_POLY1305
    )


def generate_key_pair() -> tuple[bytes, bytes]:
    """Return raw (private, public) keys using the library's OS-backed generator."""
    sk = X25519PrivateKey.generate()
    return sk.private_bytes_raw(), sk.public_key().public_bytes_raw()


def public_key(private_key: bytes) -> bytes:
    return X25519PrivateKey.from_private_bytes(private_key).public_key().public_bytes_raw()


def encode_record(payload: bytes) -> bytes:
    if not isinstance(payload, bytes) or len(payload) > MAX_PAYLOAD:
        raise FramingError("Payload must be bytes of length 0..128")
    # No padding in v1. The length is unsigned, network byte order (big-endian).
    return secrets.token_bytes(16) + len(payload).to_bytes(4, "big") + payload


def decode_record(record: bytes) -> tuple[bytes, bytes]:
    if not 20 <= len(record) <= 20 + MAX_PAYLOAD:
        raise FramingError("Invalid authenticated inner record size")
    length = int.from_bytes(record[16:20], "big")
    if length > MAX_PAYLOAD or length != len(record) - 20:
        raise FramingError("Invalid authenticated payload length or trailing bytes")
    return record[:16], record[20:]


def serialize(envelope: bytes) -> str:
    if not MIN_ENVELOPE <= len(envelope) <= MAX_ENVELOPE:
        raise FramingError("Envelope length outside v1 bounds")
    return base64.b64encode(envelope).decode("ascii")


def deserialize(text: str) -> bytes:
    # Bound before ASCII conversion or Base64 allocation; reject whitespace, URL alphabet,
    # extra padding, omitted padding, and nonzero unused pad bits by canonical re-encoding.
    if not isinstance(text, str) or not 92 <= len(text) <= MAX_BASE64 or len(text) % 4:
        raise FramingError("Invalid Base64 length")
    try:
        data = base64.b64decode(text.encode("ascii"), validate=True)
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise FramingError("Invalid Base64") from exc
    if not MIN_ENVELOPE <= len(data) <= MAX_ENVELOPE or serialize(data) != text:
        raise FramingError("Noncanonical Base64 or invalid envelope length")
    return data


def seal(payload: bytes, recipient_public_key: bytes, binding: Binding) -> str:
    record = encode_record(payload)
    s = suite()
    pk = s.kem.deserialize_public_key(recipient_public_key)
    # No sender secret, PSK, deterministic ephemeral key or caller-provided nonce.
    enc, sender = s.create_sender_context(pk, info=binding.info)
    return serialize(enc + sender.seal(record, binding.aad))


class ReplayCache:
    """Persistent atomic first delivery; no expiry/eviction in this bounded prototype."""

    def __init__(self, path: str = ":memory:", max_entries: int = 10000):
        self.db = sqlite3.connect(path)
        self.max_entries = max_entries
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS delivered (scope BLOB, id BLOB, PRIMARY KEY (scope, id))"
        )
        self.db.commit()

    def accept(self, scope: bytes, message_id: bytes):
        try:
            self.db.execute("BEGIN IMMEDIATE")
            if self.db.execute(
                "SELECT 1 FROM delivered WHERE scope=? AND id=?", (scope, message_id)
            ).fetchone():
                raise ReplayError("Authenticated message already delivered")
            if self.db.execute("SELECT count(*) FROM delivered").fetchone()[0] >= self.max_entries:
                raise ReplayError("Replay cache full; refusing new deliveries")
            self.db.execute("INSERT INTO delivered VALUES (?,?)", (scope, message_id))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def close(self):
        self.db.close()


def open_message(
    text: str, recipient_private_key: bytes, binding: Binding, replay: ReplayCache
) -> bytes:
    envelope = deserialize(text)
    s = suite()
    try:
        sk = KEMKey.from_pyca_cryptography_key(
            X25519PrivateKey.from_private_bytes(recipient_private_key)
        )
        receiver = s.create_recipient_context(envelope[:32], sk, info=binding.info)
        record = receiver.open(envelope[32:], binding.aad)
    except (OpenError, ValueError) as exc:
        raise AuthenticationError("HPKE authentication failed") from exc
    # No unauthenticated plaintext reaches the parser, replay state, or caller.
    message_id, payload = decode_record(record)
    replay.accept(public_key(recipient_private_key) + binding.digest, message_id)
    return payload
