# Stage 3: bounded qualification of public text-stable rank transport

**Verdict: bounded engineering qualification passed.** This authorized allocation is complete and stopped. Historical-envelope fixtures: **2/2 exact recoveries**. Fresh encrypted payloads: **2/2 at 32 bytes, 2/2 at 128 bytes**. Independent 128-byte receiver processes: **2/2 exact authenticated recoveries**. These are development-only engineering observations, not concealment, general reliability, novelty or publication-grade security results.

## Baseline and implementation

Repository: https://github.com/mantzaris/CalgacusPublicEncryption. Work, commits and normal pushes use `main` as required by [AGENTS.md](AGENTS.md). Actual starting revision: **`54a57067e4c44dd0937950fe1e86d721489b7064`**, initially clean. Previous GPU-tested implementation: `5d53916e31171a69de04f5108c5cfe8bb5cc4bf7`. Stage 3 GPU-tested source and frozen-allocation commit: **`6f78518d69e5e3f0bea80db94b9885a9daaa47e7`**. The later report/evidence commit is distinct and is not claimed as the GPU-tested source.

The original Calgacus codec, public profile, HPKE implementation, GPU backend, previous worker, historical reports and historical case artifacts are unchanged. The new [PublicUtf8Rank16Codec](src/llm_stego_public_key/codecs/public_utf8_rank16.py) implements the existing `PublicEnvelopeCodec` interface under [public_utf8_rank16_v1](configs/public_utf8_rank16_v1.json), registered by exact canonical profile digest **`b3a106424d9e0e8b1c6d19ec7061d13a07a9a0871d0a92d5bb3dd1296b6156a6`**. The existing profile remains separately accepted; arbitrary profiles remain rejected. The only shared controller change permits the explicitly selected new leased worker. Accounting, absolute deadlines, process guards, model loading and token metering are reused.

The [transport specification](docs/transport_profile_v1.md) defines all framing, candidate selection and stopping details. A four-byte unsigned big-endian envelope length precedes the unchanged raw encapsulation plus ciphertext/tag. Each byte becomes high nibble then low nibble. At each position the first 16 admissible IDs among at most the top 128 descending-logit/ascending-ID candidates encode symbols 0..15. Metadata special/control IDs (mask 27) and empty pieces are excluded. Admission requires strict UTF-8 of the full proposed prefix and exact retokenization to the proposed IDs. No normalization, token-only transport, enlarged pool, changed radix or profile search occurred.

The decoder independently recomputes the list from its preceding received prefix. It validates the bounded 68..196-byte length and exact total received token count before allocating the envelope buffer; incomplete frames, trailing symbols and invalid token choices are rejected. Limits remain 512 carrier tokens, 65,536 bytes and a 2,048-token model context. Candidate checks perform host tokenization, not speculative inference; their elapsed cost remains inside GPU-job time.

Small compatible MIT helpers were inspected in local ImageCalgacus at `2bec65dbe5509623f6658d8a231ec93f6d579b4e` and RankCloak at `ce853d42d6ba64065cb63c6bdfc0d825c62734cd`. Full-prefix consistency, attribute exclusions and high-nibble ordering were adapted with [attribution](THIRD_PARTY_NOTICES.md) and the retained ImageCalgacus license. The environment record preserves exact helper hashes and local tree state; RankCloak had unrelated cover-letter edits, untouched here. No probability/static filter, image coder, secret-key claim or expected-length receiver interface was imported. No broad source, dependency, literature or novelty audit was repeated.

## Cryptographic and receiver boundaries

Fresh cases use the established HPKE base suite X25519/HKDF-SHA256/ChaCha20-Poly1305, existing 16-byte random identifier, u32be payload length, payload and no padding. Two new independent TEST_ONLY recipient keys and fresh OS/library HPKE randomness were used. The full **new** profile, including its codec identifier, framing/selection constants and selected public cover context, enters the existing length-delimited HPKE information and associated-data binding. Canonical Base64 is only the existing wrapper's internal bridge to raw envelope bytes; it is not the new wire representation.

The receiver begins with saved UTF-8, public profile/context and a test private key. It does not receive original envelopes/payloads, expected lengths/hashes, token IDs, rank lists, encoder caches or diagnostic traces. Fresh-process jobs have unique PIDs/leases, start their own model and compare recovered hashes outside the receiver. Authentication remains before plaintext delivery. HPKE base mode **does not authenticate a sender**; a different public sender may create a fresh valid ciphertext.

The two fixtures re-encode the saved historical **envelopes**, not the old carrier text. Their original HPKE profile binding is unchanged, and no new-profile authentication claim is made for them. New exact envelope recovery does not repair or relabel either old failure.

## Actual GPU and focused verification

Rediscovered hardware: **NVIDIA RTX 5000 Ada Generation**, UUID `GPU-10d1f16f-9e79-08bb-b2ba-3353c04422cf`, **32760 MiB VRAM**, driver **590.48.01**. All 10 jobs have PID-matched samples and **33/33-layer GPU-offload** logs. Peak sampled per-process VRAM: **5006 MiB**; sampling does not establish a continuous peak.

The existing local RankCloak environment was reused without rebuild/download: QuantFactory Meta-Llama-3-8B-Instruct Q4_K_M; GGUF SHA-256 `86c8ea6c8b755687d0b723176fcd0b2411ef80533d23e2a5030f845d13ab2db7`; embedded tokenizer hash `5c8950bef385be95db5feda8c8afadba6a5c0b903e6ceaa39efe6cfe3d84f3f3`; llama-cpp-python 0.3.23; NumPy 2.2.6; CUDA runtime 12.4.127 and cuBLAS 12.4.5.8. All six native and four CUDA binary hashes matched. Native build-source SHA remains historically unavailable. Precision, batch/microbatch 1, serial evaluation, cache clearing, no chat template and deterministic backend settings are unchanged. Exact hardware, OS, interpreter, asset hashes and public contexts are linked in [environment.json](artifacts/stage3_transport/environment.json) and the frozen profile. The legacy source context field is explicitly unused by this byte-envelope comparator.

Only **7 focused new-codec tests** and **5 fixed-allocation/admission checks** were run. Independent literal wire fixtures test high-nibble order and inverse decoding; additional checks cover maximum/out-of-range lengths, truncation, trailing data, invalid choices, ties, special/empty/invalid/noncanonical candidates, exhaustion and unregistered profiles. They passed. No full pytest suite, lint/formatting sweep, CPU benchmark, new environment or general dependency audit was run. Historical CPU results are not attributed to the new codec.

## Results and actual text transport

Planned **10**, attempted **10**, recorded **10**, unused **0**. The fixed order was two fixtures; A32/0, A128/1, B32/2, B128/0; two 128-byte receiver replays; two matched controls. Fresh payload byte `j` is `(193 + 31*u + 11*j + n) mod 256`, frozen before inference. All material is development-only and excluded from future held-out evaluation.

| Case | Outcome | Carrier tokens | Evaluated tokens | Job seconds | Evidence |
|---|---|---:|---:|---:|---|
| rank16-fixture-0 | exact envelope recovery (fixture) | 400 | 818 | 45.877 | [outcome](artifacts/stage3_transport/attempts/b1047479-0b2c-4a26-bedd-b819aafcc9ca/outcome.json) |
| rank16-fixture-1 | exact envelope recovery (fixture) | 400 | 818 | 45.924 | [outcome](artifacts/stage3_transport/attempts/7f758cd4-bea8-4765-947a-7dd433da341a/outcome.json) |
| rank16-k0-n32 | exact authenticated recovery | 208 | 657 | 36.799 | [outcome](artifacts/stage3_transport/attempts/1514528d-2e90-4288-ae56-172086110902/outcome.json) |
| rank16-k0-n128 | exact authenticated recovery | 400 | 1236 | 60.800 | [outcome](artifacts/stage3_transport/attempts/c2249cd8-c821-435b-8d46-ac5f58b8d480/outcome.json) |
| rank16-k1-n32 | exact authenticated recovery | 208 | 651 | 37.391 | [outcome](artifacts/stage3_transport/attempts/368fd333-39ce-487e-aa54-736034d8c5e3/outcome.json) |
| rank16-k1-n128 | exact authenticated recovery | 400 | 1233 | 60.802 | [outcome](artifacts/stage3_transport/attempts/f213c595-a301-4e4a-a3f3-fdec26de6c2b/outcome.json) |
| rank16-replay-0 | exact authenticated recovery | — | 412 | 30.413 | [outcome](artifacts/stage3_transport/attempts/aa7ad412-8954-4929-aa0f-5777968c337d/outcome.json) |
| rank16-replay-1 | exact authenticated recovery | — | 411 | 30.393 | [outcome](artifacts/stage3_transport/attempts/67eeb99e-2e26-4091-b5f9-d506a5396da4/outcome.json) |
| rank16-control-0 | ordinary UTF-8 generated | 400 | 432 | 25.618 | [outcome](artifacts/stage3_transport/attempts/cafeba1d-5d47-4dc1-a32d-58aeedd2b438/outcome.json) |
| rank16-control-1 | ordinary UTF-8 generated | 400 | 430 | 25.067 | [outcome](artifacts/stage3_transport/attempts/6e8cb2a1-d3d1-4193-8dee-8d61ac1bd85d/outcome.json) |

Fixture 0 uses envelope `12de85ea-3e3e-4a4a-8997-27e551978366`, originally a retokenization-drift failure; fixture 1 uses `21732f7e-11f4-48da-8b5c-2f7b622a7770`, originally invalid UTF-8. Both use their original rainfall cover context (index 2). Their new carriers are canonical UTF-8 with exact public envelope reconstruction. Both fresh 128-byte replays select the intended 128-byte source for that key; no 32-byte replacement was used.

Every comparator carrier was saved verbatim as `carrier.txt`; the encoder's final tokenization check and independent decoder traces agree. Candidate-order digests and decoded nibble streams match across each encode/receive path. First-divergence and rejection records are preserved in [compact_traces.json](artifacts/stage3_transport/compact_traces.json), with complete traces in per-attempt results.

The public observer receives only codec, text, public profile and context. It validates the public bounded frame and reports an envelope hash without private keys or tag authentication. All **4/4 fresh carriers** passed the public format check; **0/2 ordinary controls** did. Both controls decoded an out-of-range public length header and were rejected. These are expected diagnostic results, not failed encrypted recoveries:

- `rank16-control-0`: context 1, 400 generated tokens, PCG64 seed 2026092001, matched source `c2249cd8-c821-435b-8d46-ac5f58b8d480`; public format `False`.
- `rank16-control-1`: context 0, 400 generated tokens, PCG64 seed 2026092002, matched source `f213c595-a301-4e4a-a3f3-fdec26de6c2b`; public format `False`.

Ordinary controls sample the full vocabulary at temperature one and do not apply the comparator's constrained emission policy. These are different distributions; this small diagnostic contrast is not a reliable detector-performance estimate and supports no concealment claim.

## Expansion, candidate availability and resources

Analytically, the 196-byte maximum envelope produces a 200-byte frame and **400 carrier tokens**. Fresh 32-byte payloads require **208 tokens**; 128-byte payloads require **400 tokens**. Gross framed throughput is four bits/token; net payload throughput includes the public length and HPKE overhead. Measured carrier lengths agree with those analytical counts:

| Case | Envelope bytes | Carrier tokens | UTF-8 bytes | Net payload bits/token |
|---|---:|---:|---:|---:|
| rank16-fixture-0 | 196 | 400 | 1231 | not a fresh payload test |
| rank16-fixture-1 | 196 | 400 | 1799 | not a fresh payload test |
| rank16-k0-n32 | 100 | 208 | 933 | 1.2307692307692308 |
| rank16-k0-n128 | 196 | 400 | 1657 | 2.56 |
| rank16-k1-n32 | 100 | 208 | 910 | 1.2307692307692308 |
| rank16-k1-n128 | 196 | 400 | 1792 | 2.56 |

The fixture carriers expand from the historical intended **185 and 183 tokens to 400**, respectively **2.1622× and 2.1858×**. Those old sequences did not provide successful UTF-8 transport. This is a descriptive comparison of fixed envelopes, not a randomized paired performance experiment. Fresh ciphertexts and keys differ across stages; historical Calgacus's failures and 6/12 Stage 1 recovery remain unchanged.

Across **2016 encoder positions**, the capped admissible count was at least **16**; the search examined a mean **16.0441** and maximum **23** ranked candidates. Scanning stopped at 16 eligible IDs, so these are availability lower bounds, not full support counts. Rejections before the 16th eligible token: `{"empty": 0, "invalid_utf8": 0, "noncanonical": 88, "special_control": 1}`. No candidate exhaustion occurred. Timing includes these host checks. Fluency and formal detectability were not measured. Fresh encode/receive/public-extract jobs took at most **60.802 seconds**, including startup and shutdown; per-phase times are retained separately.

| Resource | Prior usage | Incremental Stage 3 | Cumulative | Stage 3 ceiling | Project ceiling |
|---|---:|---:|---:|---:|---:|
| GPU-job seconds | 1002.445408537 | 399.084108945 | 1401.529517482 | 1,200 | 7,200 |
| Evaluated tokens | 16,401 | 7,098 | 23,499 | 8,000 | 25,000 |
| Attempted cases | 33 | 10 | 43 | 10 | 72 |

Incremental **0.110857 GPU-job hours**, cumulative **0.389314 hours**. The same authoritative [project ledger](artifacts/project_budget.jsonl) and shared execution lock were used. Its entire pre-Stage-3 prefix is unchanged, checked against the starting Git revision and [immutable prefix anchor](artifacts/stage3_transport/budget_anchor.json). The existing checkpoint advances with append-only reservations/settlements; no independent ledger, reset or discarded attempt was introduced. Historical usage retains the previously qualified 30-second carry-in whose original raw trace is unavailable.

Every job was admitted with its complete frozen reservation against both ceilings. Wall time covers imports, hash/model startup, candidate checking, all inference, public extraction and shutdown. **22 phase charges** reconcile independently from context-token counts and advanced-token traces. All workers exited before their absolute deadlines with matching input hashes, unique leases and GPU PIDs. No retries, ungoverned warmups, crashes, abandoned attempts, numerical/invariant failures or resource breaches occurred. Stop reason: **Fixed allocation exhausted; stop GPU work**. Remaining original token headroom is only **1,501 tokens**; this is not authorization to spend it.

## Reproduction and evidence

Commands actually used in the existing environment:

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_public_utf8_rank16.py -v
.venv/bin/python scripts/prepare_stage3.py > artifacts/stage3_transport/preparation.txt 2>&1
.venv/bin/python scripts/run_stage3.py --allocation-check > artifacts/stage3_transport/allocation_check.txt
# Commit frozen source/allocation before inference.
.venv/bin/python scripts/run_stage3.py > artifacts/stage3_transport/controller.log 2>&1
.venv/bin/python artifacts/stage3_transport/reconcile.py > artifacts/stage3_transport/reconciliation_output.txt
```

Preparation and execution are one-shot and refuse regeneration/automatic resumption. The last command regenerates the derived evidence summary without model inference. The [evidence manifest](artifacts/stage3_transport/evidence_manifest.json) links every result to the tested commit, public configuration, exact inputs, saved carrier, worker argv/environment, lease, GPU samples, raw results and output hashes. [summary.json](artifacts/stage3_transport/summary.json), [cases.jsonl](artifacts/stage3_transport/cases.jsonl) and [reconciliation.json](artifacts/stage3_transport/reconciliation.json) agree. Private key material in this package is clearly marked public **TEST_ONLY**, never production credentials; no weights are committed.

## Interpretation and next recommendation

The canonical-prefix invariant explains conditional exact transport: final UTF-8 retokenizes to emitted IDs; identical prefix, model state and candidate ordering let the decoder recover the same nibbles and bounded frame. Native numerical reproducibility remains an assumption outside these measured runs. This is a **public rank-based transport comparator** with changed capacity, fluency and detectability tradeoffs, not unmodified Calgacus or a new cryptographic primitive. All successful runs qualify only this frozen model/backend/profile and small development allocation. Public extraction remains possible and distinguishable in these examples; sender authentication, edit robustness, concealment and formal security are not established.

No execution repair is indicated by these results. **Recommendation: separately plan a small, preregistered admissibility stress study over public contexts and token-boundary endings before any larger matrix, with an explicitly reviewed token budget.** Current project headroom cannot support a broad study. Scientific novelty, manuscript overlap, keyed comparator validation and publication-grade evaluation remain unresolved; none was reopened or executed here. The full research study remains stopped.
