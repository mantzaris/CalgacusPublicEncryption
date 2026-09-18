from typing import Protocol

import numpy as np


class RankModel(Protocol):
    def tokenize(self, raw: bytes) -> list[int]: ...
    def detokenize(self, ids: list[int]) -> bytes: ...
    def begin(self, context: str): ...
    def logits(self) -> np.ndarray: ...
    def advance(self, token: int): ...


class TextCodec(Protocol):
    def encode(self, source: str, cover_context: str) -> bytes: ...
    def extract(self, transmitted_utf8: bytes, cover_context: str) -> str: ...


class PublicEnvelopeCodec(Protocol):
    """Future arithmetic/range adapter: length/framing must be public and explicit.

    No receiver ranks, bit decisions, payload hashes, or encoder state may be inputs.
    Implementations must document eligible distributions, precision and termination.
    """

    def embed(self, envelope: bytes, public_profile: dict, cover_context: str) -> bytes: ...
    def extract(
        self, transmitted_utf8: bytes, public_profile: dict, cover_context: str
    ) -> bytes: ...


class KeyedEnvelopeCodec(Protocol):
    """Separate setup: secret steganographic key is independent of the HPKE key.

    Nonce is overt agreed metadata; its transport and reuse policy need auditing.
    A simulation PRNG seed does not fulfill the cryptographic-key contract.
    """

    def embed(
        self,
        envelope: bytes,
        public_profile: dict,
        cover_context: str,
        stego_key: bytes,
        public_nonce: bytes,
    ) -> bytes: ...
    def extract(
        self,
        transmitted_utf8: bytes,
        public_profile: dict,
        cover_context: str,
        stego_key: bytes,
        public_nonce: bytes,
    ) -> bytes: ...
