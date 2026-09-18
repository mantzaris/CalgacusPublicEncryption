"""Canonical public configuration: no implicit secret context or normalization."""

import hashlib
import json
from dataclasses import dataclass


def canonical_json(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


@dataclass(frozen=True)
class Binding:
    # Snapshot bytes prevent later mutation of a dictionary changing the binding.
    encoded: bytes

    @classmethod
    def from_profile(cls, profile: dict, cover_context: str):
        if cover_context not in profile["cover_contexts"]:
            raise ValueError("Cover context is not in the agreed public profile")
        return cls(canonical_json({"profile": profile, "cover_context": cover_context}))

    @property
    def digest(self) -> bytes:
        return hashlib.sha256(self.encoded).digest()

    @property
    def info(self) -> bytes:
        return b"ICISSP2027/HPKE/info/v1\x00" + len(self.encoded).to_bytes(4, "big") + self.encoded

    @property
    def aad(self) -> bytes:
        return b"ICISSP2027/HPKE/envelope/v1\x00" + self.digest


SUPPORTED_PROFILE_SHA256 = "bd8a59d736843d78984c5d093dcee72cec50747629ce79a0685fe7652f4989b3"


def validate_supported_profile(profile: dict):
    """Reject unimplemented profile settings before loading the frozen backend."""
    if hashlib.sha256(canonical_json(profile)).hexdigest() != SUPPORTED_PROFILE_SHA256:
        raise ValueError(
            "Unsupported public model/profile; explicit adaptation and revalidation required"
        )
