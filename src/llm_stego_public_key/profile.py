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


RANK16_PROFILE_SHA256 = "b3a106424d9e0e8b1c6d19ec7061d13a07a9a0871d0a92d5bb3dd1296b6156a6"


STAGE6_PROFILE_HASHES = {'L': 'ca3fb4b56b74e9aa263cf365e10413465f46546badca5fbd9862b5d54480003a', 'F': 'c41e25c434f13f868ad2b795715437026d22029ffe92f01ab74c871f94b7b006', 'Calgacus': '45a56748eeb728052a7d31d464527e5fb0c6d99adadd32b8a43f026cd6973e71'}

STAGE7_PROFILE_HASHES = {'F32': '8058245eab41db9f5b3826943e32f17bb3fe8dbe605aa15281b66f4d0d84d885', 'F128': 'c96715f5280b57f3beaa719c00546ec907d679f5a2ab63fdbf00c32664f783c6', 'R32': 'c581c623f4eb99e0043af0f415d0215585626bd0d65e377a3d06dcfe40923acf', 'R128': 'e1f2a4e90bfadca57a196cb364775030748cf223a70de9e1877b51fe3a8c843a'}

def validate_stage7_profile(profile, method=None):
    digest=hashlib.sha256(canonical_json(profile)).hexdigest()
    allowed={v for k,v in STAGE7_PROFILE_HASHES.items() if method is None or k.startswith(method)}
    if digest not in allowed: raise ValueError("Unsupported Stage 7 profile")

def validate_inferred_profile(profile: dict):
    if hashlib.sha256(canonical_json(profile)).hexdigest() not in {STAGE6_PROFILE_HASHES["F"], STAGE7_PROFILE_HASHES["F32"], STAGE7_PROFILE_HASHES["F128"]}:
        raise ValueError("Unsupported inferred rank16 profile")

def validate_rank_transport_profile(profile: dict):
    if hashlib.sha256(canonical_json(profile)).hexdigest() not in {RANK16_PROFILE_SHA256, STAGE6_PROFILE_HASHES["L"], STAGE6_PROFILE_HASHES["F"], *STAGE7_PROFILE_HASHES.values()}:
        raise ValueError("Unsupported public envelope transport profile")

def validate_rank16_profile(profile: dict):
    if hashlib.sha256(canonical_json(profile)).hexdigest() not in {RANK16_PROFILE_SHA256, STAGE6_PROFILE_HASHES["L"]}:
        raise ValueError("Unsupported public rank16 profile")


def validate_supported_profile(profile: dict):
    """Reject unimplemented profile settings before loading the frozen backend."""
    if hashlib.sha256(canonical_json(profile)).hexdigest() not in {SUPPORTED_PROFILE_SHA256, RANK16_PROFILE_SHA256, *STAGE6_PROFILE_HASHES.values(), *STAGE7_PROFILE_HASHES.values()}:
        raise ValueError(
            "Unsupported public model/profile; explicit adaptation and revalidation required"
        )
