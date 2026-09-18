# Preliminary claim-overlap matrix

**Novelty gate: unresolved.** This is an engineering evidence package, not a novelty declaration or completed priority search. Available local drafts are identified below; their publication/submission status and any newer overlapping drafts need author confirmation before a submission claim. No manuscript is written in this stage.

| Material inspected | Exact identity / inspected scope | Evidence status |
|---|---|---|
| Calgacus | arXiv:2510.20075v6, Jan 16 2026; main method/security/appendix discussion; all official notebook code cells at `116123d4b7a74b3d56d15623355f9acf32a87165` | Primary paper and actual code inspected; local reference-function cases are separately labelled |
| CARTS | [arXiv:2609.10744v1](https://arxiv.org/abs/2609.10744v1), Sep 9 2026, full main paper including definitions, theoretical results, experiments and conclusion | Public manuscript available and read; author's latest submitted revision not established |
| RankCloak | `../llm-rankcloak/paperV3/scientific_reports/main3.tex`, repository `ce853d42d6ba64065cb63c6bdfc0d825c62734cd`; abstract, method/contract, results and limitations inspected | Local draft and relevant code inspected; reported large-study outcomes not reproduced |
| Cross-modal / ImageCalgacus | `../ImageCalgacus/paper/icaart2027/main.tex`, repository `2bec65dbe5509623f6658d8a231ec93f6d579b4e`; main methods, results and discussion; V2 review README and cover manifest inspected | Local draft and artifact descriptions inspected; no prior recovery result counted as Stage 1 evidence |
| LlmStenoExplore | Repository `b9f1650b4eb0b2261b0080f86d9b1d8fadedbc0b`; README and `paper-empirical-explorations/results/raw/run_manifest.json` | Manifest inspected; it records CPU-only inference and historical source `2389ada4c69b0d01ca805167980d162a0488563e`; not a current GPU benchmark |
| Meteor | [primary ePrint record](https://eprint.iacr.org/2021/686) accessible; PDF fetch returned HTTP 403 | Full primary text and implementation audit unresolved; no reconstructed theorem or setup claim from secondary descriptions |

CARTS already supplies deterministic rank-trace inversion (Lemma 1), two-context correctness (Theorem 2), and rank-coordinate conjugacy (Proposition 1), with explicit tokenization/numerical assumptions. Its main security focus is prompt-key search, collisions, equivocation and commutativity, rather than a public HPKE composition. These are inspected scope observations, not proof that every potential new claim is absent.

| Candidate claim or capability | Closest overlap | Stage 1 disposition |
|---|---|---|
| Exact conditional rank inversion | Calgacus; CARTS Lemma 1 and Theorems 1–2 | Reused foundation, not new |
| Rank-coordinate bijections/change of coordinates | CARTS Section 4.2; standard probability change of variables | Do not claim novelty for the bijection or generic TV/KL identity |
| High-entropy source ranks hurt fluency; rank preservation differs from probability matching | Calgacus hash example and discussion; RankCloak rank-pressure analysis | Already known; new ciphertext examples alone are incremental |
| Concealing surface Base64/cryptographic artifacts | RankCloak | Strong overlap; actual HPKE wrapping is an implementation distinction, not sufficient novelty |
| Explicit authenticated bytes inside generated carriers | Cross-modal shared AES-GCM packet contract | Already present; HPKE changes sender setup but does not invent encrypt-then-embed |
| Actual UTF-8 artifact receiver, isolated state, strict bytes | Cross-modal saved-artifact boundary; RankCloak rendered-text diagnostics | Reuse and test infrastructure, not a new scientific contribution |
| Stable token-ID tie order, native cache reset, serial inference | RankCloak and cross-modal implementations | Attributed engineering reuse |
| Public-key confidentiality with public contexts | Standard HPKE and public-key steganography literature | Library composition; conditional security argument still needs review |
| Public inverse-format observer for HPKE envelopes versus ordinary model covers | Candidate project direction; adjacent recognition/detection work in RankCloak and model-aware scores in cross-modal work | Diagnostic implemented; novelty and practical incremental value remain unresolved |
| Length, tokenization, framing, confidentiality and detectability measured separately | All three local projects cover subsets; cross-modal particularly close | Useful common evaluation contract, no standalone priority claim |
| Public arithmetic codec for full envelopes | Neural Linguistic Steganography; cross-modal finite-packet arithmetic comparison | Adapter interface only; not a newly invented comparator |
| Modern keyed range-coding reference | RRC and broader keyed generative steganography | Additional shared-secret setup must stay explicit; no inherited security claim for a seeded simulation |

No prior carrier, payload dataset or experimental measurement is reused as a new Stage 1 case. Only model/backend assets, small implementation practices and source references are reused. Source hashes and local manuscript identities are in `manifests/related_materials.json`. Missing latest submitted manuscripts, Meteor full text, and a focused priority search for the proposed public-format result prevent a publication-novelty decision.

## Comparator feasibility audit

Public arithmetic candidate: [harvardnlp/NeuralSteganography](https://github.com/harvardnlp/NeuralSteganography/tree/14e982564aeaf9a33f7b4de440deda2184d17f12). `arithmetic.py` and requirements were inspected. It uses torch/Transformers logits, integer intervals (default precision 16), truncation/rounding and GPT-specific token exclusions (last vocabulary entry and ID 628), optional sentence completion and retokenizing extraction. The pinned environment includes torch 2.7.1, Transformers 4.52.4 and CUDA 12.6 components. These are not the chosen llama.cpp runtime. A common-model adapter needs explicit token-order/probability, fixed payload-bit length, termination and UTF-8 contracts; blindly preserving GPT-specific token IDs would be wrong. Existing cross-modal A1 code is a possible starting reference, but its manuscript already reports text-capacity failures. No arithmetic benchmark runs here.

Keyed candidate: [ryehr/RRC_steganography](https://github.com/ryehr/RRC_steganography/tree/dae326259e4fca8bc4fcf460dafdbc0e88a0a71a), README, requirements, `rrc_core.py` and CLI setup inspected. Requires torch>=2, Transformers>=4.35, pandas, NumPy, HF weights and tokenizer; no llama.cpp adapter exists in the inspected code. Uses Decimal range arithmetic, matched incremental decoding, message-bit length and a termination verification guard. The CLI reinitializes `random.Random(args.key)` per message; core rotations use `Decimal(prng.random())`. There is no cryptographic PRNG or fresh per-message nonce in that path. A fixed public example seed does not provide the secret random offsets assumed by a security argument. Before treating it as a secure keyed reference, audit a CSPRNG/nonce adaptation, preserve its shared-secret assumption, and label that adaptation distinctly. Missing audited randomness, finite-precision/termination tests and an agreed backend bridge block comparator readiness.

The typed interfaces in `codecs/interfaces.py` accept envelope bytes and return transmitted UTF-8, with separate public and keyed setup. They are contracts, not implemented benchmarks or distributional guarantees. Estimated setup work is several focused engineering days, unbenchmarked; additional model downloads or environment repairs have not been undertaken.
