# Public six-token prefix observer for public_utf8_rank16_v1

This stage diagnoses one public framing choice. It changes neither Calgacus nor the rank16 codec/profile, and it generates no new encrypted transmissions. Transport correctness, recognition of communication and cryptographic content confidentiality are separate properties.

## Structural finding and scope

The unchanged `frame` writes `len(envelope).to_bytes(4, 'big')` before the 68..196-byte envelope. Since every supported length is less than 256, its first three header bytes are zero. The high-nibble-first mapping yields **six initial zero symbols**. Each zero chooses the first of the 16 admissible tokens, in the existing public conditional order. For a fixed public cover context, model/tokenizer/profile, reproducible backend order and successful admission, those six token IDs are therefore publicly predictable.

This applies to successfully encoded/transmitted carriers of **public_utf8_rank16_v1**, with its canonical-prefix invariant and actual UTF-8 transport. The final tokenization must recover the emitted IDs. It assumes agreed contexts, tokenization boundaries, tie handling and sufficiently reproducible native logits. Candidate exhaustion can abort encoding; a complete carrier can also fail later. This is not a claim about the original Calgacus method, all rank methods or linguistic steganography generally. It neither exposes the HPKE plaintext nor breaks HPKE.

## Prediction, observer and provenance

The predictor runs the unchanged `PublicUtf8Rank16Codec.candidates` under the public context, selecting index zero and advancing the model six times. It receives no ciphertext, carrier, encoder trace, private key, label or expected payload. Predictions are computed in three fresh leased GPU jobs and persisted before any historical carrier files are opened. They are cached by the exact profile hash and context, with observer identifier `public_zero6_v1`, source revision, attempt ID, PID, GPU UUID and per-step probabilities. Caches contain public computation, not encoder state.

The observer API takes only transmitted bytes, public profile/context, a validated public prediction and the public tokenizer. It decodes strict UTF-8, tokenizes those actual bytes with the existing no-BOS/no-special-interpretation rule, and compares **only the first six IDs**. It does not inspect a total token/byte count to discriminate full message length, parse a header, extract an envelope, authenticate tags or access payload/private-key/evaluator fields. Valid suffixes are not length features, although actual tokenization can depend on text boundaries. This is a function-input boundary, not an operating-system sandbox against the account owner.

Non-byte input and invalid UTF-8 are explicit nonmatches. Fewer than six tokenized IDs is `insufficient_tokens`, also a nonmatch. Valid text with six or more IDs produces `match` or `valid_nonmatch`. Bad public cache/profile/context is a configuration error; tokenizer/runtime failures are retained as execution failures, not silently classified. A match does **not** prove that a valid ciphertext exists. Generated IDs and retokenization diagnostics are kept outside this observer API.

Historical reanalysis checks exactly the six unique Stage 3 comparator carriers (two fixtures and four fresh transmissions), grouped by their public contexts. It uses saved UTF-8 only after prediction construction. Prior replay copies and ordinary full-length controls are not selected as new observations. These are historical artifact checks, not new transmissions, new recovery successes or independent trials.

## Frozen control generators and probabilities

Each control attempts exactly **six token emissions**, without a header, payload, encryption, tail or EOS stop. All use the same public cover contexts, backend, cache clearing, and NumPy PCG64 with the two predeclared seeds 2026092101 and 2026092102. Seeds are reproducibility parameters, not cryptographic keys. The same two seeds are used across contexts/families; the resulting 18 controls are not independent operational traffic samples.

- **A:** full-vocabulary temperature-one softmax sampling, exactly the existing float64 softmax/`rng.choice` convention. No rank16 filtering is applied.
- **B:** compute the unchanged first 16 admissible candidates at each prefix, then sample their model logits using a temperature-one softmax renormalized over those 16 IDs, in their agreed rank order.
- **C:** compute the same 16 admissible candidates and choose an index uniformly using `rng.integers(16)`.

For B/C the canonical-prefix admission rule is reused directly, not reimplemented. Invalid UTF-8, tokenization changes, candidate exhaustion and partial prefixes are retained; no normalization, resampling, replacement token or seed substitution is allowed. A can produce noncanonical/invalid rendered output. B/C violating the invariant indicates an implementation/numerical problem and stops this allocation.

At public zero-path position `i`, let `t_i` be candidate zero, `E_i` the 16 admissible IDs, and `l_i(v)` the model logit. Record the numerical conditional probabilities and sum their logarithms:

- `log p_A_latent = sum_i [l_i(t_i) - logsumexp_v l_i(v)]`, for the intended latent six-token sequence. This is **not automatically the probability that transmitted text retokenizes to the observed prefix**; other latent sequences may map to the same observed prefix. The canonical zero sequence is one contribution to that event.
- `log p_B_match = sum_i [l_i(t_i) - logsumexp_{v in E_i} l_i(v)]`. For the six-token B generator, canonical final tokenization makes a match equivalent to following this zero path. Other paths may abort; their aborts are not discarded from the sample space. This is a model-derived probability under ideal draws from the specified conditional distributions, evaluated numerically under the frozen backend.
- `p_C_match = 16^(-6) = 1/16,777,216`, assuming the zero path has 16 eligible choices at each step and ideal independent uniform index choices. For actual fixed PCG64 seeds the outputs are deterministic; this formula describes the ideal generator model, not a cryptographic randomness guarantee.

Scoring reads existing logits and performs host arithmetic without additional model evaluations. All prefill and selected-token evaluations, including the sixth token, are metered. Numerical probabilities, structural claims and small-sample frequencies are reported separately. No operational detector accuracy or general false-positive rate is estimated.

## Sample space, aborts and distinguishing statements

For each control family/context, the experiment is one six-step generation attempt followed by exact serialization and observation, or an explicit abort outcome. Invalid text and candidate exhaustion map to nonmatch/abort in the intention-to-generate denominator; no unsuccessful case is discarded. Valid retokenized text is classified as received, with drift retained as a separate diagnostic flag. Infrastructure failures are separately inconclusive, stop further work and cannot be credited as valid nonmatches. Report allocated/attempted/completed/aborted counts separately.

For a complete rank16 stego attempt, let `q_S` be the unknown probability of successful transmission; the structural result is `P(match | successful stego) = 1`, not an estimate that `q_S = 1`. If abort maps to nonmatch in both distributions, the unconditional acceptance gap against B is `q_S - p_B_match` (or its absolute value under an absolute-advantage convention), and against ideal C it is `q_S - 16^(-6)`. `q_S` is not established here. If both distributions instead condition on success, B's acceptance is `p_B_match/q_B`, where `q_B` is its own unknown success probability; one cannot silently use an unconditional cover probability against success-conditioned stego. Historical successful carriers are selected artifacts, not an estimate of either success probability. **No numerical distinguishing advantage for full traffic is claimed.**

## Allocation and stopping

Three prediction/scoring cases, contexts 0/1/2, then contexts 0/1/2 × A/B/C × the two seeds: **21 cases maximum**. Each reserves **45 conservative GPU-job seconds and 64 evaluated tokens**. All full reservations together are 945 seconds / 1,344 tokens / 21 cases, below the additional **1,000 seconds / 1,400 tokens / 21 cases** and the original project ceilings at the recorded baseline. Context-plus-six bounds are verified from prior public context tokenizations with matching model/tokenizer/backend hashes, then checked against actual metering in every worker. Host-only identity checks do not load a model. No unmetered inference or backend rebuild occurs.

Use the single authoritative project ledger, current complete-prefix anchor, inherited execution lock, one-shot leases, pre-import absolute deadlines, existing token meter and clean-source check. Stop on a prediction failure or accounting, lease, deadline, provenance, numerical or B/C invariant failure; ordinary serialization/admissibility aborts remain outcomes without retries. Abandoned attempts retain full reservations. Freeze and commit the allocation before inference. All data are development-only and excluded from future held-out evaluation.

## Contribution assessment boundary

Use the existing `docs/novelty_matrix.md` and available local materials. Predictable public framing and recognition via a public inverse are straightforward consequences of framing/public-inversion principles; exact rank inversion and encrypt-then-embed are already overlapping foundations. A possible distinct research question is how explicit observer knowledge, cover distributions, finite framing and abort-conditioned text transport jointly determine practical leakage and utility. A regular-paper claim would need a clearly delimited threat/sample-space model, supported comparisons, broader separately budgeted evidence and overlap clearance against the latest CARTS, RankCloak and cross-modal manuscripts. Latest submitted revisions and priority clearance remain unresolved. This diagnostic is not a novelty declaration or manuscript project.
