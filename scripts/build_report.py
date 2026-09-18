#!/usr/bin/env python3
"""Derive the review report and hash-linked evidence manifest without GPU work."""

import collections
import hashlib
import json
import statistics
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from llm_stego_public_key.evaluation.budget import BudgetLedger, LIMITS

ART = ROOT / "artifacts/stage1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")


def main():
    records = [json.loads(line) for line in (ART / "cases.jsonl").read_text().splitlines()]
    ledger = BudgetLedger(ART / "budget.jsonl")
    usage, events = ledger.usage(), ledger.events()
    ledger.close()
    reservations = [e for e in events if e["event"] == "reserve"]
    unsettled = sorted(
        {e["attempt_id"] for e in reservations}
        - {e["attempt_id"] for e in events if e["event"] == "settle"}
    )
    codes = list(
        dict.fromkeys(r["tested_code_commit"] for r in records if r.get("tested_code_commit"))
    )
    kinds = {}
    for kind in ("preflight", "upstream_reference", "encrypted", "control", "replay"):
        rows = [r for r in records if r["kind"] == kind]
        kinds[kind] = {"attempted": len(rows), "successful": sum(bool(r["success"]) for r in rows)}
    encrypted = [r for r in records if r["kind"] == "encrypted"]
    failures = [r for r in records if not r["success"]]
    observer = {}
    for kind in ("encrypted", "control"):
        rows = [r for r in records if r["kind"] == kind and "observer" in r]
        observer[kind] = {
            "examined": len(rows),
            "format_positive": sum(r["observer"]["format_valid"] for r in rows),
        }
    test = ET.parse(ART / "cpu-tests-final.xml").getroot().find("testsuite")
    tests = {k: int(test.attrib[k]) for k in ("tests", "failures", "errors", "skipped")}
    timings = {}
    for phase in (
        "load_and_verify_seconds",
        "encode_seconds",
        "receiver_seconds",
        "public_inversion_seconds",
    ):
        values = [r["timings"][phase] for r in encrypted if phase in r.get("timings", {})]
        if values:
            timings[phase] = {
                "count": len(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "maximum": max(values),
            }
    wall = [r["job_elapsed_seconds"] for r in encrypted]
    # Deliberately conservative extrapolation: slowest measured job, includes cold
    # startup and independent public inversion where performed, plus 50% contingency.
    forecast = 120 * max(wall, default=0) * 1.5 / 3600
    sizes = {
        str(n): {
            "attempted": sum(r.get("payload_bytes") == n for r in encrypted),
            "recovered": sum(r.get("payload_bytes") == n and r["success"] for r in encrypted),
        }
        for n in (32, 128)
    }
    summary = {
        "schema_version": 1,
        "development_only": True,
        "novelty_gate": "unresolved",
        "comparator_readiness": "blocked_pending_audited_adapters_and_randomness",
        "tested_code_commit": codes[-1],
        "tested_code_commits": codes,
        "cpu_tests": tests,
        "hpke_known_answer_ciphertexts": 257,
        "hpke_exporter_vectors": 3,
        "by_kind": kinds,
        "by_payload_bytes": sizes,
        "independent_receiver_keys": len({r["key_id"] for r in encrypted if "key_id" in r}),
        "public_cover_contexts": len(
            {r["cover_context"] for r in encrypted if "cover_context" in r}
        ),
        "text_retokenization_passed": sum(r.get("text_retokenizes", False) for r in encrypted),
        "actual_authenticated_exact_recovery": sum(
            r["success"] and r.get("authenticated", False) for r in encrypted
        ),
        "failure_counts": dict(collections.Counter(r["failure_category"] for r in failures)),
        "failed_attempt_ids": [r["attempt_id"] for r in failures],
        "public_format_diagnostic": observer,
        "budget": dict(
            usage,
            gpu_hours=usage["seconds"] / 3600,
            limits=LIMITS,
            token_definition="ALL model-evaluated tokens, including prefill/scoring/reconstruction; an upper bound on generated tokens",
            carry_in_seconds=30,
            unsettled_reservations=unsettled,
        ),
        "gpu": {
            "name": "NVIDIA RTX 5000 Ada Generation",
            "vram_total_mib": 32760,
            "driver": "590.48.01",
            "cuda_runtime": "12.4",
            "peak_sampled_process_vram_mib": max(
                (r.get("peak_sampled_process_vram_mib") or 0 for r in records)
            ),
            "model_jobs_with_gpu_evidence": sum(r.get("gpu_verified", False) for r in records),
        },
        "encrypted_phase_timings_seconds": timings,
        "conditional_120_case_forecast_gpu_hours": forecast,
        "forecast_method": "120 times maximum measured encrypted-job wall time times 1.5; no full-matrix authorization",
        "assessment": "foundational_issues_remain"
        if failures or unsettled
        else "ready_for_external_review_not_stage2",
    }
    analyses = []
    for row in failures:
        trace = row.get("encoder_trace", {})
        detail = {
            "attempt_id": row["attempt_id"],
            "case_id": row["case_id"],
            "category": row["failure_category"],
            "first_transport_divergence": trace.get("first_transport_divergence"),
            "first_rank_divergence": row.get("first_rank_divergence"),
            "first_reconstruction_divergence": row.get("first_reconstruction_divergence"),
            "receiver_error": row.get("receiver_error", row.get("error")),
        }
        if "carrier_bytes_hex" in trace:
            raw = bytes.fromhex(trace["carrier_bytes_hex"])
            try:
                raw.decode("utf-8", "strict")
            except UnicodeDecodeError as error:
                detail["invalid_utf8"] = {
                    "first_byte_offset": error.start,
                    "end_byte_offset": error.end,
                    "reason": error.reason,
                    "nearby_hex": raw[max(0, error.start - 8) : error.end + 8].hex(),
                }
        if detail.get("invalid_utf8"):
            detail["consequence"] = (
                "Encoder produced bytes that cannot be a UTF-8 carrier; no text transmitted, no receiver success credited."
            )
        else:
            detail["consequence"] = (
                "Actual saved text changed token segmentation; ranks and reconstructed source diverged at the recorded position; authentication/delivery not credited."
            )
        analyses.append(detail)
    write(
        ART / "failure_analysis.json",
        {
            "schema_version": 1,
            "failures": analyses,
            "method": "CPU inspection of preserved traces; no model evaluation, normalization or retry",
        },
    )
    write(ART / "summary.json", summary)
    lines = [
        "# Stage 1 foundations report",
        "",
        "This package is ready for external inspection; Stage 2 is not authorized by this report. "
        + (
            "Foundational transport or runtime issues remain."
            if failures or unsettled
            else "The bounded implementation checks passed; novelty and comparator readiness remain unresolved."
        ),
        "",
        "## Repository and source identity",
        "",
        "Repository: https://github.com/mantzaris/CalgacusPublicEncryption",
        "",
        "Delivery branch: `main`. Starting commit: `7d5b2dce89b8c7463f04b3b4c7980b6b1e19dddb`.",
        "",
        f"Final tested inference/crypto code commit: `{codes[-1]}`. Earlier retained test revision: `{codes[0]}`. "
        "The first three model cases used the earlier revision. The later revision adds independent worker wall-time and parent-death guards; it leaves the model/profile/codec unchanged. "
        "The delivery commit additionally contains report tooling, documentation and evidence. Every model attempt records its exact tested revision. "
        "Use `git rev-parse HEAD` or the pushed branch for the final evidence commit; it is distinct from the tested code revision.",
        "",
        "## Implemented and reused",
        "",
        "Implemented a bounded pyhpke 0.6.5 / cryptography 46.0.7 base-mode adapter, 16-byte random message IDs, big-endian lengths, strict canonical Base64, full public-profile binding, authenticated persistent replay handling, "
        "a full-vocabulary Calgacus text codec, a saved-UTF-8 receiver boundary, independent toy tests, public format diagnostics, and persistent GPU accounting. "
        "Maximum supported payload is 128 arbitrary bytes, no padding. Public and separately keyed comparator interfaces are defined.",
        "",
        "The original MIT Calgacus notebook is preserved unchanged. Reference cases execute its original two rank functions using the existing local Llama-3-8B-Instruct Q4_K_M / llama-cpp-python 0.3.23 runtime, "
        "so they are not exact paper-environment reproductions. The main adapter explicitly changes BOS/boundary handling, strict serialization, deterministic tie order and native cache clearing. "
        "Small CUDA-preload/cache/rank practices and model assets are reused from RankCloak with attribution. See [source audit](docs/source_audit.md).",
        "",
        "## Tests and outcomes",
        "",
        f"CPU verification: **{tests['tests']} tests, {tests['failures']} failures, {tests['errors']} errors, {tests['skipped']} skipped**. "
        "The known-answer test compares all 257 published ciphertexts for the RFC 9180 A.2.1 suite, key derivation/encapsulation/shared secret/nonce and three exporter vectors. "
        "Other tests cover exact binary/empty/maximum payloads, length/framing errors, wrong key/info/AAD, corruption/truncation, replay persistence, outsider-created valid messages, ties, an independently specified inverse and serialization/special-token edge cases. "
        "The initial test-collection naming error was fixed before GPU work; its failed output is retained.",
        "",
        "| Case family | Attempts | Successful |",
        "|---|---:|---:|",
    ]
    for kind, counts in kinds.items():
        lines.append(f"| {kind} | {counts['attempted']} | {counts['successful']} |")
    lines += [
        "",
        f"Encrypted payload strata: {json.dumps(sizes, sort_keys=True)}. "
        f"Six-key requirement: {summary['independent_receiver_keys']} independent receiver key pairs; {summary['public_cover_contexts']} public cover contexts. "
        f"Exact authenticated recovery from actual UTF-8: {summary['actual_authenticated_exact_recovery']}/{len(encrypted)}. "
        f"Text retokenization agreement: {summary['text_retokenization_passed']}/{len(encrypted)}. "
        f"Fresh-process receiver replays: {kinds['replay']['successful']}/{kinds['replay']['attempted']}. "
        "Fresh receivers use only the delivered carrier, public profile/context and test private key; equality against source bytes is checked outside the receiver.",
        "",
        "Failures are never replaced. "
        + (
            json.dumps(summary["failure_counts"], sort_keys=True)
            if failures
            else "No model-case failure occurred in this allocation."
        ),
        "",
    ]
    if failures:
        lines += ["| Failed attempt | Category | First available divergence |", "|---|---|---|"]
        for r in failures:
            d = (
                r.get("encoder_trace", {}).get("first_transport_divergence")
                or r.get("first_rank_divergence")
                or r.get("first_reconstruction_divergence")
                or next(
                    (a.get("invalid_utf8") for a in analyses if a["attempt_id"] == r["attempt_id"]),
                    None,
                )
                or r.get("error")
            )
            lines.append(
                f"| `{r['attempt_id']}` | {r['failure_category']} | `{json.dumps(d, ensure_ascii=True)}` |"
            )
        lines.append("")
    lines += [
        "The per-failure consequences and invalid UTF-8 byte offsets are in `artifacts/stage1/failure_analysis.json`. The full saved texts and compact traces are in `artifacts/stage1/attempts/<immutable UUID>/`. "
        "No token-ID-only diagnostic is credited as a transport recovery. All samples are development-only and excluded from future held-out evaluation.",
        "",
        "Public inverse-format diagnostic: " + json.dumps(observer, sort_keys=True) + ". "
        "The observer uses no private key and never authenticates a tag. These few examples establish neither reliable detection nor formal concealment.",
        "",
        "## Local resources",
        "",
        f"Actual GPU: NVIDIA RTX 5000 Ada Generation, **32,760 MiB**, driver 590.48.01; CUDA runtime 12.4; "
        f"{summary['gpu']['model_jobs_with_gpu_evidence']} model jobs have PID-matched GPU samples and full 33/33-layer offload evidence. "
        f"Peak sampled process VRAM: **{summary['gpu']['peak_sampled_process_vram_mib']} MiB** (sampling may miss the true peak). "
        "The Quadro T2000 was not selected. Native logs report the selected GPU and backend flags.",
        "",
        f"Cumulative charged usage: **{usage['seconds']:.3f} seconds ({usage['seconds'] / 3600:.6f} GPU-hours), {usage['tokens']} tokens, {usage['cases']} cases**. "
        "Includes 30 conservative carry-in seconds and one pre-stage connectivity case. All model eval tokens, including source scoring, prompt prefill, reconstruction and public inversion, are charged; generated-only usage is bounded by this larger count. "
        "GPU-job wall time includes imports, asset hashing/loading, occupied CPU work and teardown. No warmup or retry is omitted. "
        f"Limits: 7,200 seconds / 25,000 tokens / 72 cases. Unsettled full-charge reservations: {len(unsettled)}. No cloud compute, paid API or fine-tuning was used.",
        "",
        "Environment, model/tokenizer hashes, quantization, native libraries, runtime versions and exact contexts are in `manifests/environment.json`, `configs/public_profile.json` and per-attempt logs. "
        "The preinstalled wheel's underlying llama.cpp source/build commit is unavailable; binary hashes pin the tested build. That limits clean-room reconstruction from source.",
        "",
        "## Security and novelty boundaries",
        "",
        "Published HPKE vectors and negative tests support implementation correctness for the selected suite. Confidentiality is inherited conditionally from HPKE, not proved anew by the LLM. "
        "HPKE base mode does not authenticate the sender; a stranger can encrypt a fresh valid message. Replay protection is application state and at-most-once delivery, not session management. "
        "No formal concealment, chosen-covertext security, prompt-based hardness, deniability, text-edit robustness, forward secrecy, traffic hiding, production readiness or publication-grade result is established. "
        "All committed recipient keys are intentionally public test material.",
        "",
        "CARTS already treats rank inversion and coordinate bijections; RankCloak covers cryptographic-artifact representations and detectability; ImageCalgacus already implements authenticated saved-artifact transport. "
        "HPKE integration or another successful round trip alone is not a novelty claim. The specific public-extraction comparison needs a focused priority search and review against the latest submitted drafts. "
        "See [novelty matrix](docs/novelty_matrix.md), [threat model](docs/threat_model.md) and [protocol](docs/protocol.md).",
        "",
        "## Skipped, blocked and recommended next work",
        "",
        "The full experiment matrix, all detector training, parameter search, larger payloads, alternative models, fine-tuning and manuscript writing were intentionally skipped. "
        "Public arithmetic and modern keyed comparator execution remain unimplemented by design. Their setup audit found backend/termination/transport work and, for the inspected RRC CLI, noncryptographic `random.Random(key)` reuse. "
        "A vetted CSPRNG/nonce adaptation would need explicit labelling and tests. Novelty and current-submission overlap remain unresolved. "
        "Inspect every failed case before any scale-up; do not silently add token filtering or normalization to this profile.",
        "",
        f"Conservative conditional forecast for 120 comparable development cases: **{forecast:.2f} local GPU-hours**, using 120 times the slowest observed encrypted-job wall time with 50% contingency. "
        "This includes the measured cold-start cost and public inversion where that job performed it. It excludes unimplemented comparator work and extra repeated receivers; it is not a full-program forecast or execution permission. "
        "The next useful work is external source/evidence review, transport-failure analysis, novelty/overlap resolution and comparator setup audit under a new bounded allocation.",
        "",
        "## Exact reproduction and evidence commands",
        "",
        "```bash",
        "python3.10 -m venv .venv",
        ".venv/bin/python -m pip install -r requirements-cpu.lock",
        ".venv/bin/python -m pytest -q",
        ".venv/bin/python -m ruff check src scripts tests",
        ".venv/bin/python scripts/verify_evidence.py",
        "```",
        "",
        "Original GPU commands (run at their recorded source revisions after CPU success):",
        "",
        "```bash",
        ".venv/bin/python scripts/run_smoke.py --max-new-cases 3",
        ".venv/bin/python scripts/run_smoke.py --max-new-cases 20",
        "```",
        "",
        "These commands continue only unattempted entries in the fixed allocation and share the persistent project ledger. "
        "On this completed bundle they perform no additional inference. Each attempt contains its exact subprocess argv/environment/input. "
        "Do not invoke workers directly or erase the ledger for a new run; independent re-execution needs a separately identified allocation under the remaining/new authorized budget. "
        "To reproduce the CPU-only summaries: `.venv/bin/python scripts/build_report.py`.",
        "",
        "`manifests/stage1_evidence.json` maps claims to tests/commands/configuration, tested source revisions and SHA-256 output files. "
        "`artifacts/stage1/summary.json` and `cases.jsonl` are machine-readable. The report and manifest are generated from retained evidence without new model work. "
        "The commit containing this report is for review; no Stage 2 work follows.",
    ]
    (ROOT / "STAGE1_FOUNDATIONS_REPORT.md").write_text("\n".join(lines) + "\n")
    links = []
    for r in records:
        if "evidence_dir" in r:
            links.append(
                {
                    "attempt_id": r["attempt_id"],
                    "claim": "case outcome in summary by_kind",
                    "tested_code_commit": r["tested_code_commit"],
                    "config": "configs/public_profile.json",
                    "command": r["evidence_dir"] + "/command.json",
                    "input": r["evidence_dir"] + "/input.json",
                    "output": r["evidence_dir"] + "/outcome.json",
                }
            )
    include = [
        "src",
        "scripts",
        "tests",
        "configs",
        "docs",
        "manifests",
        "artifacts/stage1",
        "vendor",
    ]
    files = []
    for directory in include:
        files.extend(
            p
            for p in (ROOT / directory).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix not in (".pyc", ".lock")
        )
    files += [
        ROOT / p
        for p in (
            "README.md",
            "THIRD_PARTY_NOTICES.md",
            "STAGE1_FOUNDATIONS_REPORT.md",
            "pyproject.toml",
            "requirements-cpu.lock",
            "ICISSP_2027_Public_Key_LLM_Steganography_Research_Plan.md",
        )
    ]
    excluded = {"manifests/stage1_evidence.json", "artifacts/stage1/evidence-verification.txt"}
    hashes = {
        str(p.relative_to(ROOT)): sha(p)
        for p in sorted(set(files))
        if str(p.relative_to(ROOT)) not in excluded
    }
    manifest = {
        "schema_version": 1,
        "tested_code_commit": codes[-1],
        "tested_code_commits": codes,
        "generator": ".venv/bin/python scripts/build_report.py",
        "cpu_evidence": {
            "tested_code_commit": codes[-1],
            "command": ".venv/bin/python -m pytest -q --junitxml=artifacts/stage1/cpu-tests-final.xml",
            "output": "artifacts/stage1/cpu-tests-final.xml",
            "stdout": "artifacts/stage1/cpu-tests-final.txt",
        },
        "claims": {
            "cryptography": "tests/test_crypto.py; tests/vectors/rfc9180_x25519_chacha20poly1305.json",
            "toy_inverse_transport": "tests/test_codec.py",
            "budget_enforcement": "tests/test_budget.py; tests/test_process_guard.py",
            "resource_usage": "artifacts/stage1/budget.jsonl; per-attempt gpu_samples.json",
            "starting_state": "manifests/starting_state.json",
            "novelty": "docs/novelty_matrix.md; manifests/related_materials.json",
        },
        "attempts": links,
        "files_sha256": hashes,
        "self_hash_exclusion": "This manifest and verifier stdout are excluded to avoid self-reference.",
    }
    write(ROOT / "manifests/stage1_evidence.json", manifest)
    print(json.dumps({"summary": summary, "hashed_files": len(hashes)}, indent=2))


if __name__ == "__main__":
    main()
