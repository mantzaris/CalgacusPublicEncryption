#!/usr/bin/env python3
"""Independent CPU-only reconciliation of immutable historical Stage 1 artifacts.

Does not load llama.cpp/CUDA, mutate the Stage 1 ledger, or claim new live recovery.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from llm_stego_public_key.cryptography.hpke import ReplayCache, open_message, public_key
from llm_stego_public_key.evaluation.observer import public_format_test
from llm_stego_public_key.profile import Binding, canonical_json


def require(value, message):
    if not value:
        raise RuntimeError(message)


def read(path):
    return json.loads((ROOT / path).read_text())


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def audit(check_assets=False):
    baseline = read("artifacts/stage1_review/baseline.json")
    base = baseline["reviewed_main_commit"]
    for name, expected in baseline["files_sha256"].items():
        original = subprocess.check_output(["git", "show", f"{base}:{name}"], cwd=ROOT)
        require(
            hashlib.sha256(original).hexdigest() == expected, "Baseline source mismatch: " + name
        )
        if name.startswith(("artifacts/stage1/", "manifests/", "vendor/")) or name in (
            "STAGE1_FOUNDATIONS_REPORT.md",
            "configs/public_profile.json",
            "configs/local_runtime.json",
            "ICISSP_2027_Public_Key_LLM_Steganography_Research_Plan.md",
        ):
            require(digest(ROOT / name) == expected, "Historical evidence changed: " + name)
    manifest = read("manifests/stage1_evidence.json")
    for name, expected in manifest["files_sha256"].items():
        require(baseline["files_sha256"][name] == expected, "Historical manifest/source mismatch")
    profile = read("configs/public_profile.json")
    runtime = read("configs/local_runtime.json")
    rows = [json.loads(s) for s in (ROOT / "artifacts/stage1/cases.jsonl").read_text().splitlines()]
    events = [
        json.loads(s) for s in (ROOT / "artifacts/stage1/budget.jsonl").read_text().splitlines()
    ]
    require(len(rows) == len({r["attempt_id"] for r in rows}), "Duplicate case UUID")
    reservations = {e["attempt_id"]: e for e in events if e["event"] == "reserve"}
    settlements = {e["attempt_id"]: e for e in events if e["event"] == "settle"}
    require(len(events) == 2 * len(rows), "Missing/extra ledger events")
    require(
        set(reservations) == set(settlements) == {r["attempt_id"] for r in rows},
        "Unaccounted attempt",
    )
    expected_cases = {"prior-connectivity-check", "upstream-0", "upstream-1"}
    expected_cases |= {f"encrypted-k{k}-n{n}" for k in range(6) for n in (32, 128)}
    expected_cases |= {f"{kind}-{k}" for kind in ("control", "replay") for k in range(3)}
    require({r["case_id"] for r in rows} == expected_cases, "Frozen allocation differs")
    jobs = {}
    usage_at = {}
    for e in events:
        require(e["schema_version"] == 1, "Event schema")
        aid = e["attempt_id"]
        if e["event"] == "reserve":
            require(aid not in jobs, "Repeated reservation")
            jobs[aid] = e["reserved"]
        else:
            charge = e["charged"]
            require(all(0 <= charge[k] <= jobs[aid][k] for k in charge), "Charge out of bounds")
            require(charge["cases"] == 1, "Attempt refunded")
            jobs[aid] = charge
            usage_at[aid] = {k: sum(j[k] for j in jobs.values()) for k in charge}
    usage = {k: sum(j[k] for j in jobs.values()) for k in ("seconds", "tokens", "cases")}
    by_kind = defaultdict(lambda: {"attempted": 0, "successful": 0})
    strata = defaultdict(lambda: {"attempted": 0, "recovered": 0})
    observer = defaultdict(lambda: {"examined": 0, "format_positive": 0})
    failures = Counter()
    key_ids = set()
    covers = set()
    pids = set()
    replays = []
    peak = 0
    profile_hash = hashlib.sha256(canonical_json(profile)).hexdigest()
    phase_reconciliations = 0
    for row in rows:
        aid = row["attempt_id"]
        by_kind[row["kind"]]["attempted"] += 1
        by_kind[row["kind"]]["successful"] += int(row["success"])
        require(row["split"] == "development_only", "Split leakage")
        require(row["charged_tokens"] == settlements[aid]["charged"]["tokens"], "Token mismatch")
        require(
            row["job_elapsed_seconds"] == settlements[aid]["charged"]["seconds"], "Time mismatch"
        )
        if row["kind"] == "preflight":
            continue
        folder = ROOT / row["evidence_dir"]
        job = json.loads((folder / "input.json").read_text())
        result = json.loads((folder / "result.json").read_text())
        require(json.loads((folder / "outcome.json").read_text()) == row, "Outcome mismatch")
        for key, value in result.items():
            require(row[key] == value, "Worker result changed: " + key)
        require(job["tested_code_commit"] == row["tested_code_commit"], "Source revision mismatch")
        require(
            row["tested_code_commit"] in manifest["tested_code_commits"], "Unknown live revision"
        )
        require(row["cumulative_budget"] == usage_at[aid], "Cumulative accounting mismatch")
        require(row["profile_sha256"] == profile_hash, "Profile mismatch")
        require(
            sum(row["tokens_by_phase"].values()) == row["charged_tokens"], "Phase tokens mismatch"
        )
        require(row["worker_seconds"] <= row["job_elapsed_seconds"], "Worker time exceeds charge")
        require(
            sum(row["timings"].values()) <= row["worker_seconds"] + 0.01,
            "Operation time inconsistency",
        )
        require(row["exit_code"] == 0 and row["pid"] not in pids, "Process evidence inconsistent")
        pids.add(row["pid"])
        samples = json.loads((folder / "gpu_samples.json").read_text())
        require(
            samples
            and all(
                s["pid"] == row["pid"] and s["gpu_uuid"] == runtime["gpu_uuid"] for s in samples
            ),
            "GPU samples do not match worker",
        )
        log = (folder / "worker.log").read_text()
        require(
            "offloaded 33/33 layers to GPU" in log and "RTX 5000 Ada" in log,
            "GPU offload/model evidence missing",
        )
        peak = max(peak, max(s["used_vram_mib"] for s in samples))
        if "transport_sha256" in row:
            wire_path = (
                ROOT / job["carrier_path"] if row["kind"] == "replay" else folder / "carrier.txt"
            )
            require(digest(wire_path) == row["transport_sha256"], "Transport hash mismatch")
            wire_path.read_bytes().decode("utf-8", "strict")
        if row["kind"] == "encrypted":
            source = bytes.fromhex(job["payload_hex"])
            sk = bytes.fromhex(job["TEST_ONLY_private_key_hex"])
            cache = ReplayCache()
            try:
                opened = open_message(
                    row["serialized_base64"],
                    sk,
                    Binding.from_profile(profile, row["cover_context"]),
                    cache,
                )
            finally:
                cache.close()
            require(opened == source, "Recorded HPKE input does not recover recorded payload")
            require(public_key(sk).hex() == row["receiver_public_key_hex"], "Wrong public key")
            require(hashlib.sha256(source).hexdigest() == row["payload_sha256"], "Payload hash")
            require(
                len(source) == row["payload_bytes"] and row["envelope_bytes"] == len(source) + 68,
                "Payload/envelope length",
            )
            strata[str(len(source))]["attempted"] += 1
            strata[str(len(source))]["recovered"] += int(row["success"])
            key_ids.add(row["receiver_public_key_hex"])
            covers.add(row["cover_context"])
            trace = row["encoder_trace"]
            if "first_transport_divergence" in trace:
                same = trace["carrier_ids"] == trace["retokenized_ids"]
                require(same == row["text_retokenizes"], "Retokenization claim mismatch")
            if row["success"]:
                require(
                    row["authenticated"]
                    and row["text_retokenizes"]
                    and row["recovered_sha256"] == row["payload_sha256"],
                    "Unsupported recovery",
                )
                require(
                    trace["source_ids"] == row["receiver_trace"]["reconstructed_ids"],
                    "Reconstruction mismatch",
                )
            else:
                failures[row["failure_category"]] += 1
                if "first_transport_divergence" not in trace:
                    try:
                        bytes.fromhex(trace["carrier_bytes_hex"]).decode("utf-8")
                    except UnicodeDecodeError:
                        pass
                    else:
                        raise RuntimeError("Claimed invalid UTF-8 is valid")
            contexts = row["public_context_token_ids"]
            expected = (
                len(contexts[profile["source_context"]])
                + len(contexts[row["cover_context"]])
                + 2 * len(trace["source_ids"])
            )
            require(expected == row["tokens_by_phase"]["encode"], "Encode phase token undercharge")
            phase_reconciliations += 1
        if row["kind"] in ("encrypted", "replay", "control"):
            for phase, name in (
                ("receiver", "receiver_trace"),
                ("fresh_receiver", "receiver_trace"),
                ("public_inversion", "observer_trace"),
            ):
                if phase not in row["tokens_by_phase"]:
                    continue
                trace = row[name]
                contexts = row["public_context_token_ids"]
                expected = (
                    len(contexts[profile["source_context"]])
                    + len(contexts[row["cover_context"]])
                    + 2 * len(trace["received_ids"])
                )
                require(expected == row["tokens_by_phase"][phase], "Receiver/observer undercharge")
                phase_reconciliations += 1
        if row["kind"] == "control":
            require(job["target_tokens"] == row["carrier_tokens"], "Control length mismatch")
            expected = (
                len(row["public_context_token_ids"][row["cover_context"]]) + row["carrier_tokens"]
            )
            require(expected == row["tokens_by_phase"]["ordinary_control"], "Control undercharge")
            phase_reconciliations += 1
        if row["kind"] == "replay":
            require(
                not (
                    {
                        "payload_hex",
                        "expected_payload",
                        "encoder_trace",
                        "source_ranks",
                        "source_ids",
                    }
                    & set(job)
                ),
                "Receiver side information",
            )
            original = next(r for r in rows if r["attempt_id"] == job["source_attempt_id"])
            require(
                row["pid"] != original["pid"]
                and row["recovered_sha256"] == original["payload_sha256"],
                "Replay evidence invalid",
            )
            command = json.loads((folder / "command.json").read_text())
            require(
                command["argv"][1].endswith("scripts/gpu_worker.py"),
                "Replay is not a new worker process",
            )
            replays.append(
                {
                    "attempt_id": aid,
                    "pid": row["pid"],
                    "source_pid": original["pid"],
                    "source_attempt_id": original["attempt_id"],
                }
            )
        if "observer" in row:
            obs = row["observer"]
            require(obs["authenticated"] is False, "Observer authenticates")
            if "extracted_text" in obs:
                require(
                    public_format_test(obs["extracted_text"])["format_valid"]
                    == obs["format_valid"],
                    "Format claim mismatch",
                )
            observer[row["kind"]]["examined"] += 1
            observer[row["kind"]]["format_positive"] += int(obs["format_valid"])
    summary = read("artifacts/stage1/summary.json")
    for actual, key in [
        (dict(by_kind), "by_kind"),
        (dict(strata), "by_payload_bytes"),
        (dict(failures), "failure_counts"),
        (dict(observer), "public_format_diagnostic"),
    ]:
        require(actual == summary[key], "Summary mismatch: " + key)
    require(all(usage[k] == summary["budget"][k] for k in usage), "Budget summary mismatch")
    require(
        len(key_ids) == 6 and len(covers) == 3 and len(replays) == 3 and peak == 5006,
        "Coverage/hardware mismatch",
    )
    xml = ET.parse(ROOT / "artifacts/stage1/cpu-tests-final.xml").getroot().find("testsuite")
    require(
        int(xml.attrib["tests"]) == 59
        and all(int(xml.attrib[k]) == 0 for k in ("errors", "failures", "skipped")),
        "Historical CPU claim",
    )
    import pyhpke

    provenance = read("manifests/upstream_sources.json")
    for name, expected in provenance["pyhpke"]["installed_source_sha256"].items():
        require(digest(Path(pyhpke.__file__).parent / name) == expected, "Installed HPKE differs")
    vectors = json.loads((ROOT / "tests/vectors/rfc9180_x25519_chacha20poly1305.json").read_text())
    cached = Path("/tmp/stage1-hpke-vectors/test-vectors.json")
    vector_match = "unavailable cached full upstream file; fixture hash checked"
    require(
        digest(ROOT / "tests/vectors/rfc9180_x25519_chacha20poly1305.json")
        == provenance["hpke-vectors"]["selected_fixture_sha256"],
        "Vector fixture mismatch",
    )
    if cached.exists():
        require(
            digest(cached) == provenance["hpke-vectors"]["full_vector_file_sha256"],
            "Full vector source changed",
        )
        selected = [
            v
            for v in json.loads(cached.read_text())
            if tuple(v[k] for k in ("mode", "kem_id", "kdf_id", "aead_id")) == (0, 32, 1, 3)
        ]
        require(selected == vectors, "Fixture is not exact upstream selection")
        vector_match = "exact published entry checked against pinned full upstream file"
    assets = {"checked": False}
    if check_assets:
        import gguf

        model = Path(runtime["model_path"])
        require(digest(model) == profile["model"]["sha256"], "Model changed")
        reader = gguf.GGUFReader(str(model), "r")
        h = hashlib.sha256()
        for name, field in sorted(reader.fields.items()):
            if name.startswith("tokenizer."):
                raw = name.encode()
                h.update(len(raw).to_bytes(4, "big") + raw)
                for part in field.parts:
                    raw = part.tobytes()
                    h.update(len(raw).to_bytes(8, "big") + raw)
        require(h.hexdigest() == profile["model"]["tokenizer_sha256"], "Tokenizer changed")
        site = Path(runtime["reused_site_packages"])
        for name, expected in profile["backend"]["native_library_sha256"].items():
            require(digest(site / "llama_cpp/lib" / name) == expected, "Native backend changed")
        for name, expected in read("manifests/environment.json")["cuda_libraries"].items():
            require(digest(site / name) == expected, "CUDA library changed")
        assets = {
            "checked": True,
            "model_sha256": profile["model"]["sha256"],
            "tokenizer_sha256": h.hexdigest(),
            "native_and_cuda_hashes": "matched; no libraries loaded",
        }
    return {
        "schema_version": 1,
        "reviewed_main_commit": base,
        "status": "PASS",
        "historical_file_hashes": len(baseline["files_sha256"]),
        "historical_manifest_hashes": len(manifest["files_sha256"]),
        "by_kind": dict(by_kind),
        "by_payload_bytes": dict(strata),
        "failure_counts": dict(failures),
        "budget": usage,
        "phase_token_reconciliations": phase_reconciliations,
        "public_format_diagnostic": dict(observer),
        "fresh_process_replays": replays,
        "unique_receiver_public_keys": len(key_ids),
        "peak_sampled_vram_mib": peak,
        "gpu_jobs_with_pid_offload_evidence": len(pids),
        "live_gpu_revalidation_performed": False,
        "vectors": vector_match,
        "cpu_package_versions": {
            n: importlib.metadata.version(n) for n in ("pyhpke", "cryptography", "numpy", "pytest")
        },
        "assets": assets,
        "evidence_limits": [
            "Preflight 30 seconds is declared conservative carry-in, without a retained raw connectivity trace.",
            "Historical controller checked selected code paths, not dependency lock/vendor; no per-job dirty diff retained.",
            "No new GPU recovery is claimed; recorded traces and authenticated source fixtures are reconciled on CPU.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", action="store_true")
    args = parser.parse_args()
    print(json.dumps(audit(args.assets), indent=2, sort_keys=True))
