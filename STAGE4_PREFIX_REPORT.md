# Stage 4: bounded public-prefix leakage diagnostic

**Completed the fixed 21-case local-GPU allocation.** The independently computed public six-token predictions matched all six selected historical rank16 carriers. All 18 six-token controls were valid nonmatches: 0/6 matches for each of A, B and C. No serialization, candidate-exhaustion, numerical, lease, deadline or execution failure occurred. These observations demonstrate a predictable framing property of `public_utf8_rank16_v1`, not operational detector accuracy or a break of HPKE.

Repository: https://github.com/mantzaris/CalgacusPublicEncryption. Work started directly on clean `main` at `fe3aeaddd7df1d4fb3b19c49ccc84251a519d39f`. The implementation, public observer specification and complete allocation were committed **before inference** at GPU-tested revision **`32edd3bf54712a8134659f298b8958462024c2a0`**. The later evidence/report commit does not change tested code. Stage 3 GPU revision `6f78518d69e5e3f0bea80db94b9885a9daaa47e7` remains the source of the historical carriers; this stage does not attribute their recovery results to the new revision.

## Finding and implementation boundary

The unchanged [rank16 codec](src/llm_stego_public_key/codecs/public_utf8_rank16.py) frames the complete envelope with a four-byte unsigned big-endian length, bounded to 68–196 bytes. Every supported length has three initial zero bytes. High-nibble-first emission therefore starts with six zero symbols, each selecting the **first admissible token** in the public conditional ordering.

Consequently, a successfully encoded and transmitted canonical rank16 carrier has six publicly predictable initial token IDs, conditional on the agreed public context, exact model/tokenizer/profile, reproducible numerical candidate ordering and successful admission. This concerns this registered framing/selection policy. It does not generalize to original Calgacus, all rank transports or linguistic steganography. A match does not prove that an envelope exists or that a ciphertext authenticates.

The new [observer and generators](src/llm_stego_public_key/evaluation/public_prefix.py) directly reuse `PublicUtf8Rank16Codec.candidates`. The predictor starts from public configuration and selects zero six times; it has no carrier, ciphertext, private key, payload or encoder-trace input. Each prediction was saved before historical files were opened. The observer receives actual transmitted bytes, public profile/context, a public prediction and the tokenizer; it checks only the first six tokenized IDs. It never authenticates a tag or uses full message length. Invalid UTF-8/non-byte input and insufficient tokens are explicit nonmatches; tokenizer/configuration errors are execution failures. This is an API/data-flow boundary, not an OS sandbox. The provenance phrase “independent public zero-symbol selections” means computed independently of saved carriers, not statistically independent model steps.

[The observer specification](docs/public_prefix_observer.md) was frozen before execution. Neither transport codec, either registered profile, HPKE, framing, key policy, backend settings nor historical evidence was changed. The controller reuses the existing shared ledger lock, reservation/settlement contract, one-shot worker leases, pre-import deadlines, phase meter, source checks, GPU loader and PID-matched GPU evidence. No encrypted messages, fresh keys, full recovery tests, model downloads or backend builds were generated here.

## Frozen sample and observed outcomes

Three public prediction/scoring cases ran first, then contexts 0/1/2 × families A/B/C × seeds **2026092101, 2026092102**. Every control emitted exactly six tokens, without encryption, header, payload, EOS stop, resampling or appended text. Seeds are PCG64 reproducibility parameters, not cryptographic keys; the same two seeds across families/contexts do not constitute independent traffic samples.

- **A:** existing full-vocabulary temperature-one softmax sampling.
- **B:** temperature-one model probabilities renormalized over the unchanged 16 admissible candidates.
- **C:** uniform index sampling over those same 16 admissible candidates.

These are three different specified distributions and only prefix diagnostics, not complete messages or realistic full-length cover traffic. All material is **development-only, excluded from future held-out evaluation**.

| Public context | Predicted text prefix (JSON quotes preserve leading space) | Historical matches | A latent-sequence probability | B prefix-match probability | Ideal C prefix-match probability | Observed matches A / B / C |
|---|---|---:|---:|---:|---:|---|
| 0: garden | `" The trees in the public garden"` | 2/2 | 0.00771830954 | 0.04173936315 | 0.00000005960464478 | 0/2 / 0/2 / 0/2 |
| 1: library | `" Dewey Decimal Classification (DD"` | 1/1 | 0.09102270732 | 0.11624181360 | 0.00000005960464478 | 0/2 / 0/2 / 0/2 |
| 2: rainfall | `" a case study in the city"` | 3/3 | 0.00026031646 | 0.00439316302 | 0.00000005960464478 | 0/2 / 0/2 / 0/2 |

Exact public contexts:

```text
0: A field note about trees in the public garden:
1: A brief explanation of how a library organizes books:
2: A research note about measuring afternoon rainfall:
```

Predicted IDs respectively: `[578,12690,304,279,586,13863]`, `[50400,1216,27826,55982,320,4195]`, `[264,1162,4007,304,279,3363]`. [Public predictions](artifacts/stage4_prefix/public_predictions.json) retain all six conditional probabilities/log probabilities, 16 candidate logits/IDs per step, context/profile cache keys and originating attempt provenance.

Every context/family cell contains two valid nonmatches, with **zero invalid UTF-8, insufficient-token, retokenization-change, candidate-exhaustion or runtime outcomes**. All controls retained exactly the emitted token IDs after text round-tripping. The unchanged admission rule examined 16–17 candidates at each of 90 prediction/B/C steps. It excluded two noncanonical proposed candidates; these are successful admission checks, not failed emitted snippets or discarded control cases.

The six historical artifacts comprise two Stage 3 envelope fixtures and four Stage 3 fresh transmissions. Existing receiver-replay copies and full-length ordinary controls were excluded. Their prefix checks use actual saved UTF-8 after public prediction computation. **6/6 is selected historical-artifact acceptance, not six new transmissions, authenticated recoveries or independent successes.** No new recovery count is claimed.

All 21 planned cases were attempted and completed; none was skipped, substituted or retried. The retained controller's generic `success`/`expected_outcome_agreement` fields mean job completion here, not prefix acceptance or message recovery. Use `observer.prefix_match` for the diagnostic decision. Every Stage 4 `authenticated` and `authenticated_message_recovery` field is false.

## Probability interpretation and abort sample space

These numerical scores use frozen native float32 logits and stable float64 softmax/log arithmetic. For each zero-path step, B's probability is the selected logit normalized over its 16 admissible logits; summing six log probabilities and exponentiating gives the table. B's three log-products are −3.1763106350, −2.1520826576 and −5.4277058059. Artifact reconciliation independently recomputes these values from retained logits. A's log-products are −4.8641599102, −2.3966462727 and −8.2536125121; its full-vocabulary normalization is recorded from the worker, not independently re-evaluated with another GPU call.

For ideal B sampling, canonical six-token emission makes a match equivalent to following the zero path. Ideal C follows that path with probability **16⁻⁶ = 1/16,777,216**, assuming 16 eligible choices at each zero-path step and independent uniform index draws. Actual fixed-seed runs are deterministic; the probability statements describe the specified ideal generators under the frozen model, not randomness guarantees for PCG64.

A's entry is only the probability of the intended **latent token sequence**. Alternative latent sequences can serialize and retokenize to the observed prefix; therefore this number is not automatically the text-observer match probability. The zero sequence is one contribution to that event. No operational false-positive rate is estimated from 0/6 controls or from these model-derived path scores.

The predeclared control sample space is a six-emission attempt followed by exact text serialization/observation, or an explicit abort. Invalid text/candidate exhaustion remain in the intention-to-generate denominator as nonmatch/abort; infrastructure failures remain separately inconclusive and would stop execution. Valid text with tokenization changes would be classified as received, with drift separately flagged. None of these aborts occurred in the retained sample.

The structural stego statement is **P(match | successful rank16 transmission) = 1**. If full stego attempts succeed with unknown probability `q_S` and abort is nonmatch for both distributions, the acceptance gap against B is `q_S − p_B` and against ideal C is `q_S − 16⁻⁶` (absolute value if that is the chosen advantage convention). Success-conditioning both sides would instead require B's own success probability `q_B`, giving its conditioned acceptance `p_B/q_B`. Neither `q_S` nor `q_B` is established by selected historical carriers and eighteen prefixes. **No numerical full-traffic distinguishing advantage is asserted.**

Transport correctness and concealment are separate. Predictable framing and public extraction can coexist with cryptographic content confidentiality. These observations do not recover encrypted plaintext, break HPKE, establish sender authentication, demonstrate edit robustness or establish concealment. A probability-weighted admissible null gives notably different prefix probabilities from a uniform admissible null; the cover-generation model is part of the claim.

## Hardware, accounting and focused verification

Rediscovery and exact asset checks selected **NVIDIA RTX 5000 Ada Generation**, UUID `GPU-10d1f16f-9e79-08bb-b2ba-3353c04422cf`, **32,760 MiB**, driver **590.48.01**. The separate Quadro T2000 was not used. Existing Meta-Llama-3-8B-Instruct Q4_K_M, embedded tokenizer, llama-cpp-python 0.3.23, NumPy 2.2.6, CUDA runtime 12.4.127 and cuBLAS 12.4.5.8 remained unchanged. Model hash `86c8ea6c8b755687d0b723176fcd0b2411ef80533d23e2a5030f845d13ab2db7`; tokenizer hash `5c8950bef385be95db5feda8c8afadba6a5c0b903e6ceaa39efe6cfe3d84f3f3`; canonical public profile hash `b3a106424d9e0e8b1c6d19ec7061d13a07a9a0871d0a92d5bb3dd1296b6156a6`. Native/CUDA library hashes and operating environment are in [environment.json](artifacts/stage4_prefix/environment.json).

Inference remained serial batch/ubatch 1, full GPU offload (33/33 layers verified in every worker log), n_ctx 2048, float32 logits, f16 KV, cublas 32F, cache reset/clear per sequence, ascending-ID ties and existing special-token/BOS rules. All 21 distinct prediction/control worker PIDs had matching selected-GPU memory samples, verified leases, clean exits and verified source/phase metering. No CPU model inference occurred. Peak **sampled**, not continuously measured, per-process VRAM was **5,006 MiB**.

| Budget | Conservative GPU-job seconds | Evaluated tokens | Attempted cases |
|---|---:|---:|---:|
| Prior reconciled project | 1,401.529517482 | 23,499 | 43 |
| Stage 4 increment | **331.169239841** | **350** | **21** |
| Project cumulative | **1,732.698757323** | **23,849** | **64** |
| Remaining original headroom | **5,467.301242677** | **1,151** | **8** |

Each case retained its full **45-second/64-token** reservation. All 21 full reservations (945 seconds/1,344 tokens) fit the additional 1,000-second/1,400-token/21-case ceilings and the global ceilings at launch. No reservation was reduced. Public contexts plus six selected-token evaluations cost 17/18/15 tokens respectively, checked against actual worker metering. Phase totals: **50 public-prediction tokens + 300 control tokens**. The final selected token was evaluated and charged even though no seventh prediction was needed. Candidate checks and probability arithmetic added no model evaluations.

Charges cover each launched process from before imports through loading, operation and shutdown, including host work inside the GPU job; they are not kernel-active time. Jobs took 15.458–16.116 seconds, median 15.995. Recorded in-worker load/verify time totaled 305.021 seconds and operation plus host observation 9.029 seconds; these components are not an alternative budget. The unchanged controller's absolute worker deadline was 37 seconds from launch, leaving eight seconds within each reservation for termination/shutdown. All jobs exited cleanly before it. The original **21,601-byte historical ledger prefix** is unchanged; 42 reserve/settle events were appended, and the final checkpoint agrees. No budget reset or separate ledger was created.

Only **five focused new contract tests** and **five fixed-allocation/boundary checks** were run before the implementation commit. They address public observer inputs, malformed/short inputs, prefix-only matching, six zeros, independent probability values, the three sampling policies and full-reservation limits. Existing foundational CPU results were reused; **no full pytest suite, lint sweep, CPU benchmark, new CPU environment or general audit was run**. Prior CPU results are not attributed to the new code. Post-run work was artifact arithmetic/hash reconciliation only.

## Evidence and reproduction

The [evidence manifest](artifacts/stage4_prefix/evidence_manifest.json) connects every result to its tested SHA, frozen inputs, command, worker lease, outputs, exact snippets, GPU samples and source/configuration hashes. [cases.jsonl](artifacts/stage4_prefix/cases.jsonl) is the immutable attempt index; [control_outcomes.json](artifacts/stage4_prefix/control_outcomes.json) preserves all 18 exact snippets. [summary.json](artifacts/stage4_prefix/summary.json), [historical_reanalysis.json](artifacts/stage4_prefix/historical_reanalysis.json) and [reconciliation.json](artifacts/stage4_prefix/reconciliation.json) are derived from retained records. No real credentials, new private keys or model weights are included.

Commands actually used (repository root; existing `.venv`):

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_public_prefix.py -v > artifacts/stage4_prefix/focused_checks.txt 2>&1
.venv/bin/python scripts/prepare_stage4.py > artifacts/stage4_prefix/preparation.txt
.venv/bin/python scripts/run_stage4.py --allocation-check > artifacts/stage4_prefix/allocation_check.txt
# Implementation and allocation committed at 32edd3bf... before this GPU command:
.venv/bin/python scripts/run_stage4.py > artifacts/stage4_prefix/controller.log 2>&1
.venv/bin/python artifacts/stage4_prefix/reconcile.py > artifacts/stage4_prefix/reconciliation.txt 2>&1
```

The GPU command records its exact per-attempt command/environment. **Do not delete the frozen allocation, run status, attempts or ledger to rerun it.** Preparation and execution are one-shot and reject completed/intervening work. Reviewers can regenerate derived summaries with the last command without inference; repeating GPU work would need a separately authorized allocation within then-current ceilings. Reconciliation checks saved tokenization evidence; it does not rerun the tokenizer/model or claim independent numerical replication.

## Contribution assessment and next step

Established here: a code-level six-zero framing implication; three public GPU predictions with measured conditional scores; acceptance of six actual historical carrier prefixes; and explicit outcomes from three predeclared six-token control distributions with accountable local resource use. Recognition is possible without a ciphertext parser or key, and its numerical interpretation changes substantially with the null generator.

The core observation is a straightforward consequence of public deterministic framing and public inversion, not an invented encryption primitive or an established novel stegosystem. [The existing novelty matrix](docs/novelty_matrix.md) already identifies rank inversion, artifact concealment, saved-text correctness and the separation of detection from recovery as overlapping foundations. The available RankCloak `paperV3/scientific_reports/main3.tex` abstract/method/limitations and ImageCalgacus `paper/icaart2027/main.tex` public-receiver/detection discussion were consulted narrowly; their identities are recorded in `manifests/related_materials.json`. Their manuscript claims are not new measurements here. CARTS scope is inherited from the existing matrix; no new literature search was undertaken.

A potentially distinct question is how explicit public observer knowledge, finite framing, actual text transport and matched cover/abort distributions jointly determine leakage versus useful payload throughput. This package supplies a concrete negative example and a precise diagnostic contract, **not enough evidence or novelty clearance for a regular paper**. Latest submitted CARTS, RankCloak and cross-modal manuscripts, focused priority clearance, and justified comparator implementations preserving any shared-secret assumptions remain missing. Broader independent contexts, seeds and matched complete-message cover generation would require a new plan and evidence; the present prefixes do not support general detector-performance claims.

**One recommended next step:** obtain the latest three manuscripts and perform a focused contribution/overlap decision around that explicit observer-and-cover question before authorizing more GPU experiments. This step needs those manuscript materials and no additional GPU budget. A subsequent larger study would need its own reviewed allocation and explicit budget authorization if it exceeds the remaining **1,151 tokens / 8 cases / 5,467.301 seconds**. No budget increase, transport repair or further study is executed here.
