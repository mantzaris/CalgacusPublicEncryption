"""Receiver for a public binary-envelope codec; expected values are evaluator-only."""
from ..cryptography.hpke import open_message, serialize
from ..profile import Binding, validate_rank16_profile


def receive_envelope_text(transmitted_utf8, private_key, public_profile, cover_context, codec, replay):
    validate_rank16_profile(public_profile)
    envelope = codec.extract(transmitted_utf8, public_profile, cover_context)
    return open_message(serialize(envelope), private_key,
                        Binding.from_profile(public_profile, cover_context), replay)
