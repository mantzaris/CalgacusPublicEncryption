#!/usr/bin/env python3
"""Local-only Stage 1 controller. Every invocation shares one persistent ledger.

Defaults: 2 upstream-reference cases, 12 HPKE transmissions, 3 controls, and up to
3 fresh receiver replays. No retries. A stopped run continues only pending cases.
"""

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from llm_stego_public_key.cryptography.hpke import generate_key_pair
from llm_stego_public_key.errors import BudgetError
from llm_stego_public_key.evaluation.budget import BudgetLedger, append_json
from llm_stego_public_key.profile import canonical_json

ART = ROOT / "artifacts/stage1"


def write_new(path, obj):
    with path.open("x") as handle:
        json.dump(obj, handle, indent=2, sort_keys=True)
        handle.write("\n")


def revision():
    # Untracked evidence is allowed; tracked code/config changes are not.
    dirty = subprocess.check_output(
        ["git", "diff", "HEAD", "--", "src", "scripts", "configs", "tests", "pyproject.toml"],
        cwd=ROOT,
    )
    unknown = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "src", "scripts", "configs", "tests"],
        cwd=ROOT,
    )
    if dirty or unknown:
        raise RuntimeError("Commit code, tests, scripts and frozen configs before GPU work")
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def initialize_inputs():
    path = ART / "TEST_ONLY_keys.json"
    if not path.exists():
        keys = []
        for i in range(6):
            sk, pk = generate_key_pair()
            keys.append(
                {
                    "key_id": f"development-{i}",
                    "TEST_ONLY_private_key_hex": sk.hex(),
                    "public_key_hex": pk.hex(),
                }
            )
        write_new(
            path,
            {
                "schema_version": 1,
                "warning": "INSECURE PUBLIC TEST MATERIAL. Never use these keys outside this development study.",
                "generation": "six independent OS-random X25519 library key pairs",
                "keys": keys,
            },
        )
    return json.loads(path.read_text())["keys"]


def observed_gpu(pid, gpu_uuid):
    out = subprocess.check_output(
        [
            "nvidia-smi",
            "--query-compute-apps=pid,gpu_uuid,used_gpu_memory",
            "--format=csv,noheader,nounits",
        ],
        text=True,
        timeout=3,
    )
    for line in out.splitlines():
        fields = [s.strip() for s in line.split(",")]
        if len(fields) == 3 and fields[:2] == [str(pid), gpu_uuid]:
            return int(fields[2])
    return None


def execute(ledger, job, runtime, code):
    remaining = {k: ledger.limits[k] - v for k, v in ledger.usage().items()}
    seconds = min(240.0, remaining["seconds"])
    tokens = min(1500, remaining["tokens"])
    if seconds < 30 or tokens < 64:
        raise BudgetError("Insufficient remaining reservation for another bounded job")
    aid = ledger.reserve(
        seconds, tokens, case_id=job["case_id"], kind=job["kind"], tested_code_commit=code
    )
    directory = ART / "attempts" / aid
    directory.mkdir(parents=True)
    job = dict(job, schema_version=1, tested_code_commit=code, token_reservation=tokens)
    write_new(directory / "input.json", job)
    command = [sys.executable, str(ROOT / "scripts/gpu_worker.py"), str(directory / "input.json")]
    write_new(
        directory / "command.json",
        {
            "argv": command,
            "cwd": str(ROOT),
            "environment": {
                "PYTHONPATH": runtime["reused_site_packages"],
                "STAGE1_GOVERNED_ATTEMPT": aid,
                "PYTHONDONTWRITEBYTECODE": "1",
                "CUDA_CACHE_DISABLE": "1",
            },
            "reservation_seconds": seconds,
        },
    )
    env = dict(
        os.environ,
        PYTHONPATH=runtime["reused_site_packages"],
        STAGE1_GOVERNED_ATTEMPT=aid,
        PYTHONDONTWRITEBYTECODE="1",
        CUDA_CACHE_DISABLE="1",
    )
    start = time.monotonic()
    timed_out = False
    samples = []
    with (directory / "worker.log").open("x") as log:
        proc = subprocess.Popen(
            command, cwd=ROOT, env=env, stdout=log, stderr=log, start_new_session=True
        )
        while proc.poll() is None:
            elapsed = time.monotonic() - start
            if elapsed >= seconds - 8:
                timed_out = True
                os.killpg(proc.pid, signal.SIGKILL)
                break
            try:
                used = observed_gpu(proc.pid, runtime["gpu_uuid"])
                if used is not None:
                    samples.append(
                        {
                            "elapsed_seconds": elapsed,
                            "used_vram_mib": used,
                            "pid": proc.pid,
                            "gpu_uuid": runtime["gpu_uuid"],
                        }
                    )
            except (subprocess.SubprocessError, ValueError):
                pass  # Absence of evidence remains explicit; not a GPU success.
            time.sleep(0.5)
        proc.wait(timeout=5)
    elapsed = time.monotonic() - start
    result_path = directory / "result.json"
    if result_path.exists() and not timed_out:
        record = json.loads(result_path.read_text())
        if elapsed <= seconds:
            ledger.settle(aid, elapsed, record["charged_tokens"])
        else:
            record["accounting_note"] = (
                "Wall time exceeded job reservation; full reservation retained"
            )
            record["success"] = False
            record["failure_category"] = "timeout_resource_failure"
    else:
        # Crash/timeout: retained reservation includes unreported work. Never zero it.
        record = {
            "schema_version": 1,
            "attempt_id": aid,
            "kind": job["kind"],
            "case_id": job["case_id"],
            "tested_code_commit": code,
            "split": "development_only",
            "success": False,
            "failure_category": "timeout_resource_failure",
            "charged_tokens": tokens,
            "error": "Worker timeout" if timed_out else "Worker exited without result",
        }
    log_text = (directory / "worker.log").read_text(errors="replace")
    gpu_evidence = bool(samples) and "offloaded 33/33 layers to GPU" in log_text
    record.update(
        job_elapsed_seconds=elapsed,
        gpu_verified=gpu_evidence,
        peak_sampled_process_vram_mib=max((s["used_vram_mib"] for s in samples), default=None),
        exit_code=proc.returncode,
        evidence_dir=str(directory.relative_to(ROOT)),
        cumulative_budget=ledger.usage(),
    )
    if not gpu_evidence:
        record["success"] = False
        record["failure_category"] = "timeout_resource_failure"
        record["gpu_evidence_error"] = "No PID-matched GPU sample or incomplete full-offload log"
    if job["kind"] == "replay" and record["success"]:
        # The controller, not the receiver, compares the expected source digest.
        source = next(r for r in cases() if r["attempt_id"] == job["source_attempt_id"])
        record["source_attempt_id"] = source["attempt_id"]
        record["exact_recovery"] = record["recovered_sha256"] == source["payload_sha256"]
        record["success"] = record["exact_recovery"]
        if not record["success"]:
            record["failure_category"] = "rank_numerical_divergence"
    write_new(directory / "gpu_samples.json", samples)
    write_new(directory / "outcome.json", record)
    append_json(ART / "cases.jsonl", record)
    print(
        json.dumps(
            {
                k: record.get(k)
                for k in [
                    "case_id",
                    "attempt_id",
                    "success",
                    "failure_category",
                    "charged_tokens",
                    "job_elapsed_seconds",
                    "cumulative_budget",
                ]
            }
        ),
        flush=True,
    )
    return record


def cases():
    p = ART / "cases.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-new-cases",
        type=int,
        default=20,
        help="Lower per-invocation cap; persistent global ceilings still apply",
    )
    args = parser.parse_args()
    if not 0 <= args.max_new_cases <= 20:
        parser.error("max-new-cases must be 0..20")
    code = revision()
    profile = json.loads((ROOT / "configs/public_profile.json").read_text())
    runtime = json.loads((ROOT / "configs/local_runtime.json").read_text())
    ledger = BudgetLedger(ART / "budget.jsonl")
    keys = initialize_inputs()
    if not ledger.events():
        aid = ledger.reserve(
            30,
            0,
            case_id="prior-connectivity-check",
            kind="preflight",
            note="Conservative carry-in for the preceding session's small PyTorch matrix and llama.cpp backend checks; no model tokens",
        )
        ledger.settle(aid, 30, 0)
        append_json(
            ART / "cases.jsonl",
            {
                "schema_version": 1,
                "attempt_id": aid,
                "case_id": "prior-connectivity-check",
                "kind": "preflight",
                "success": True,
                "split": "development_only",
                "charged_tokens": 0,
                "job_elapsed_seconds": 30,
                "accounting": "conservative carry-in, not a model transport case",
                "tested_code_commit": None,
                "gpu_model": "NVIDIA RTX 5000 Ada Generation",
            },
        )
    # Fixed balanced design: six independent receiver keys, both sizes, three contexts.
    jobs = [
        {
            "kind": "upstream_reference",
            "case_id": f"upstream-{i}",
            "context_index": i,
            "source_text": text,
        }
        for i, text in enumerate(
            [
                "The research notebook records the height of a young tree.",
                "A librarian checks the returned books before closing.",
            ]
        )
    ]
    for key_index, key in enumerate(keys):
        for size_index, size in enumerate((32, 128)):
            payload = bytes((j + 17 * key_index + size_index) % 256 for j in range(size))
            jobs.append(
                {
                    "kind": "encrypted",
                    "case_id": f"encrypted-k{key_index}-n{size}",
                    "context_index": (key_index + size_index) % 3,
                    "payload_hex": payload.hex(),
                    "key_id": key["key_id"],
                    "TEST_ONLY_private_key_hex": key["TEST_ONLY_private_key_hex"],
                    "public_observer": key_index == 0 or (key_index == 1 and size == 128),
                }
            )
    frozen = {
        "schema_version": 1,
        "allocation": {"upstream_reference": 2, "encrypted": 12, "control": 3, "replay": 3},
        "limits": {"seconds": 7200, "tokens": 25000, "cases": 72},
        "profile_sha256": hashlib.sha256(canonical_json(profile)).hexdigest(),
        "split": "development_only_excluded_from_future_heldout",
        "payload_design": "byte[j]=(j+17*key_index+size_index) mod 256; sizes 32,128",
        "context_design": "(key_index+size_index) mod 3",
        "keys": 6,
        "control_sampling": "PCG64(2026091800+context_index), temperature 1, full vocabulary, fixed matched token length; EOS does not stop",
        "replay_selection": "first successful encrypted attempt per context in fixed case order, maximum 3",
        "retry_policy": "none; all reservations (even failed/abandoned) consume a case",
    }
    if not (ART / "design.json").exists():
        write_new(ART / "design.json", frozen)
    elif json.loads((ART / "design.json").read_text()) != frozen:
        raise RuntimeError("Design drift; do not overwrite the frozen study")
    count = 0
    completed = {e["case_id"] for e in ledger.events() if e["event"] == "reserve"}
    try:
        for phase in ("core", "controls", "replays"):
            if phase != "core":
                jobs = []
                for i in range(3):
                    matches = [
                        r
                        for r in cases()
                        if r["kind"] == "encrypted"
                        and r.get("cover_context") == profile["cover_contexts"][i]
                    ]
                    if phase == "controls":
                        reference = next((r for r in matches if "carrier_tokens" in r), None)
                        jobs.append(
                            {
                                "kind": "control",
                                "case_id": f"control-{i}",
                                "context_index": i,
                                "target_tokens": reference["carrier_tokens"] if reference else 96,
                                "matched_attempt": reference["attempt_id"] if reference else None,
                                "sampling_seed": 2026091800 + i,
                            }
                        )
                    else:
                        reference = next((r for r in matches if r["success"]), None)
                        if reference:
                            key = next(k for k in keys if k["key_id"] == reference["key_id"])
                            jobs.append(
                                {
                                    "kind": "replay",
                                    "case_id": f"replay-{i}",
                                    "context_index": i,
                                    "carrier_path": reference["evidence_dir"] + "/carrier.txt",
                                    "source_attempt_id": reference["attempt_id"],
                                    "TEST_ONLY_private_key_hex": key["TEST_ONLY_private_key_hex"],
                                }
                            )
            for job in jobs:
                if job["case_id"] in completed:
                    continue
                if count >= args.max_new_cases:
                    return
                outcome = execute(ledger, job, runtime, code)
                count += 1
                if outcome["failure_category"] in (
                    "implementation_failure",
                    "rank_numerical_divergence",
                    "timeout_resource_failure",
                ):
                    print(
                        "Stopping GPU work for an unexplained/runtime failure; preserve and review.",
                        flush=True,
                    )
                    return
    except BudgetError as exc:
        print("GPU work stopped:", str(exc), flush=True)
    finally:
        ledger.close()


if __name__ == "__main__":
    main()
