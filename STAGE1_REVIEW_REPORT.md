# Stage 1 review and hardening

**Engineering verdict: CONDITIONAL. Scientific novelty readiness: BLOCKED / unresolved.** The demonstrated control defects are repaired and CPU-tested. A small, explicitly gated engineering pilot is reasonable only after separate approval of this package and live revalidation of the repaired execution path. Reliable general UTF-8 transport has not been established. No Stage 2 work was executed.

Reviewed main: **`68f8d78d9c2aa6d4df005d80bbac4bb18d8d45f6`**, independently checked against `origin/main`; initial working tree was clean. No applicable `AGENTS.md` was found. Review branch: `stage1-review-hardening`. CPU-tested repair commit: **`7f60caf86f7430a19105aa5641f1003336d154b6`**. The later review-package commit adds documentation and evidence, not additional implementation changes. Main was not rewritten or updated by this review.

The full research plan, foundation report, five design/audit documents, code, frozen configurations, manifests and raw attempt records were inspected. [Baseline hashes](artifacts/stage1_review/baseline.json) identify all 207 originally tracked files. Original attempts, summaries, reports, manifests, model profile, upstream notebook and budget bytes are preserved. This report supersedes overbroad interpretations of the earlier report; it does not replace historical measurements.

## Findings, ordered by severity

| ID | Severity | Demonstrated defect or limitation | Repair and status |
|---|---|---|---|
| C01 | Critical | [BudgetLedger](src/llm_stego_public_key/evaluation/budget.py) treated a deleted/empty ledger as zero usage; parsed negative resource values; metadata could overwrite `reserved`; `TokenMeter(inf)` accepted more than 25,000 tokens. These are resource-control defects, not evidence that historical runs exceeded the ceilings. | Explicit one-time initialization; durable hashed-prefix checkpoint; immutable historical [anchor](configs/stage1_budget_anchor.json); strict types/finite bounds; protected accounting fields; no attempt refunds; closed/replaced locks rejected. Resolved in CPU tests. |
| C02 | Critical | [Worker/controller](scripts/run_smoke.py) trusted an environment attempt ID without checking a live reservation. Worker timeout started after imports, allowing delayed startup to shift the reserved deadline. Lock ownership ended with the controller rather than necessarily with the child. | [Inherited one-shot lease](src/llm_stego_public_key/evaluation/worker_lease.py), matching reservation/input hash, atomic worker claim, inherited lock lifetime, absolute controller deadline armed before heavy imports, parent-death guard, and `finally` cleanup of interrupted children. Wall overruns are charged explicitly and stop continuation. CPU subprocess tests pass; live CUDA revalidation is pending. |
| M01 | Major | Restart skipped reserved cases lacking outcomes and did not remember prior fatal stop conditions. A nonzero child exit could be credited as successful if a result file existed. Missing test keys were silently regenerated. | `validate_resume` requires complete settled history and refuses previous runtime/numerical failures. Nonzero exits retain conservative charges and fail. Missing historical keys fail closed. Resolved in CPU tests; no incomplete original attempts were found. |
| M02 | Major | Backend/profile fields such as batch size and token rules were advertised and bound, while several runtime values were hard-coded. A changed profile could therefore describe settings the loader never used. | [Exact supported-profile digest validation](src/llm_stego_public_key/profile.py) before CUDA/backend initialization. No new profile or algorithm is accepted implicitly. Unsupported batch, tie, payload and context settings are tested. Resolved for the one supported profile; live acceptance of the valid profile remains pending. |
| M03 | Major | Historical source-cleanliness checks omitted the dependency lock and vendored upstream code, ran once per invocation, and retained no per-job dirty-state snapshot. Native wheel source/build SHA is unavailable. | Check dependency lock/vendor and repeat the clean-revision check immediately before each reservation; future inputs record the checked paths/revision. Installed HPKE sources and current native/model/tokenizer assets independently match the recorded hashes. Historical missing dirty-state evidence and unknown native build SHA cannot be reconstructed retroactively; provenance remains qualified. |
| M04 | Major | Actual encrypted UTF-8 transport succeeded in only 6/12 attempts: 5/6 at 32 bytes, 1/6 at 128 bytes. Five tokenization ambiguities and one invalid UTF-8 output remain. | Retained as failures with original traces. No normalization, token filtering, silent retry or token-ID-only transport was introduced. Open limitation: the full-vocabulary profile is suitable for a diagnostic pilot, not a claim of reliable general transport. |
| N01 | Minor | The observer wrapper received the full evaluator record, including unavailable authentication outcomes, although inspection found it did not read them for classification. | A pure [public observer API](src/llm_stego_public_key/evaluation/observer.py) now accepts only codec, transmitted text and public context. A regression confirms it never authenticates a syntactically valid envelope. This is a function boundary, not an OS security sandbox. |
| N02 | Minor | The 30-second preflight carry-in has no retained raw connectivity trace. Statements that absolutely no out-of-harness warmup/retry occurred cannot be independently established from the bundle. | Preserve the conservative charge and identify it as declared carry-in, separate from 20 PID/offload-verified model jobs. No new historical evidence is invented. |

[Baseline defect reproductions](artifacts/stage1_review/baseline_defect_reproductions.json) show zero usage after ledger deletion, negative accepted accounting, metadata-overwritten reservations, and the unbounded token meter. [Regression tests](tests/test_review_hardening.py) exercise the repaired contracts, including real CPU subprocess deaths, inherited descriptor locking, duplicate worker claims, controller interruption and atomic concurrent replay rejection. Temporary subprocess stand-ins use no model or GPU; their simulated log markers are not research evidence.

The checkpoint protects accidental single-file rollback and partial writes. It is not protection against an account owner deliberately reverting all files and code. An append committed before checkpoint replacement remains conservatively charged; incomplete records, mismatched prefixes and unresolved attempts block continuation. There is no automatic repair, reset or override that resumes an ambiguous history.

## Cryptography and receiver review

The selected implementation remains `pyhpke==0.6.5` with `cryptography==46.0.7`, HPKE base mode with `(kem,kdf,aead)=(32,1,3)`. All 31 installed pyhpke source hashes match the inspected upstream provenance. The cached, pinned full CFRG vector file matches its recorded hash, and the committed fixture is its exact selected entry. The independent known-answer test covers 257 expected ciphertexts, key derivation, encapsulation/shared secret, nonce and three exporter values. [RFC 9180 A.2.1](https://www.rfc-editor.org/rfc/rfc9180.html#appendix-A.2.1) and the [pinned vector source](https://github.com/cfrg/draft-irtf-cfrg-hpke/blob/b1f7cb0cdeab6906c61b3d6574e8bdfdbe1cd3fb/test-vectors.json) are the primary references.

No cryptographic primitive or encryption/framing path was replaced. Normal `seal` obtains fresh library-generated encapsulation randomness and an OS-random 16-byte message ID. Deterministic ephemeral material appears only in published-vector tests. The inner record remains `id[16] || length_u32be || payload`, maximum 128 bytes, no padding; the complete envelope is 32-byte encapsulation plus ciphertext/tag, 68..196 bytes. Canonical standard padded Base64, 92..264 characters, is bounded before decoding and rejects alternate encodings. The public binding snapshots canonical JSON of the entire profile plus exact selected context, with a length-prefixed domain-separated `info` and digest-bound AAD.

[HPKE open](src/llm_stego_public_key/cryptography/hpke.py) authenticates before record parsing and replay insertion. Authenticated lengths must exactly match remaining bytes; malformed, wrong-key, wrong-info/AAD and modified/truncated inputs never deliver unauthenticated plaintext. Persistent SQLite replay state is inserted atomically before returning a valid payload; concurrent opens of one message deliver it once. At-most-once delivery is not guaranteed receipt after a crash. **Base mode has no sender authentication**: fresh valid encryption by a stranger is expected, not an AEAD forgery.

The [receiver](src/llm_stego_public_key/transport/receiver.py) starts from actual UTF-8 bytes, public configuration/contexts and a private key. It has no payload, expected hash, encoder ranks/IDs or cache argument. The retained replay workers have distinct PIDs from their source workers, independently start the model, read the saved carrier, and compare recovered hashes only in the controller. Three replays use three contexts but only two of the six recipient keys; they are selected successful examples, not unbiased reliability estimates.

The core [rank codec](src/llm_stego_public_key/codecs/calgacus.py), wire framing and cryptographic module remain unchanged. Ties are descending native float32 logits, ascending token ID. Context BOS and separate text tokenization, native cache clearing, full vocabulary, no EOS stop, strict UTF-8 and the 512-token/65,536-byte caps remain explicit. Detokenized text is independently retokenized. Drifted carriers are retained, never silently corrected.

The upstream notebook is still identifiable and unchanged. Its two original functions are exercised through a local wrapper that serializes evaluation and uses a different model/runtime; these are not exact paper-environment reproductions. The adapted codec deliberately differs in BOS/boundaries, tie handling, strict serialization and native cache clearing. The review did not erase these distinctions.

## Independently checked evidence and limits

[Artifact audit](artifacts/stage1_review/artifact-audit.json) and its [CPU-only script](scripts/audit_stage1.py) reconcile the historical manifest's 203 file hashes against the reviewed Git revision, all 21 case IDs and 42 budget events, worker results/outcomes, profile hashes, payload sizes/hashes, six unique recipient public keys, contexts, saved text hashes and first-failure evidence. Thirty-five encode/receiver/observer/control phase totals also reconcile with retained context/token traces. The two upstream cases' metered totals are supported by their records and wrapper source, rather than independently retokenized here.

| Claim | Review conclusion |
|---|---|
| Original CPU suite | Reproduced: 59/59 pass at baseline. |
| Review CPU suite | 109/109 pass, zero failures/errors/skips, at the repair commit above. |
| Reference / encrypted recovery | Historical evidence supports 2/2 references and 6/12 encrypted messages; no new inference performed. |
| Controls / clean-process replays | 3 ordinary controls; 3/3 selected fresh receiver replays supported by distinct process records and saved carriers. |
| Public format diagnostic | Retained extracted text reproduces 2/3 format positives on examined encrypted carriers and 0/3 controls. No private-key tag test or fitted detector. |
| Hardware | All 20 model jobs have matching worker PID/GPU UUID samples and 33/33-layer offload logs: RTX 5000 Ada, 32,760 MiB, driver 590.48.01; runtime CUDA 12.4. Sampled process peak 5,006 MiB is not an exact allocator peak. |
| Asset identity | Full existing GGUF, embedded tokenizer, six native libraries and four CUDA library hashes were rechecked on CPU. No model or CUDA library was loaded by this audit. |
| Historical resources | 632.4426544 charged seconds (0.1756785 GPU-hours), 10,230 evaluated-token charges, 21 cases. Includes declared 30-second/one-case carry-in. All recorded failures count. |
| Review resources | **0 GPU seconds, 0 generated/evaluated model tokens, 0 GPU cases.** Existing budget bytes unchanged. |
| Security | Vector/negative tests support implementation correctness and authenticated delivery under HPKE assumptions. No formal concealment, reliable detection, chosen-covertext security, sender authentication, edit robustness or publication-grade result is established. |

Old GPU results remain evidence for `c21265e9a9b31d8ee965808ceca8ef8b58cca092` (first three jobs) and `d07f5a7ee6025e7e65ac236c3dd08e2b5981beec` (remaining jobs), under the unchanged frozen model/profile. They are **not** live validation of the repaired controller, worker lease, absolute timer or profile gate. The original report's broad resource-control assurance is superseded by C01/C02/M01. The original counts are not superseded.

## Reproduction and checks

All commands below are CPU-only, including the explicit zero-case controller check:

```bash
.venv/bin/python -m pytest -q --junitxml=artifacts/stage1_review/cpu-final.xml
.venv/bin/python -m ruff check src scripts tests
.venv/bin/python -m ruff format --check src scripts tests
.venv/bin/python scripts/run_smoke.py --max-new-cases 0
.venv/bin/python scripts/audit_stage1.py
.venv/bin/python scripts/audit_stage1.py --assets
.venv/bin/python scripts/verify_stage1_review.py
```

Use `requirements-cpu.lock` for the CPU environment. `--assets` hashes already-present assets without loading an inference backend; omit it when those external files are unavailable. Review commands/outputs are linked in [commands.json](artifacts/stage1_review/commands.json); final tests, baseline tests, intermediate checks and asset audit are retained. [Review evidence manifest](artifacts/stage1_review/evidence_manifest.json) hashes the final files and identifies the tested repair commit. Re-running tests can change timing-bearing XML; write reproduction output to `/tmp` to preserve this package byte-for-byte. Historical `build_report.py` / `verify_evidence.py` belong to their recorded revisions and must not relabel repaired code as the original experiment.

## Novelty, comparators and readiness gates

Available RankCloak and ImageCalgacus manuscript hashes still match the Stage 1 records. Cached primary CARTS, Calgacus and Meteor PDFs match their recorded hashes. Targeted re-reading confirms prior overlap in rank inversion/conjugacy, cryptographic-artifact representations, authenticated saved-artifact transport and hybrid public-key/shared-secret steganography. [Material review](artifacts/stage1_review/related-materials.json) records the checked identities. Latest submitted revisions/status and a focused priority search are not established; no contribution is declared novel.

The public arithmetic and keyed comparator interfaces remain contracts only. The inspected arithmetic implementation needs a compatible backend and explicit precision, token eligibility, finite-message termination and UTF-8 handling. The inspected RRC CLI uses `random.Random(key)`; it cannot inherit a cryptographic shared-key security claim from that seed. Meteor's historical HMAC_DRBG demo also needs a reviewed port and key/nonce policy. None is silently made public, implemented or benchmarked by this review.

Required gates before the proposed pilot: external review/approval of this package; a CPU-tested fixed pilot allocation with cumulative carry-forward accounting and a no-inference dry run; unchanged asset/profile checks; and the pilot's mandatory live revalidation gate before fresh cases. Any unexpected failure of a previously successful saved carrier, budget/lease discrepancy, unexplained numerical divergence or missing GPU evidence stops execution. The specification allows only a small development diagnostic; reliable transport, comparator validity and novelty clearance are separate gates before any larger study.

See [STAGE2_PILOT_SPEC.md](STAGE2_PILOT_SPEC.md). The pilot is proposed, not authorized or executed by this report.
