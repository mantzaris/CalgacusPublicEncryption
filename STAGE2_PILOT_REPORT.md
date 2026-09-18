# Stage 2 bounded local-GPU diagnostic pilot

**Executed the authorized fixed pilot and stopped.** The mandatory replay gate agreed in 4/4 cases: three exact authenticated recoveries and one expected framing rejection. Fresh recovery was 2/2 at 32 bytes and 2/2 at 128 bytes. Both ordinary controls and both selected fresh-process replays completed. This validates these execution paths and examples; reliable general text transport remains unestablished because the preserved Stage 1 serialization failures remain material.

## Baseline, authorization and source

Repository: https://github.com/mantzaris/CalgacusPublicEncryption. Branch: `main` throughout. Starting commit: `24fd553e6b79fcfdbe7dc6b6abca71cac440ea8a` with a clean working tree. Applicable [AGENTS.md](AGENTS.md) requires direct commits/pushes to main. No branches were created or history rewritten. Historical reports, Stage 1 artifacts, review artifacts, profiles, manifests and core `src/` code are unchanged.

GPU-tested code and frozen-allocation commit: **`5d53916e31171a69de04f5108c5cfe8bb5cc4bf7`**. Every reservation and job records this revision and a clean source check immediately before launch. The later evidence/report commit contains the results and an artifact-only reconciler; no GPU results are attributed to that later revision. [Evidence manifest](artifacts/stage2_pilot/evidence_manifest.json) connects individual attempts to commands, inputs, outputs and configuration hashes.

The user explicitly waived another full CPU/static-check cycle and authorized this pilot. The existing **109 CPU tests** at `7f60caf86f7430a19105aa5641f1003336d154b6` were reused as historical evidence. **No new full pytest suite, lint/formatting sweep, CPU benchmark, environment, or literature review was run.** The new extension received only five focused admission/allocation checks (fixed reservations, exact limit, one over each resource limit), asset checks, diff review, actual GPU execution and retained-artifact reconciliation. Historical test results are not credited to the new controller.

## Minimal implementation and safeguards

[run_pilot.py](scripts/run_pilot.py) supplies the fixed allocation, full reservations, additional-delta ceilings, mandatory replay gate, selection rules and persistent terminal status. It reuses the Stage 1 `execute` helper, ledger, lease, pre-import absolute deadline and token meter. [prepare_pilot.py](scripts/prepare_pilot.py) performs host-only identity verification, ledger migration and one-time random test-key/allocation preparation. The original `run_smoke.py` launch command is retired; the worker accepts the single project ledger/lock. No model, codec, token order, tokenizer, contexts, cryptography, framing or sampling algorithm changed. The codec remains the adapted full-vocabulary Calgacus profile; this pilot adds no unmodified-upstream examples. Worker changes are ledger selection and additional replay diagnostics; the controller also checks lease, phase totals, source/profile/GPU provenance, and evaluator-side recovered hashes.

The entire 10608-byte historical ledger prefix was copied byte-for-byte while holding its old lock, verified by SHA-256 `3ce4afa608815a52578b688952ed220e2362999a9a533ec63fac6dfcada73bbf`. The authoritative ledger is now [artifacts/project_budget.jsonl](artifacts/project_budget.jsonl), using `artifacts/project_budget.lock` and its durable prefix checkpoint. [Migration record](artifacts/stage2_pilot/migration.json) preserves prior usage and the anchor. There is no reset or independent new allocation ledger. Incomplete attempts retain reservations; unexpected/fatal outcomes and completed/stopped status prohibit automatic continuation. The OS-account owner can still deliberately change all files; these are cooperating-process controls, not a hostile-user sandbox.

Reservations remained 60 s / 600 tokens for historical replays, 120 s / 2,000 tokens for fresh encrypted cases, 90 s / 1,200 tokens for controls, and 60 s / 750 tokens for new replays. Each reservation fit both ceilings before launch. The worker deadline is eight seconds inside the wall reservation and is armed before heavy imports. No lowered reservations, discretionary retries, separate warmups or out-of-controller inference occurred. Startup, imports, model verification/load and shutdown are included in conservative job wall time. All model-evaluated tokens in source scoring, context prefill, carrier generation, receivers, controls and public inversion are charged.

## Rediscovered hardware and frozen method

The connected supported device was **NVIDIA RTX 5000 Ada Generation**, UUID `GPU-10d1f16f-9e79-08bb-b2ba-3353c04422cf`, **32760 MiB VRAM**, driver **590.48.01**. The separate Quadro T2000 was not selected. All 12 processes have PID-matched samples on the supported UUID and logs reporting **33/33 layers offloaded**. Peak sampled per-process memory was **5006 MiB**; this is sampled usage, not a continuous peak measurement.

The existing RankCloak local environment was reused without rebuilding or downloading: llama-cpp-python 0.3.23, NumPy 2.2.6, CUDA runtime 12.4.127, cuBLAS 12.4.5.8. Model: QuantFactory Meta-Llama-3-8B-Instruct Q4_K_M, GGUF SHA-256 `86c8ea6c8b755687d0b723176fcd0b2411ef80533d23e2a5030f845d13ab2db7`; embedded tokenizer SHA-256 `5c8950bef385be95db5feda8c8afadba6a5c0b903e6ceaa39efe6cfe3d84f3f3`. All six backend and four CUDA library hashes matched the existing records. Exact platform, interpreter, paths, versions and hashes are in [environment.json](artifacts/stage2_pilot/environment.json). The native build-source SHA remains historically unavailable; no rebuild was attempted.

[Public profile](configs/public_profile.json) is unchanged: full vocabulary, Q4_K_M weights, float32 logits with ascending token-ID ties, f16 KV, batch/microbatch 1, serial prefill, native/Python cache clearing, no chat template, no token filtering, no normalization, strict UTF-8, no EOS stopping, full GPU offload and the existing deterministic backend flags. Source context is `Canonical Base64 data:`. Exact cover contexts are:

- 0: `A field note about trees in the public garden:`
- 1: `A brief explanation of how a library organizes books:`
- 2: `A research note about measuring afternoon rainfall:`

Two independent new OS-random recipient key pairs are explicitly public, insecure **TEST_ONLY** material. Payload byte `j` for key `u`, length `n` is `(167 + 29*u + 7*j + n) mod 256`. Order/contexts were A32/0, A128/1, B32/2, B128/0. Each encryption used fresh library encapsulation randomness and a fresh random message ID; payload and ciphertext hashes are in the raw results. HPKE and inner record remain base mode X25519/HKDF-SHA256/ChaCha20-Poly1305, `message_id[16] || length_u32be || payload`, no padding, canonical Base64 of complete encapsulation and ciphertext/tag. Envelopes are 100 and 196 bytes respectively.

## Measured outcomes

Planned: **12**. Attempted: **12**. Recorded outcomes: **12**. Unused slots: **0**. Historical carriers are kept separate from fresh transmissions. Expected rejection is not a recovered message; ordinary generated controls are not encrypted-message recoveries.

| Case | Family | Outcome | Public format | Charged tokens | Job seconds | Evidence |
|---|---|---|---|---:|---:|---|
| pilot-historical-0 | historical_replay | exact authenticated recovery | — | 201 | 21.351 | [outcome](artifacts/stage2_pilot/attempts/467c9100-538a-4aa0-b54a-a083efe7c768/outcome.json) |
| pilot-historical-1 | historical_replay | exact authenticated recovery | — | 386 | 26.762 | [outcome](artifacts/stage2_pilot/attempts/b64e8424-8265-477d-b247-83337b47c455/outcome.json) |
| pilot-historical-2 | historical_replay | exact authenticated recovery | — | 207 | 22.464 | [outcome](artifacts/stage2_pilot/attempts/c6bb3df0-09f8-4e7f-a31c-2ff9c3e50915/outcome.json) |
| pilot-historical-3 | historical_replay | expected framing rejection | — | 387 | 26.733 | [outcome](artifacts/stage2_pilot/attempts/a93ac2e7-00b2-420c-a250-7fa62360d1ed/outcome.json) |
| pilot-k0-n32 | fresh_encrypted | exact authenticated recovery | true | 675 | 35.182 | [outcome](artifacts/stage2_pilot/attempts/eeb0c599-59dd-41ce-996f-bbd6775b40c8/outcome.json) |
| pilot-k0-n128 | fresh_encrypted | exact authenticated recovery | true | 1188 | 49.657 | [outcome](artifacts/stage2_pilot/attempts/dd57b386-a4e2-46a1-b75a-5d864eabbb89/outcome.json) |
| pilot-k1-n32 | fresh_encrypted | exact authenticated recovery | true | 585 | 33.062 | [outcome](artifacts/stage2_pilot/attempts/38bb3a58-18f1-414f-8478-ea3c071b2d72/outcome.json) |
| pilot-k1-n128 | fresh_encrypted | exact authenticated recovery | true | 1185 | 52.854 | [outcome](artifacts/stage2_pilot/attempts/c2ec252a-199e-4c84-9979-70f56659f976/outcome.json) |
| pilot-control-0 | control | ordinary UTF-8 generated | false | 340 | 24.548 | [outcome](artifacts/stage2_pilot/attempts/c2581d80-40af-48b4-9e18-abf3ca9ce492/outcome.json) |
| pilot-control-1 | control | ordinary UTF-8 generated | false | 597 | 31.469 | [outcome](artifacts/stage2_pilot/attempts/d79c3b77-f3ed-4919-92e9-5a16a0a58960/outcome.json) |
| pilot-fresh-replay-0 | fresh_replay | exact authenticated recovery | — | 225 | 22.959 | [outcome](artifacts/stage2_pilot/attempts/cd876b13-57a1-46db-a631-2d229387b2de/outcome.json) |
| pilot-fresh-replay-1 | fresh_replay | exact authenticated recovery | — | 195 | 22.961 | [outcome](artifacts/stage2_pilot/attempts/e61508e1-4d58-4ccf-a057-9c9ac3d328e8/outcome.json) |

The three positive historical receivers recovered hashes identical to the original payload hashes. The negative carrier was rejected with **Invalid Base64 length**, without authentication/plaintext delivery. Its first transport/rank/reconstruction differences, computed outside the receiver against the original debug traces, are retained in [compact_traces.json](artifacts/stage2_pilot/compact_traces.json): `{"ranks": {"index": 35, "intended": 453, "observed": 180}, "reconstruction": {"index": 35, "intended": 11328, "observed": 3971}, "transport": {"index": 35, "intended": 98968, "observed": 101722}}`. This reproduces the known serialization failure; it is not a new numerical failure.

All four new carriers were valid UTF-8 and retokenized to their intended token sequences. Their receivers authenticated and returned exact bytes. This is a development sample of four messages and only two independent recipient keys. It does not supersede the earlier 6/12 Stage 1 recovery record.

Controls used full-vocabulary temperature-one sampling, fixed token count and no EOS stop:

- `pilot-control-0`: 104 tokens, cover 0, PCG64 seed 2026091901, matched carrier `eeb0c599-59dd-41ce-996f-bbd6775b40c8`; UTF-8 generated, public format result `False`.
- `pilot-control-1`: 189 tokens, cover 1, PCG64 seed 2026091902, matched carrier `dd57b386-a4e2-46a1-b75a-5d864eabbb89`; UTF-8 generated, public format result `False`.

The replay selection rule chose the first successful new carrier per key, hence both fresh replays used the 32-byte carriers. The receiver jobs contain saved carrier paths, public context/profile, test private key and execution metadata; they contain no original payload, expected digest, ranks, token IDs, encoder cache or source-attempt identifier. Hash comparison occurs in the parent controller after receiver exit. Each replay starts its own model/process. The new 128-byte messages were not independently replayed; the mandatory historical 128-byte carrier was.

The public-only observer received codec, text and public cover context. It recognized canonical bounded ciphertext format in 4/4 fresh carriers and 0/2 ordinary controls. It never received private keys, ground-truth labels or authentication outcomes and never verified a tag. The artifact reconciler independently recomputes that syntax predicate from retained extraction text. These are diagnostic examples with no trained detector or reliable performance estimate.

## Resource accounting and retained failures

| Resource | Prior usage | Incremental pilot | Cumulative | Pilot ceiling | Project ceiling |
|---|---:|---:|---:|---:|---:|
| Conservative GPU-job seconds | 632.442654400 | 370.002754137 | 1002.445408537 | 1,200 | 7,200 |
| Model-evaluated tokens | 10,230 | 6,171 | 16,401 | 8,000 | 25,000 |
| Cases | 21 | 12 | 33 | 12 | 72 |

Incremental time: **0.102779 GPU-job hours**; cumulative **0.278457 hours**. All reservations, settlements, outcomes, phase totals and checkpoint hashes reconcile. **22 phase charges** were independently reconstructed from retained token traces plus public context tokens. All workers exited cleanly with unique one-shot leases, deadlines and process IDs. No crashes, abandoned attempts, accounting overruns, timeouts, unexpected authentication failures, new serialization failures or unexplained numerical divergences occurred. The single negative replay remains a retained framing failure and an expected diagnostic outcome. Original failures were not erased or retried. Historical cumulative usage still includes the declared 30-second carry-in whose original raw connectivity trace is unavailable.

Stop reason: **Fixed allocation exhausted; no further GPU work**. No additional inference is authorized by the presence of unused time/tokens. The full research matrix was not run.

## Commands and evidence verification

Commands actually used from the repository root, with the existing local `.venv`:

```sh
.venv/bin/python scripts/prepare_pilot.py > artifacts/stage2_pilot/preparation.txt 2>&1
.venv/bin/python scripts/run_pilot.py --allocation-check > artifacts/stage2_pilot/allocation_check.txt
git commit -m "Add fixed local GPU pilot with shared cumulative reservations"
.venv/bin/python scripts/run_pilot.py > artifacts/stage2_pilot/controller.log 2>&1
.venv/bin/python artifacts/stage2_pilot/reconcile.py > artifacts/stage2_pilot/reconciliation_output.txt
```

The allocation and preparation are one-shot and refuse regeneration/resumption of the completed pilot. Reproduce the evidence reconciliation with the last command; it performs no model inference. Future GPU work requires a separately authorized allocation and must carry forward the existing ledger. Per-worker exact argv, environment, input hash, PID and deadline are in each attempt's `command.json` and `worker_claim.json`. The original saved carriers are referenced directly for historical replay, and each new transmitted text is retained verbatim in `carrier.txt` and raw records. No token-only transport or hidden normalization was used.

The [summary](artifacts/stage2_pilot/summary.json), [cases](artifacts/stage2_pilot/cases.jsonl), [reconciliation](artifacts/stage2_pilot/reconciliation.json), [terminal status](artifacts/stage2_pilot/run_status.json), traces and manifest are derived from retained attempts. Every item is **development-only and excluded from future held-out evaluation**, including historical replays, new payloads, keys, contexts, families and controls.

## Interpretation and next work

**Execution readiness: the reviewed controller/lease/profile path now has successful live GPU evidence for this fixed allocation. General transport readiness remains conditional.** No execution repair is indicated by these outcomes. The sample establishes exact recovery and authentication outcomes for the listed carriers only. Cryptographic confidentiality relies on the established HPKE construction and its previously reviewed implementation, not on the cover prompt or these GPU observations. HPKE base mode provides no sender authentication: another public sender may create a fresh valid ciphertext. This pilot establishes none of concealment, edit robustness, formal security, publication-grade recovery/detection performance or novelty.

**Recommended next step: a separately reviewed transport-design study addressing the already demonstrated detokenization/retokenization failures before expanding the experiment matrix.** These four successes do not explain away the prior five tokenization ambiguities and one invalid UTF-8 output. Any proposed profile change must be explicit and newly validated; preserve the current baseline. A same-profile diagnostic job here took at most 52.854 seconds, so a forecast for any separately planned small allocation can conservatively use about 80 seconds per fresh encode/receive/public-invert job, retaining full reservations and actual evaluated-token accounting; this does not forecast an unimplemented new codec.

Novelty/manuscript overlap and comparator implementation/security assumptions remain unresolved and were not reopened. No shared steganographic key may be made public while retaining its original security claims. No comparator, detector training, fine-tuning, cloud resource, paid inference API, new model, CPU model inference or larger study was launched.
