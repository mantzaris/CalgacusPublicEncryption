#!/usr/bin/env python3
"""CPU-only integrity/reconciliation of the complete Stage 1 review package."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from llm_stego_public_key.cryptography.hpke import ReplayCache, open_message
from llm_stego_public_key.evaluation.budget import BudgetLedger, LIMITS
from llm_stego_public_key.profile import Binding, canonical_json


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    manifest = json.loads((ROOT / "manifests/stage1_evidence.json").read_text())
    require(manifest["schema_version"] == 1, "Unknown manifest schema")
    for name, expected in manifest["files_sha256"].items():
        path = ROOT / name
        require(path.is_relative_to(ROOT), "Path outside repository")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, "Hash mismatch: " + name)
    source_paths = [
        "src",
        "tests",
        "configs",
        "scripts/gpu_worker.py",
        "scripts/run_smoke.py",
        "scripts/inventory.py",
        "pyproject.toml",
        "requirements-cpu.lock",
    ]
    diff = subprocess.check_output(
        ["git", "diff", manifest["tested_code_commit"], "--", *source_paths], cwd=ROOT
    )
    unknown = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", *source_paths], cwd=ROOT
    )
    require(not diff and not unknown, "Current tested code/config differs from recorded revision")
    art = ROOT / "artifacts/stage1"
    ledger = BudgetLedger(art / "budget.jsonl")
    events, usage = ledger.events(), ledger.usage()
    ledger.close()
    for key in LIMITS:
        require(usage[key] <= LIMITS[key], "Resource ceiling exceeded")
    reserves = {e["attempt_id"]: e for e in events if e["event"] == "reserve"}
    settlements = {e["attempt_id"]: e for e in events if e["event"] == "settle"}
    rows = [json.loads(s) for s in (art / "cases.jsonl").read_text().splitlines()]
    require(len(rows) == len({r["attempt_id"] for r in rows}), "Duplicate attempt ID")
    require(
        set(reserves) == {r["attempt_id"] for r in rows},
        "A reservation is missing its case outcome",
    )
    profile = json.loads((ROOT / "configs/public_profile.json").read_text())
    keys = json.loads((art / "TEST_ONLY_keys.json").read_text())
    require("TEST" in keys["warning"], "Test key material not visibly labelled")
    public_keys = {k["public_key_hex"] for k in keys["keys"]}
    require(len(public_keys) == 6, "Expected six independent test recipient keys")
    for row in rows:
        aid = row["attempt_id"]
        require(row["schema_version"] == 1, "Unknown case schema")
        require(row["case_id"] == reserves[aid]["case_id"], "Case/ledger mismatch")
        if aid in settlements:
            require(
                row["charged_tokens"] == settlements[aid]["charged"]["tokens"],
                "Token accounting mismatch",
            )
            require(
                abs(row["job_elapsed_seconds"] - settlements[aid]["charged"]["seconds"]) < 1e-6,
                "Time accounting mismatch",
            )
        if row["kind"] == "preflight":
            continue
        folder = ROOT / row["evidence_dir"]
        require(
            json.loads((folder / "outcome.json").read_text()) == row, "Outcome/ledger row mismatch"
        )
        job = json.loads((folder / "input.json").read_text())
        require(job["tested_code_commit"] == row["tested_code_commit"], "Tested revision mismatch")
        require(
            row["profile_sha256"] == hashlib.sha256(canonical_json(profile)).hexdigest(),
            "Profile drift",
        )
        if "transport_sha256" in row:
            raw = (
                (folder / "carrier.txt").read_bytes()
                if row["kind"] != "replay"
                else (ROOT / job["carrier_path"]).read_bytes()
            )
            require(
                hashlib.sha256(raw).hexdigest() == row["transport_sha256"], "Transport file drift"
            )
            raw.decode("utf-8", "strict")
        if row["success"]:
            require(row["gpu_verified"], "Unverified GPU success")
            require(
                bool(json.loads((folder / "gpu_samples.json").read_text())), "Missing GPU samples"
            )
        if row["kind"] == "encrypted":
            payload = bytes.fromhex(job["payload_hex"])
            require(
                hashlib.sha256(payload).hexdigest() == row["payload_sha256"],
                "Payload digest mismatch",
            )
            binding = Binding.from_profile(profile, row["cover_context"])
            recovered = open_message(
                row["serialized_base64"],
                bytes.fromhex(job["TEST_ONLY_private_key_hex"]),
                binding,
                ReplayCache(),
            )
            require(
                recovered == payload,
                "Retained sealed input does not authenticate to the declared payload",
            )
            if row["success"]:
                require(
                    row["text_retokenizes"] and row["authenticated"], "False text-transport success"
                )
                require(row["first_rank_divergence"] is None, "Successful case has rank divergence")
                require(
                    row["first_reconstruction_divergence"] is None,
                    "Successful case has source divergence",
                )
                require(row["recovered_sha256"] == row["payload_sha256"], "False recovery equality")
        if row["kind"] == "replay":
            require(
                not {
                    "payload_hex",
                    "source_text",
                    "source_ranks",
                    "source_ids",
                    "serialized_base64",
                }.intersection(job),
                "Receiver was supplied diagnostic side information",
            )
        if "observer" in row:
            require(
                row["observer"]["authenticated"] is False,
                "Public observer claims tag authentication",
            )
    summary = json.loads((art / "summary.json").read_text())
    for key in LIMITS:
        require(summary["budget"][key] == usage[key], "Summary budget mismatch")
    for kind, counts in summary["by_kind"].items():
        selected = [r for r in rows if r["kind"] == kind]
        require(
            counts
            == {"attempted": len(selected), "successful": sum(r["success"] for r in selected)},
            "Summary outcome mismatch",
        )
    print(
        f"PASS: {len(manifest['files_sha256'])} file hashes; {len(rows)} immutable cases; "
        f"source revisions, transport hashes, test HPKE inputs, receiver boundary and budgets reconciled."
    )
    print(json.dumps(usage, sort_keys=True))


if __name__ == "__main__":
    main()
