# Stage 1 foundations report

This package is ready for external inspection; Stage 2 is not authorized by this report. Foundational transport or runtime issues remain.

## Repository and source identity

Repository: https://github.com/mantzaris/CalgacusPublicEncryption

Working branch: `stage1-foundations`. Starting commit: `7d5b2dce89b8c7463f04b3b4c7980b6b1e19dddb`.

Final tested inference/crypto code commit: `d07f5a7ee6025e7e65ac236c3dd08e2b5981beec`. Earlier retained test revision: `c21265e9a9b31d8ee965808ceca8ef8b58cca092`. The first three model cases used the earlier revision. The later revision adds independent worker wall-time and parent-death guards; it leaves the model/profile/codec unchanged. The delivery commit additionally contains report tooling, documentation and evidence. Every model attempt records its exact tested revision. Use `git rev-parse HEAD` or the pushed branch for the final evidence commit; it is distinct from the tested code revision.

## Implemented and reused

Implemented a bounded pyhpke 0.6.5 / cryptography 46.0.7 base-mode adapter, 16-byte random message IDs, big-endian lengths, strict canonical Base64, full public-profile binding, authenticated persistent replay handling, a full-vocabulary Calgacus text codec, a saved-UTF-8 receiver boundary, independent toy tests, public format diagnostics, and persistent GPU accounting. Maximum supported payload is 128 arbitrary bytes, no padding. Public and separately keyed comparator interfaces are defined.

The original MIT Calgacus notebook is preserved unchanged. Reference cases execute its original two rank functions using the existing local Llama-3-8B-Instruct Q4_K_M / llama-cpp-python 0.3.23 runtime, so they are not exact paper-environment reproductions. The main adapter explicitly changes BOS/boundary handling, strict serialization, deterministic tie order and native cache clearing. Small CUDA-preload/cache/rank practices and model assets are reused from RankCloak with attribution. See [source audit](docs/source_audit.md).

## Tests and outcomes

CPU verification: **59 tests, 0 failures, 0 errors, 0 skipped**. The known-answer test compares all 257 published ciphertexts for the RFC 9180 A.2.1 suite, key derivation/encapsulation/shared secret/nonce and three exporter vectors. Other tests cover exact binary/empty/maximum payloads, length/framing errors, wrong key/info/AAD, corruption/truncation, replay persistence, outsider-created valid messages, ties, an independently specified inverse and serialization/special-token edge cases. The initial test-collection naming error was fixed before GPU work; its failed output is retained.

| Case family | Attempts | Successful |
|---|---:|---:|
| preflight | 1 | 1 |
| upstream_reference | 2 | 2 |
| encrypted | 12 | 6 |
| control | 3 | 3 |
| replay | 3 | 3 |

Encrypted payload strata: {"128": {"attempted": 6, "recovered": 1}, "32": {"attempted": 6, "recovered": 5}}. Six-key requirement: 6 independent receiver key pairs; 3 public cover contexts. Exact authenticated recovery from actual UTF-8: 6/12. Text retokenization agreement: 6/12. Fresh-process receiver replays: 3/3. Fresh receivers use only the delivered carrier, public profile/context and test private key; equality against source bytes is checked outside the receiver.

Failures are never replaced. {"tokenization_serialization_drift": 6}

| Failed attempt | Category | First available divergence |
|---|---|---|
| `12de85ea-3e3e-4a4a-8997-27e551978366` | tokenization_serialization_drift | `{"actual": 101722, "expected": 98968, "position": 35}` |
| `78f24dcd-bb0c-48a3-86d7-48ef679fbd91` | tokenization_serialization_drift | `{"actual": 28196, "expected": 2933, "position": 29}` |
| `835167cc-56a8-4d18-84f8-331427060ac9` | tokenization_serialization_drift | `{"actual": 20214, "expected": 65992, "position": 38}` |
| `21732f7e-11f4-48da-8b5c-2f7b622a7770` | tokenization_serialization_drift | `{"first_byte_offset": 353, "end_byte_offset": 355, "reason": "invalid continuation byte", "nearby_hex": "8081e695b8e5b08be6ad6f6c6b69656e202e"}` |
| `0f10b587-db34-4a42-b02f-fdd809c27583` | tokenization_serialization_drift | `{"actual": 270, "expected": 37943, "position": 10}` |
| `93f18293-da63-40ab-800c-82fbe6b11d2c` | tokenization_serialization_drift | `{"actual": 25968, "expected": 1541, "position": 27}` |

The per-failure consequences and invalid UTF-8 byte offsets are in `artifacts/stage1/failure_analysis.json`. The full saved texts and compact traces are in `artifacts/stage1/attempts/<immutable UUID>/`. No token-ID-only diagnostic is credited as a transport recovery. All samples are development-only and excluded from future held-out evaluation.

Public inverse-format diagnostic: {"control": {"examined": 3, "format_positive": 0}, "encrypted": {"examined": 3, "format_positive": 2}}. The observer uses no private key and never authenticates a tag. These few examples establish neither reliable detection nor formal concealment.

## Local resources

Actual GPU: NVIDIA RTX 5000 Ada Generation, **32,760 MiB**, driver 590.48.01; CUDA runtime 12.4; 20 model jobs have PID-matched GPU samples and full 33/33-layer offload evidence. Peak sampled process VRAM: **5006 MiB** (sampling may miss the true peak). The Quadro T2000 was not selected. Native logs report the selected GPU and backend flags.

Cumulative charged usage: **632.443 seconds (0.175679 GPU-hours), 10230 tokens, 21 cases**. Includes 30 conservative carry-in seconds and one pre-stage connectivity case. All model eval tokens, including source scoring, prompt prefill, reconstruction and public inversion, are charged; generated-only usage is bounded by this larger count. GPU-job wall time includes imports, asset hashing/loading, occupied CPU work and teardown. No warmup or retry is omitted. Limits: 7,200 seconds / 25,000 tokens / 72 cases. Unsettled full-charge reservations: 0. No cloud compute, paid API or fine-tuning was used.

Environment, model/tokenizer hashes, quantization, native libraries, runtime versions and exact contexts are in `manifests/environment.json`, `configs/public_profile.json` and per-attempt logs. The preinstalled wheel's underlying llama.cpp source/build commit is unavailable; binary hashes pin the tested build. That limits clean-room reconstruction from source.

## Security and novelty boundaries

Published HPKE vectors and negative tests support implementation correctness for the selected suite. Confidentiality is inherited conditionally from HPKE, not proved anew by the LLM. HPKE base mode does not authenticate the sender; a stranger can encrypt a fresh valid message. Replay protection is application state and at-most-once delivery, not session management. No formal concealment, chosen-covertext security, prompt-based hardness, deniability, text-edit robustness, forward secrecy, traffic hiding, production readiness or publication-grade result is established. All committed recipient keys are intentionally public test material.

CARTS already treats rank inversion and coordinate bijections; RankCloak covers cryptographic-artifact representations and detectability; ImageCalgacus already implements authenticated saved-artifact transport. HPKE integration or another successful round trip alone is not a novelty claim. The specific public-extraction comparison needs a focused priority search and review against the latest submitted drafts. See [novelty matrix](docs/novelty_matrix.md), [threat model](docs/threat_model.md) and [protocol](docs/protocol.md).

## Skipped, blocked and recommended next work

The full experiment matrix, all detector training, parameter search, larger payloads, alternative models, fine-tuning and manuscript writing were intentionally skipped. Public arithmetic and modern keyed comparator execution remain unimplemented by design. Their setup audit found backend/termination/transport work and, for the inspected RRC CLI, noncryptographic `random.Random(key)` reuse. A vetted CSPRNG/nonce adaptation would need explicit labelling and tests. Novelty and current-submission overlap remain unresolved. Inspect every failed case before any scale-up; do not silently add token filtering or normalization to this profile.

Conservative conditional forecast for 120 comparable development cases: **2.48 local GPU-hours**, using 120 times the slowest observed encrypted-job wall time with 50% contingency. This includes the measured cold-start cost and public inversion where that job performed it. It excludes unimplemented comparator work and extra repeated receivers; it is not a full-program forecast or execution permission. The next useful work is external source/evidence review, transport-failure analysis, novelty/overlap resolution and comparator setup audit under a new bounded allocation.

## Exact reproduction and evidence commands

```bash
python3.10 -m venv .venv
.venv/bin/python -m pip install -r requirements-cpu.lock
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src scripts tests
.venv/bin/python scripts/verify_evidence.py
```

Original GPU commands (run at their recorded source revisions after CPU success):

```bash
.venv/bin/python scripts/run_smoke.py --max-new-cases 3
.venv/bin/python scripts/run_smoke.py --max-new-cases 20
```

These commands continue only unattempted entries in the fixed allocation and share the persistent project ledger. On this completed bundle they perform no additional inference. Each attempt contains its exact subprocess argv/environment/input. Do not invoke workers directly or erase the ledger for a new run; independent re-execution needs a separately identified allocation under the remaining/new authorized budget. To reproduce the CPU-only summaries: `.venv/bin/python scripts/build_report.py`.

`manifests/stage1_evidence.json` maps claims to tests/commands/configuration, tested source revisions and SHA-256 output files. `artifacts/stage1/summary.json` and `cases.jsonl` are machine-readable. The report and manifest are generated from retained evidence without new model work. The commit containing this report is for review; no Stage 2 work follows.
