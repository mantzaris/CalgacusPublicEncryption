#!/usr/bin/env python3
"""Internal bounded worker. Launch ONLY through run_smoke.py's global governor."""

import ast
import copy
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from llm_stego_public_key.evaluation.worker_lease import verify_worker_lease

# Arm the inherited controller deadline before importing NumPy, crypto or a backend.
_LEASED_JOB = (
    verify_worker_lease(Path(sys.argv[1]), ROOT / "artifacts/stage1/budget.jsonl")
    if __name__ == "__main__"
    else None
)

import numpy as np

from llm_stego_public_key.codecs.calgacus import CalgacusCodec, first_difference
from llm_stego_public_key.codecs.llama_backend import load_model
from llm_stego_public_key.cryptography.hpke import ReplayCache, deserialize, public_key, seal
from llm_stego_public_key.errors import Stage1Error, TransportError
from llm_stego_public_key.evaluation.budget import TokenMeter
from llm_stego_public_key.evaluation.observer import observe_text
from llm_stego_public_key.profile import Binding, canonical_json
from llm_stego_public_key.transport.receiver import receive


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def main():
    job_path = Path(sys.argv[1])
    directory = job_path.parent
    if _LEASED_JOB is None:
        raise RuntimeError("Use the governed controller entry point")
    job = _LEASED_JOB
    profile = json.loads((ROOT / "configs/public_profile.json").read_text())
    runtime = json.loads((ROOT / "configs/local_runtime.json").read_text())
    meter = TokenMeter(job["token_reservation"])
    record = {
        "schema_version": 1,
        "attempt_id": directory.name,
        "kind": job["kind"],
        "case_id": job["case_id"],
        "split": "development_only",
        "tested_code_commit": job["tested_code_commit"],
        "profile_sha256": sha(canonical_json(profile)),
        "pid": os.getpid(),
        "gpu_uuid": runtime["gpu_uuid"],
        "success": False,
        "timings": {},
        "failure_category": None,
    }
    model = None
    started = time.monotonic()
    codec = None
    try:
        model = load_model(runtime, profile, meter)
        record["timings"]["load_and_verify_seconds"] = time.monotonic() - started
        cover = profile["cover_contexts"][job["context_index"]]
        record["cover_context"] = cover
        binding = Binding.from_profile(profile, cover)
        codec = CalgacusCodec(
            model,
            profile["source_context"],
            profile["tokens"]["max_tokens"],
            profile["tokens"]["max_transport_bytes"],
        )
        if job["kind"] == "encrypted":
            payload = bytes.fromhex(job["payload_hex"])
            sk = bytes.fromhex(job["TEST_ONLY_private_key_hex"])
            pk = public_key(sk)
            source = seal(payload, pk, binding)
            envelope = deserialize(source)
            record.update(
                payload_bytes=len(payload),
                payload_sha256=sha(payload),
                key_id=job["key_id"],
                receiver_public_key_hex=pk.hex(),
                envelope_bytes=len(envelope),
                envelope_sha256=sha(envelope),
                serialized_base64=source,
                base64_characters=len(source),
            )
            meter.phase = "encode"
            t = time.monotonic()
            try:
                wire = codec.encode(source, cover)
            finally:
                record["timings"]["encode_seconds"] = time.monotonic() - t
                record["encoder_trace"] = copy.deepcopy(codec.trace)
            (directory / "carrier.txt").write_bytes(wire)
            record.update(
                transport_utf8=wire.decode("utf-8"),
                transport_bytes=len(wire),
                transport_sha256=sha(wire),
                carrier_tokens=len(codec.trace["carrier_ids"]),
                text_retokenizes=codec.trace["first_transport_divergence"] is None,
            )
            meter.phase = "receiver"
            t = time.monotonic()
            receiver_error = None
            try:
                # Receiver input is the actual saved file, with a new codec object.
                codec = CalgacusCodec(model, profile["source_context"])
                recovered = receive(
                    (directory / "carrier.txt").read_bytes(),
                    sk,
                    binding,
                    cover,
                    codec,
                    ReplayCache(),
                )
                record["authenticated"] = True
                record["recovered_sha256"] = sha(recovered)
                record["success"] = recovered == payload
            except Stage1Error as exc:
                receiver_error = exc
                record["authenticated"] = False
            finally:
                record["receiver_trace"] = copy.deepcopy(codec.trace)
                record["timings"]["receiver_seconds"] = time.monotonic() - t
            enc, dec = record["encoder_trace"], record["receiver_trace"]
            record["first_rank_divergence"] = first_difference(
                enc["source_ranks"], dec.get("received_ranks", [])
            )
            record["first_reconstruction_divergence"] = first_difference(
                enc["source_ids"], dec.get("reconstructed_ids", [])
            )
            if receiver_error:
                record["receiver_error"] = str(receiver_error)
                record["failure_category"] = receiver_error.category
            if not record["text_retokenizes"]:
                record["failure_category"] = "tokenization_serialization_drift"
                record["success"] = False
            elif not record["success"] and (
                record["first_rank_divergence"] or record["first_reconstruction_divergence"]
            ):
                record["failure_category"] = "rank_numerical_divergence"
            if job.get("public_observer"):
                public_observer(
                    codec, (directory / "carrier.txt").read_bytes(), cover, meter, record
                )
        elif job["kind"] == "replay":
            # Deliberately no source payload, expected digest, ranks, or token IDs here.
            wire = (ROOT / job["carrier_path"]).read_bytes()
            sk = bytes.fromhex(job["TEST_ONLY_private_key_hex"])
            meter.phase = "fresh_receiver"
            t = time.monotonic()
            try:
                recovered = receive(wire, sk, binding, cover, codec, ReplayCache())
                record.update(
                    success=True,
                    authenticated=True,
                    recovered_sha256=sha(recovered),
                    recovered_bytes=len(recovered),
                    transport_sha256=sha(wire),
                )
            finally:
                record["receiver_trace"] = copy.deepcopy(codec.trace)
                record["timings"]["receiver_seconds"] = time.monotonic() - t
        elif job["kind"] == "control":
            meter.phase = "ordinary_control"
            t = time.monotonic()
            model.begin(cover)
            rng = np.random.Generator(np.random.PCG64(job["sampling_seed"]))
            ids = []
            for _ in range(job["target_tokens"]):
                values = model.logits().astype(np.float64)
                probabilities = np.exp(values - values.max())
                probabilities /= probabilities.sum()
                token = int(rng.choice(len(probabilities), p=probabilities))
                ids.append(token)
                model.advance(token)
            wire = model.detokenize(ids)
            record["control_ids"] = ids
            record["timings"]["control_seconds"] = time.monotonic() - t
            try:
                record["transport_utf8"] = wire.decode("utf-8", "strict")
            except UnicodeError as exc:
                record["carrier_bytes_hex"] = wire.hex()
                raise TransportError("Control was not UTF-8") from exc
            (directory / "carrier.txt").write_bytes(wire)
            record.update(
                success=True,
                carrier_tokens=len(ids),
                transport_bytes=len(wire),
                text_retokenizes=model.tokenize(wire) == ids,
                transport_sha256=sha(wire),
                sampling_seed=job["sampling_seed"],
            )
            public_observer(codec, wire, cover, meter, record)
        elif job["kind"] == "upstream_reference":
            run_upstream(model, meter, job, directory, cover, record)
        else:
            raise ValueError("Unknown job kind")
    except Exception as exc:
        record["success"] = False
        record["failure_category"] = getattr(exc, "category", "implementation_failure")
        record["error"] = str(exc)
        record["exception_type"] = type(exc).__name__
        if codec is not None:
            record["last_trace"] = copy.deepcopy(codec.trace)
        traceback.print_exc()
    finally:
        if model:
            record["public_context_token_ids"] = model.context_ids
            model.close()
        record.update(
            charged_tokens=meter.tokens,
            tokens_by_phase=meter.by_phase,
            worker_seconds=time.monotonic() - started,
        )
        dump(directory / "result.json", record)


def public_observer(codec, wire, cover, meter, record):
    meter.phase = "public_inversion"
    t = time.monotonic()
    record["observer"] = observe_text(codec, wire, cover)
    if "extracted_text" in record["observer"]:
        record["observer"]["extracted_sha256"] = sha(
            record["observer"]["extracted_text"].encode("utf-8")
        )
    record["observer_trace"] = copy.deepcopy(codec.trace)
    record["timings"]["public_inversion_seconds"] = time.monotonic() - t


def run_upstream(model, meter, job, directory, cover, record):
    # Execute ONLY the two audited function definitions from cell 10. No installs,
    # downloads, notebook presets or initialization cells are executed.
    notebook = json.loads(
        (
            ROOT / "vendor/calgacus/LLMs_can_hide_text_in_other_text_of_the_same_length.ipynb"
        ).read_text()
    )
    tree = ast.parse("".join(notebook["cells"][10]["source"]))
    definitions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    namespace = {"np": np, "List": list, "Llama": object}
    exec(
        compile(ast.Module(body=definitions, type_ignores=[]), "upstream_cell_10", "exec"),
        namespace,
    )

    class MeteredOriginal:
        def __getattr__(self, name):
            return getattr(model.llm, name)

        def eval(self, ids):
            model.eval(ids)

    proxy = MeteredOriginal()
    ranks_fn, decode_fn = namespace["get_token_ranks_llama_cpp"], namespace["decode_from_ranks"]
    source = job["source_text"]
    source_context = "A text:"
    meter.phase = "upstream_encode"
    t = time.monotonic()
    ranks, _ = ranks_fn(source, proxy, source_context)
    wire, _ = decode_fn(cover, ranks, proxy)
    record["timings"]["encode_seconds"] = time.monotonic() - t
    (directory / "carrier.txt").write_bytes(wire.encode("utf-8"))
    meter.phase = "upstream_text_receiver"
    t = time.monotonic()
    observed, _ = ranks_fn((directory / "carrier.txt").read_bytes().decode("utf-8"), proxy, cover)
    reconstructed, _ = decode_fn(source_context, observed, proxy)
    record["timings"]["receiver_seconds"] = time.monotonic() - t
    record.update(
        source_text=source,
        source_context=source_context,
        source_ranks=ranks,
        receiver_ranks=observed,
        first_rank_divergence=first_difference(ranks, observed),
        reconstructed_text=reconstructed,
        transport_utf8=wire,
        transport_sha256=sha(wire.encode()),
        carrier_tokens=len(ranks),
        success=reconstructed == source,
        method_label="unchanged upstream cell-10 functions, adapted local model/runtime",
    )
    if reconstructed != source:
        record["failure_category"] = (
            "rank_numerical_divergence" if ranks == observed else "tokenization_serialization_drift"
        )


if __name__ == "__main__":
    main()
