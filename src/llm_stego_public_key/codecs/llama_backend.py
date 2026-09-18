"""Pinned llama.cpp adapter reusing RankCloak's CUDA preload/cache practices.

The GPU loader is intentionally separate from CPU tests and crypto imports.
"""

import ctypes
import hashlib
import importlib.metadata
import os
from pathlib import Path

import numpy as np

from ..errors import CapacityError
from ..profile import validate_supported_profile
from ..evaluation.budget import TokenMeter

FLAGS = {
    "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
    "CUDA_LAUNCH_BLOCKING": "1",
    "GGML_CUDA_DISABLE_GRAPHS": "1",
    "GGML_CUDA_DISABLE_FUSION": "1",
    "GGML_CUDA_FORCE_CUBLAS_COMPUTE_32F": "1",
    "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
}


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_model(runtime: dict, profile: dict, meter: TokenMeter):
    validate_supported_profile(profile)
    # Must be set before importing llama_cpp or loading any CUDA library.
    os.environ.update(FLAGS)
    os.environ["CUDA_VISIBLE_DEVICES"] = runtime["gpu_uuid"]
    import nvidia

    for directory in nvidia.__path__:
        for relative in (
            "cuda_runtime/lib/libcudart.so.12",
            "cublas/lib/libcublasLt.so.12",
            "cublas/lib/libcublas.so.12",
        ):
            path = Path(directory) / relative
            if path.exists():
                ctypes.CDLL(str(path), mode=ctypes.RTLD_GLOBAL)
    import llama_cpp

    if llama_cpp.__version__ != profile["backend"]["llama_cpp_python"]:
        raise RuntimeError("Wrong llama.cpp Python version")
    if np.__version__ != profile["backend"]["numpy"]:
        raise RuntimeError("Wrong NumPy version")
    if not llama_cpp.llama_supports_gpu_offload():
        raise RuntimeError("GPU offload unavailable; no CPU fallback")
    for name, digest in profile["backend"]["native_library_sha256"].items():
        if sha256_file(Path(llama_cpp.__file__).parent / "lib" / name) != digest:
            raise RuntimeError("Backend native library hash mismatch: " + name)
    for package, version in profile["backend"]["cuda_packages"].items():
        if importlib.metadata.version(package) != version:
            raise RuntimeError("Wrong CUDA runtime package: " + package)
    if sha256_file(runtime["model_path"]) != profile["model"]["sha256"]:
        raise RuntimeError("Model/tokenizer GGUF hash mismatch")
    llm = llama_cpp.Llama(
        model_path=runtime["model_path"],
        n_gpu_layers=-1,
        n_ctx=profile["inference"]["n_ctx"],
        n_batch=1,
        n_ubatch=1,
        n_threads=8,
        n_threads_batch=8,
        logits_all=True,
        flash_attn=False,
        offload_kqv=True,
        seed=1337,
        verbose=True,
    )
    return LlamaRankModel(llm, meter)


class LlamaRankModel:
    def __init__(self, llm, meter):
        self.llm = llm
        self.meter = meter
        self.context_ids = {}

    def tokenize(self, raw: bytes) -> list[int]:
        return list(map(int, self.llm.tokenize(raw, add_bos=False, special=False)))

    def detokenize(self, ids: list[int]) -> bytes:
        return self.llm.detokenize(ids, special=True)

    def eval(self, ids):
        if self.llm.n_tokens + len(ids) > self.llm.n_ctx():
            raise CapacityError("Model context capacity exceeded")
        self.meter.charge(len(ids))
        # Serial prefill and serial replay match; no batch-dependent logits.
        for token in ids:
            self.llm.eval([int(token)])

    def begin(self, context: str):
        self.llm.reset()
        self.llm._ctx.kv_cache_clear()
        ids = [self.llm.token_bos()] + self.tokenize(context.encode("utf-8"))
        self.context_ids[context] = ids
        self.eval(ids)

    def logits(self):
        # Native float32 logits; sorting does not recompute probabilities.
        return self.llm.scores[self.llm.n_tokens - 1].copy()

    def advance(self, token: int):
        self.eval([token])

    def close(self):
        self.llm.close()
