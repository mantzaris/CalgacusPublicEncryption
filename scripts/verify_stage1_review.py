#!/usr/bin/env python3
"""Verify current review evidence without rewriting historical records or using a GPU."""

import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from audit_stage1 import audit, require

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "artifacts/stage1_review"


def main():
    summary = json.loads((REVIEW / "review_summary.json").read_text())
    manifest = json.loads((REVIEW / "evidence_manifest.json").read_text())
    require(summary["schema_version"] == manifest["schema_version"] == 1, "Unknown schema")
    for name, expected in manifest["files_sha256"].items():
        path = ROOT / name
        require(path.resolve().is_relative_to(ROOT), "Evidence path outside repository")
        require(
            hashlib.sha256(path.read_bytes()).hexdigest() == expected,
            "Review hash mismatch: " + name,
        )
    paths = ["src", "scripts", "tests", "configs", "pyproject.toml", "requirements-cpu.lock"]
    diff = subprocess.check_output(
        ["git", "diff", summary["tested_code_commit"], "--", *paths], cwd=ROOT
    )
    unknown = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "--", *paths], cwd=ROOT
    )
    require(not diff and not unknown, "Current implementation differs from the CPU-tested revision")
    historical = audit()
    require(historical["budget"] == summary["historical_gpu_usage"], "Historical usage changed")
    require(
        summary["review_gpu_usage"] == {"seconds": 0, "tokens": 0, "cases": 0},
        "Review claims GPU work",
    )
    suite = ET.parse(REVIEW / "cpu-final.xml").getroot().find("testsuite")
    counts = {k: int(suite.attrib[k]) for k in ("tests", "failures", "errors", "skipped")}
    require(counts == summary["cpu_tests"], "Review CPU counts mismatch")
    require(
        counts["tests"] >= 109 and not any(counts[k] for k in ("failures", "errors", "skipped")),
        "CPU verification failed",
    )
    print(
        f"PASS: {len(manifest['files_sha256'])} review hashes; {counts['tests']} CPU tests; "
        "21 historical cases reconciled; original evidence and GPU ledger unchanged."
    )
    print(
        "No live GPU validation performed for the repaired revision; readiness gates remain explicit."
    )


if __name__ == "__main__":
    main()
