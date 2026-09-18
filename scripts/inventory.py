#!/usr/bin/env python3
"""CPU-only inventory; hash existing assets without loading a model or CUDA."""

import hashlib
import importlib.metadata
import json
import platform
import subprocess
from pathlib import Path

import gguf

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def main():
    model = ROOT.parent / "llm-rankcloak/models/llama3_8b/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"
    site = ROOT.parent / "llm-rankcloak/.venv-generation-v3/lib/python3.10/site-packages"
    libs = {p.name: digest(p) for p in sorted((site / "llama_cpp/lib").glob("*.so"))}
    model_hash = digest(model)
    reader = gguf.GGUFReader(str(model), "r")
    tokenizer = hashlib.sha256()
    names = []
    for name, field in sorted(reader.fields.items()):
        if name.startswith("tokenizer."):
            names.append(name)
            raw_name = name.encode()
            tokenizer.update(len(raw_name).to_bytes(4, "big") + raw_name)
            for part in field.parts:
                raw = part.tobytes()
                tokenizer.update(len(raw).to_bytes(8, "big") + raw)
    profile = {
        "schema_version": 1,
        "protocol": "ICISSP2027-HPKE-Calgacus/v1",
        "profile_id": "llama3-8b-q4km-public-rank-v1",
        "codec": "adapted-full-vocabulary-calgacus",
        "max_payload_bytes": 128,
        "hpke": {
            "mode": 0,
            "kem_id": 32,
            "kdf_id": 1,
            "aead_id": 3,
            "implementation": "pyhpke==0.6.5",
        },
        "record": "message_id[16] || payload_length_u32be || payload; no padding",
        "serialization": "RFC4648 canonical standard Base64(enc[32] || ciphertext_and_tag)",
        "model": {
            "identity": "QuantFactory/Meta-Llama-3-8B-Instruct-GGUF",
            "file": model.name,
            "sha256": model_hash,
            "quantization": "Q4_K_M",
            "tokenizer": "embedded GGUF",
            "tokenizer_sha256": tokenizer.hexdigest(),
        },
        "backend": {
            "llama_cpp_python": "0.3.23",
            "numpy": "2.2.6",
            "native_library_sha256": libs,
            "cuda_packages": {
                "nvidia-cuda-runtime-cu12": "12.4.127",
                "nvidia-cublas-cu12": "12.4.5.8",
            },
        },
        "inference": {
            "n_ctx": 2048,
            "n_batch": 1,
            "n_ubatch": 1,
            "threads": 8,
            "n_gpu_layers": -1,
            "logits_all": True,
            "flash_attn": False,
            "logits_dtype": "float32",
            "kv_type_k": "f16",
            "kv_type_v": "f16",
            "cache": "reset and kv_cache_clear per sequence; serial prefill/eval",
            "graphs": False,
            "fusion": False,
            "cublas_compute": "32F",
            "cuda_launch_blocking": True,
            "cublas_workspace": ":4096:8",
        },
        "tokens": {
            "add_bos_to_context": True,
            "add_bos_to_text": False,
            "interpret_special_tokens": False,
            "detokenize_special_tokens": True,
            "chat_template": None,
            "boundary": "separate context and text tokenization",
            "rank_order": "descending native logits; ascending token ID for exact ties",
            "vocabulary": "full; no filtering or probability truncation",
            "normalization": "none; strict UTF-8; no strip or inserted space",
            "stop": "source token count for encoder; received token count for receiver; no EOS stop",
            "max_tokens": 512,
            "max_transport_bytes": 65536,
        },
        "source_context": "Canonical Base64 data:",
        "cover_contexts": [
            "A field note about trees in the public garden:",
            "A brief explanation of how a library organizes books:",
            "A research note about measuring afternoon rainfall:",
        ],
    }
    runtime = {
        "schema_version": 1,
        "gpu_uuid": "GPU-10d1f16f-9e79-08bb-b2ba-3353c04422cf",
        "model_path": str(model.resolve()),
        "reused_site_packages": str(site.resolve()),
    }
    env = {
        "schema_version": 1,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "gpu_inventory": command(
            "nvidia-smi",
            "--query-gpu=index,name,uuid,memory.total,memory.used,driver_version",
            "--format=csv",
        ),
        "nvidia_smi": command("nvidia-smi"),
        "cpu": command("lscpu"),
        "memory": command("free", "-b"),
        "disk": command("df", "-B1", str(ROOT)),
        "os_release": Path("/etc/os-release").read_text(),
        "cpu_packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
        "reused_inference_packages": command(
            str(site.parents[2] / "bin/python"), "-m", "pip", "freeze"
        ),
        "cuda_libraries": {
            str(p.relative_to(site)): digest(p)
            for p in sorted((site / "nvidia").glob("*/lib/*.so.*"))
        },
        "model_bytes": model.stat().st_size,
        "tokenizer_hash_method": "sorted tokenizer.* fields, u32be name length/name, each GGUFReader part u64be length/raw bytes",
        "tokenizer_fields": names,
        "gpu_inference_performed": False,
    }
    for path, obj in [
        ("configs/public_profile.json", profile),
        ("configs/local_runtime.json", runtime),
        ("manifests/environment.json", env),
    ]:
        (ROOT / path).write_text(json.dumps(obj, indent=2) + "\n")
    print(
        json.dumps(
            {
                "model_sha256": model_hash,
                "tokenizer_sha256": tokenizer.hexdigest(),
                "gpu": env["gpu_inventory"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
