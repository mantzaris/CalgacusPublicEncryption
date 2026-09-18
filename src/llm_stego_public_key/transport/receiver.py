from ..codecs.interfaces import TextCodec
from ..cryptography.hpke import ReplayCache, open_message
from ..profile import Binding


def receive(
    transmitted_utf8: bytes,
    private_key: bytes,
    binding: Binding,
    cover_context: str,
    codec: TextCodec,
    replay: ReplayCache,
) -> bytes:
    """No token IDs, ranks, source hashes or encoder state cross this interface."""
    extracted = codec.extract(transmitted_utf8, cover_context)
    return open_message(extracted, private_key, binding, replay)
