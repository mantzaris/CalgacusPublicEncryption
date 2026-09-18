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
        [
            "git",
            "diff",
            "HEAD",
            "--",
            "src",
            "scripts",
            "configs",
            "tests",
            "pyproject.toml",
            "requirements-cpu.lock",
            "vendor",
        ],
        cwd=ROOT,
    )
    unknown = subprocess.check_output(
        [
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
            "src",
            "scripts",
            "configs",
            "tests",
            "pyproject.toml",
            "requirements-cpu.lock",
            "vendor",
        ],
        cwd=ROOT,
    )
    if dirty or unknown:
        raise RuntimeError("Commit code, tests, scripts and frozen configs before GPU work")
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def initialize_inputs():
    path = ART / "TEST_ONLY_keys.json"
    if not path.exists():
        raise BudgetError("Missing historical test keys; do not silently regenerate study inputs")
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


def execute(ledger, job, runtime, code, *, artifact_root=None, reservation=None, replay_source=None, expected_rejection=False, worker_script=None):
    if revision() != code:
        raise RuntimeError("Source revision changed while the controller was running")
    artifact_root = ART if artifact_root is None else artifact_root
    remaining = {k: ledger.limits[k] - v for k, v in ledger.usage().items()}
    seconds = min(240.0, remaining["seconds"])
    tokens = min(1500, remaining["tokens"])
    if reservation is not None:
        seconds, tokens = reservation  # Full frozen reservation; never shrink to fit.
    if seconds < 30 or tokens < 64:
        raise BudgetError("Insufficient remaining reservation for another bounded job")
    aid = ledger.reserve(
        seconds, tokens, case_id=job["case_id"], kind=job["kind"], tested_code_commit=code
    )
    directory = artifact_root / "attempts" / aid
    directory.mkdir(parents=True)
    job = dict(
        job,
        schema_version=1,
        tested_code_commit=code,
        token_reservation=tokens,
        wall_reservation_seconds=seconds,
        source_provenance={
            "commit": code,
            "checked_immediately_before_reservation": True,
            "tracked_and_untracked_code_dirty": False,
            "checked_paths": [
                "src",
                "scripts",
                "configs",
                "tests",
                "pyproject.toml",
                "requirements-cpu.lock",
                "vendor",
            ],
        },
    )
    write_new(directory / "input.json", job)
    command = [sys.executable, str(worker_script or ROOT / "scripts/gpu_worker.py"), str(directory / "input.json")]
    start = time.monotonic()
    deadline = start + seconds - 8
    job_sha256 = hashlib.sha256((directory / "input.json").read_bytes()).hexdigest()
    lease_env = {
        "STAGE1_LEDGER_FD": str(ledger.lock.fileno()),
        "STAGE1_DEADLINE_MONOTONIC": str(deadline),
        "STAGE1_JOB_SHA256": job_sha256,
    }
    write_new(
        directory / "command.json",
        {
            "argv": command,
            "cwd": str(ROOT),
            "environment": {
                "PYTHONPATH": runtime["reused_site_packages"],
                "STAGE1_GOVERNED_ATTEMPT": aid,
                "STAGE1_CONTROLLER_PID": str(os.getpid()),
                "PYTHONDONTWRITEBYTECODE": "1",
                "CUDA_CACHE_DISABLE": "1",
                **lease_env,
            },
            "reservation_seconds": seconds,
        },
    )
    env = dict(
        os.environ,
        PYTHONPATH=runtime["reused_site_packages"],
        STAGE1_GOVERNED_ATTEMPT=aid,
        STAGE1_CONTROLLER_PID=str(os.getpid()),
        PYTHONDONTWRITEBYTECODE="1",
        CUDA_CACHE_DISABLE="1",
        **lease_env,
    )
    timed_out = False
    samples = []
    with (directory / "worker.log").open("x") as log:
        proc = subprocess.Popen(
            command,
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=log,
            start_new_session=True,
            pass_fds=(ledger.lock.fileno(),),
        )
        try:
            while proc.poll() is None:
                elapsed = time.monotonic() - start
                if time.monotonic() >= deadline:
                    timed_out = True
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
                    pass
                time.sleep(0.5)
        finally:
            # Includes interrupted controllers and unexpected sampling exceptions.
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            proc.wait(timeout=5)
    elapsed = time.monotonic() - start
    result_path = directory / "result.json"
    if result_path.exists() and not timed_out and proc.returncode == 0:
        record = json.loads(result_path.read_text())
        if elapsed <= seconds:
            ledger.settle(aid, elapsed, record["charged_tokens"])
        else:
            ledger.settle(aid, elapsed, tokens, overrun=True)
            record["charged_tokens"] = tokens
            record["accounting_note"] = "Wall overrun charged in full; future work blocked"
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
    if elapsed > seconds and not any(
        e["attempt_id"] == aid and e["event"] == "overrun" for e in ledger.events()
    ):
        ledger.settle(aid, elapsed, tokens, overrun=True)
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
    claim_path = directory / "worker_claim.json"
    claim = json.loads(claim_path.read_text()) if claim_path.exists() else {}
    record["lease_verified"] = (claim.get("attempt_id") == aid and claim.get("pid") == proc.pid
                                and claim.get("deadline_monotonic") == deadline)
    record["phase_meter_verified"] = sum(record.get("tokens_by_phase", {}).values()) == record["charged_tokens"]
    if not record["lease_verified"] or not record["phase_meter_verified"]:
        record["success"] = False
        record["failure_category"] = "timeout_resource_failure"
    if job["kind"] == "replay" and record["success"]:
        # The controller, not the receiver, compares the expected source digest.
        source = replay_source if replay_source is not None else next(r for r in cases() if r["attempt_id"] == job["source_attempt_id"])
        record["source_attempt_id"] = source["attempt_id"]
        record["exact_recovery"] = record["recovered_sha256"] == source["payload_sha256"]
        record["success"] = record["exact_recovery"]
        if not record["success"]:
            record["failure_category"] = "rank_numerical_divergence"
    record["provenance_verified"] = (record.get("tested_code_commit") == code
        and record.get("profile_sha256") == job.get("profile_sha256", record.get("profile_sha256"))
        and record.get("gpu_uuid") == runtime["gpu_uuid"])
    if not record["provenance_verified"]:
        record["success"] = False
        record["failure_category"] = "implementation_failure"
    if job["kind"] == "encrypted" and record.get("authenticated") and record.get("recovered_sha256") != record.get("payload_sha256"):
        record["success"] = False
        record["failure_category"] = "rank_numerical_divergence"
    if replay_source is not None:
        record["source_attempt_id"] = replay_source["attempt_id"]
    record["expected_rejection"] = expected_rejection
    record["expected_outcome_agreement"] = (
        (record.get("failure_category") == "framing_failure" and not record.get("authenticated", False)
         and record.get("error") == "Invalid Base64 length") if expected_rejection else bool(record["success"])
    ) and gpu_evidence and record["lease_verified"] and record["phase_meter_verified"] and proc.returncode == 0
    record["authenticated_message_recovery"] = bool(record.get("authenticated", False) and record["success"] and job["kind"] != "control")
    write_new(directory / "gpu_samples.json", samples)
    write_new(directory / "outcome.json", record)
    append_json(artifact_root / "cases.jsonl", record)
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


def validate_resume(ledger, rows):
    """Missing outcomes and fatal attempts remain stop conditions across restarts."""
    events = ledger.events()
    reservations = {e["attempt_id"] for e in events if e["event"] == "reserve"}
    settled = {e["attempt_id"] for e in events if e["event"] == "settle"}
    ids = [row["attempt_id"] for row in rows]
    if reservations != settled or len(ids) != len(set(ids)) or set(ids) != reservations:
        raise BudgetError(
            "Incomplete/overrun history; retain full charges and review before resuming"
        )
    fatal = {"implementation_failure", "rank_numerical_divergence", "timeout_resource_failure"}
    if any(row.get("failure_category") in fatal for row in rows):
        raise BudgetError(
            "Previous runtime/numerical failure requires review; restart is not approval"
        )


def main():
    raise RuntimeError("Stage 1 allocation is retired. Use run_pilot.py with the authoritative project ledger.")
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
    anchor = json.loads((ROOT / "configs/stage1_budget_anchor.json").read_text())
    ledger = BudgetLedger(ART / "budget.jsonl", anchor=anchor)
    validate_resume(ledger, cases())
    keys = initialize_inputs()
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
