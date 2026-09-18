# Stage 6 frozen study specification

**Authorized 18 September 2026; freeze before GPU execution.** This instruction explicitly supersedes Stage 5's proposed next-step gate. Internal CARTS/RankCloak/ImageCalgacus manuscript reconciliation is not a prerequisite for this exploratory stage. The historical assessment remains unchanged. Attribution and scientific caution remain; no novelty is presumed. Provisional direction: **Framing, Recovery, and Public Recognition in LLM-Based Encrypted Text Transport**.

Starting main: `f51f38c22367aeae4dd728e37f4c092435ad0e14`, clean. Question: after removing the public length header, what complete-message recognition remains, with what actual-UTF-8 recovery and cost? Old cases remain development evidence and are never pooled into this allocation. This is a fixed prospective exploratory study, not final held-out publication evaluation. Qualification outcomes are kept separate; they cannot tune the following matrix.

## Public methods and boundaries

L uses the unchanged rank16 codec with its four-byte big-endian envelope length. F (`public_utf8_rank16_inferred_v1`) has no outer header. Both directly reuse `PublicUtf8Rank16Codec.candidates`, descending native float32 logits / ascending-ID ties, the first 16 canonical-prefix candidates among the top 128, strict UTF-8 and special/control exclusions. No normalization, candidate-pool expansion, secret prompt, radix search, tail or EOS stop is added.

Stage 6 registers exact hashed public profiles under `configs/stage6/`: L, F and the **audited adapted Calgacus Base64 codec**. The changed public context inventory receives new profile identities; old profiles and evidence remain intact. Model/tokenizer/native libraries, precision, serial batch/ubatch 1, 2048-token context, 512-token transport bound, 65536-byte bound, GPU offload and per-sequence cache clearing are unchanged. The legacy HPKE protocol label remains a binding-domain label, not a claim that F is Calgacus.

F receives only bounded actual message bytes and public configuration. It requires strict UTF-8, exact detokenize(retokenize(bytes)) equality, **even 136..392 received tokens**, then infers 68..196 envelope bytes before allocation. Each received token must be in its reconstructed 16-candidate list. High nibble comes first. The received message boundary is the only termination boundary. Odd/truncated/out-of-range sequences or invalid rank choices fail framing. Even truncation or append operations that remain within bounds can pass public syntax, but the changed envelope must authenticate and its protected inner length must validate before delivery. There is no independent clear expected length in the receiver. Empty application payloads still produce 68 envelope bytes / 136 F tokens; maximum 128-byte payloads produce 196 / 392. L requires eight more carrier tokens at each size.

HPKE remains pyhpke 0.6.5, Base / X25519-HKDF-SHA256 / HKDF-SHA256 / ChaCha20-Poly1305, with the existing random 16-byte message ID, u32be inner length and no padding. Complete public profile and selected context enter existing `Binding.info`/`aad`; independent fresh encryptions under L/F never reuse a ciphertext across bindings. Keys and HPKE ephemeral/message-ID randomness use the established OS/library generators. Neither ordinary sampling seeds nor deterministic payloads replace cryptographic randomness. Base mode does not authenticate senders. Test keys are explicitly public, synthetic fixtures.

Receiver functions have no encoder tokens, ranks, expected payload/hash/length or saved cache inputs. Main cases reconstruct from the saved file with a reset model and fresh codec. Replays use independent worker processes with only the saved carrier, public profile/context and test private key; the controller compares recovered hashes after receiver exit. Observers have no private inputs or receiver outcomes.

## Contexts and payload/key assignment

These four contexts were selected by topic before new inference and are distinct from Stages 1–4:

0. `A museum note describing how a brass compass works:`
1. `A workshop guide to repairing a wooden chair:`
2. `A coastal report about waves around a stone pier:`
3. `A short account of sorting apples at a small orchard:`

Main payload bytes are `SHAKE256(ASCII("ICISSP2027 Stage6 synthetic binary c={c} n={n} r={rep}")).digest(n)`, for c=0..3, n in {32,128}, rep in {0,1}. This is synthetic binary input generation, not encryption. Main key index is `2*c+rep`: eight independently generated recipient keys, each shared across lengths and the L/F pair. A ninth key is qualification-only. L/F pair the same payload, public context and key, but use fresh independent encapsulations and message IDs. Variant order alternates by parity of context + repetition + 128-byte indicator; exact IDs and order are frozen in `artifacts/stage6/allocation.json`.

## Allocation and qualifications

| Block, in execution order | Planned cases | Per-case full reservations |
|---|---:|---|
| Public zero-prefix prediction for each new context | 4 qualification | 45 seconds / 128 tokens |
| F empty payload in context 0; F maximum payload in context 3 | 2 qualification | 75 seconds / 700 tokens; 120 seconds / 1500 tokens |
| L/F × four contexts × two sizes × two repetitions | 32 main encrypted | 32-byte: 90 seconds / 1000 tokens; 128-byte: 120 seconds / 1500 tokens |
| Three control families for each planned encrypted setting | 96 main controls | 32-byte setting: 65 seconds / 900 tokens; 128-byte: 90 seconds / 1100 tokens |
| Existing adapted Calgacus, four contexts × two sizes, repetition-zero paired inputs | 8 baselines | 120 seconds / 3300 tokens |
| L/F × both sizes × contexts 0 and 2, repetition zero | Up to 8 fresh receivers | 32-byte: 50 seconds / 320 tokens; 128-byte: 65 seconds / 512 tokens |

All six qualification cases must pass before main execution. Public predictions select zero six times using only public L configuration; they are computed before encrypted carriers. Cached predictions have exact profile/context hashes and producing attempt/revision. F uses that same **obsolete L-prefix observer**, not an assertion that F has a zero header.

Replays are predetermined; if their source fails, leave the slot unused, with no replacement from another size, context or repetition. There are 144 principal slots and six qualifications, leaving ten of the authorized 160 slots unused. No discretionary retries, replacement cases, extra seeds or parameter changes. No separate warmups. Qualification is not a search for favorable settings.

Conservative full-reservation totals are mechanically checked before launch against **14400 GPU-job seconds, 200000 evaluated tokens, 160 attempts**. Historical usage is **1732.698757323 seconds / 23849 tokens / 64 attempts**. New lifetime ceilings are precisely historical usage plus the additional allowance: **16132.698757323 seconds / 223849 tokens / 224 attempts**. Unused old allowances are not added. Authorization identifies the prior 32183-byte ledger SHA-256 `9cf35c86ee1aa96868f244bb4703835da4e7b866d192e0a135e265c08a45f304`.

The same ledger, shared file lock, worker leases, token meter, subprocess deadlines and conservative interrupted-job charges are used. A durable checkpoint transition records the explicit extension; historical ledger bytes are never rewritten. Old launchers reject the new checkpoint/limits. Full per-case reservations are admitted before launch; the deadline leaves eight seconds for termination/shutdown. Restart accepts only a complete, clean recorded prefix of this fixed study; orphan reservations/fatal outcomes are not permission to resume or retry. All loading, imports, host checks inside a GPU job, generation, source scoring, reception and observers count. Preparation hashes/tokenizer metadata checks involve no model inference.

Stop on accounting, lease, deadline, provenance, unexplained numerical divergence, violated promised canonical emission, or authenticated incorrect plaintext. Also stop on unexpected canonical L/F framing/authentication failure. Retain candidate exhaustion, original-Calgacus serialization failures and ordinary-control serialization outcomes without replacement. Stop when the next full reservation cannot fit. No execution/environment repair loop is authorized within this fixed allocation.

## Control sample spaces

Each control has an independently predeclared PCG64 seed `202609180000 + 10*encrypted_slot_index + family_index` (A=0,B=1,C=2). Seeds are reproducibility parameters, not keys. The exact IDs/seeds are frozen. Intended lengths are **208/400 for L** and **200/392 for F**, including all envelope overhead; controls are still run for a planned setting if its encrypted transmission fails.

- A: temperature-one softmax over the full frozen vocabulary. No top-k/top-p masking, special-token filtering or EOS termination. EOS is an ordinary sampled token; special rendering follows the existing backend. The exact intended latent token count is attempted. Invalid UTF-8 and retokenization changes are retained without resampling.
- B: temperature-one model probabilities renormalized over the unchanged 16 admissible candidates at every step.
- C: uniform independent ideal choices from that same 16-candidate list, implemented with the frozen reproducibility RNG.

B/C do not add encryption, a header or payload. Both retain candidate exhaustion as an abort; canonical admission does not guarantee the set always has size 16. A/B/C are **different generators**, not interchangeable estimates of human cover traffic. Matching intended token length is conditioning on an external scenario fixed for both stego and control; it does not establish an unconditional traffic model. Fixed-length generation can end mid-sentence.

Invalid UTF-8 or capacity exhaustion produces no complete delivered UTF-8 message under this transport contract. Retain raw/partial artifacts and count failed generation attempts; do not automatically make the hidden sender abort an observer-visible wire event. Valid drifted A/Calgacus text is delivered unchanged and scored as received. No filtering to successful payload recovery is used for observer analysis.

## Frozen public observers and scores

Inputs are actual received bytes, agreed public profiles/context/model/tokenizer, public recipient key and the independently computed public prefix prediction. No family label, encoder trace, expected size, private key or authentication result enters an observer. Diagnostic traces are outputs, not inputs. One complete public cover-scoring pass supplies:

1. Specialized old six-token zero-path match, using the public L prediction even when the transport is F.
2. Profile-aware public extraction: bounded canonical frame/rank membership for L/F; public source reconstruction and canonical Base64/length parsing for Calgacus. Format acceptance is not tag authentication.
3. Complete-carrier candidate membership fraction, all-members indicator, one-based full-vocabulary rank, and mean log2 rank. Candidate-set exhaustion during scoring is explicitly retained as nonmembership, not hidden resampling.
4. Mean negative log2 model probability over the **received canonical token sequence**, with temperature one/full vocabulary. Also fixed suffix scores after the first eight received tokens, and encrypted-body scores after L's 72 / F's 64 tokens (frame plus 32-byte encapsulation). These are canonical-token scores, **not exact probabilities of UTF-8 byte strings**. Prefix and KEM exclusions are predetermined, not tuned from results.
5. Length-only scores: received token count and UTF-8 byte count, with fixed higher-is-stego orientation. Interpret them within the matched setting and separately from content statistics.
6. Necessary X25519 encapsulation representation: after successful public extraction, test `int.from_bytes(envelope[:32], 'little') < 2**255-19`. Report both this conditional check and the combined format-and-representation decision. It is neither a curve-membership check nor cryptographic authentication. RFC 7748 §5 reduces generated u-coordinate encodings modulo that prime; RFC 9180 §§4.1/7.1.1 serializes the ephemeral public key as `enc`. Installed pyhpke's `kem.py`, `kem_primitives/x25519.py` and `keys/x25519_key.py` were inspected: normal encapsulation uses an OS-generated X25519 key and raw public bytes. X25519 recipient decoding can accept noncanonical inputs; this test concerns this sender's output representation only.

The entire envelope is not assumed uniform. For ideal full-length C draws, conditional on a complete canonical emission, symbol constraints can still interact with abort conditioning. In an unconstrained ideal uniform byte string the canonical-u predicate accepts `(2**255-19)/2**256`, nearly one half; do not automatically transfer that number to success-conditioned transmitted controls without their generator/abort assumptions. Public inversion itself is not a universal detection proof.

Fixed score orientation is higher-is-stego for membership, prefix, format, format-and-KEM, mean log2 rank, surprisal and lengths. Report below-chance AUCs as such; no sign flipping or fitted thresholds. No trained detector. Calgacus baselines receive the same public scoring but have no new matched control allocation, so report their diagnostic outcomes descriptively rather than inventing an AUC comparison.

## Frozen analysis

Use all attempted encrypted transmissions for recovery denominators, separating methods/sizes and qualifications. Exact authenticated payload equality is the endpoint. Replays are repeated reconstruction checks, never independent transmissions. Report first identifiable failure, delivered/partial bytes, token counts, payload and envelope hashes, candidate costs, phase times and sampled process VRAM.

Successful-message rate is `8*payload_bytes/received_tokens`. Attempt-normalized useful rate gives failed encrypted attempts zero and averages over attempts; also report aggregate recovered bits / delivered tokens and recovered bytes / charged job seconds with explicit denominators. No undefined zero-token ratio is silently imputed. F's analytical savings are exactly eight tokens; this expected result is not the scientific contribution.

For each L/F × control-family cell, report planned/attempted/delivered/scorable counts and every observer outcome. Primary score comparisons use matched encrypted/control pairs where both delivered outputs are scorable, **regardless of payload recovery**; report exclusions and both margins. ROC/AUC is descriptive over those carriers. Do not turn hidden sender aborts into operational classifier negatives. Separately tabulate attempted generation outcomes, with any augmented abort convention explicitly labelled.

Uncertainty: 2000 predetermined hierarchical bootstrap draws, seed **2026091866**, resampling the four context blocks and then the two repetition/key blocks within each sampled context. Keep both payload lengths, variants and their three controls together. Report 2.5/97.5 percentile intervals for main AUC/rate summaries and paired L/F differences where estimable; incomplete comparisons disclose their support. Do not treat tokens as independent or pool replays/qualifications. Four selected contexts and two repetitions do not support broad population generalization; all-success or all-separated bootstrap intervals may collapse and do not prove reliability or perfect detection. Also present context-specific values rather than relying on intervals alone.

Generate compact tables/figures for recovery/useful rate, recognition by variant/family and resource/failure outcomes. Analysis is from retained records, never new model calls. Retain full-message scorings even when a simpler observer already rejects. Answer whether F preserves recovery; which signals remain past the header and past the KEM; which conclusions depend on A/B/C; and the measured encode/receive/observer cost. No p-value fishing, threshold tuning or operational accuracy claim.

A useful result must go beyond eight saved tokens and disappearance of a designed prefix: for example, a documented contrast in residual recognition across these complete-message generators or a consequential recovery/cost tradeoff. Even that may be a narrow implementation case study. The report must assess it candidly against the existing literature audit; internal manuscript allocation can be handled later without blocking this authorized study.

## Focused verification and provenance

Only new framing/receiver, observer and accounting contracts are checked on CPU. Cover odd counts, inferred bounds before allocation, empty/max authenticated payloads, truncation/appending, malformed UTF-8, independent nibble/inverse expectations, profile rejection, public-only observer inputs and ledger transition/restart/boundaries. Established crypto vectors remain evidence of their historical revisions; no broad suite is repeated or relabelled as validating new code.

Commit implementation, this specification, hashed profiles, allocation, OS-generated TEST_ONLY keys and environment identity before inference. Every immutable attempt records tested SHA, source-clean check, lease, input and command, phase meter, selected GPU/PID/offload evidence, carrier bytes and compact traces. Final analysis/report changes are distinguished from GPU-tested code. Stop after reviewable evidence, normal main commit/push and a proposed outline; no Stage 7 or manuscript submission.

Primary targeted update: [RFC 7748 §5](https://www.rfc-editor.org/rfc/rfc7748.html#section-5), [RFC 9180 §§4.1/7.1.1](https://www.rfc-editor.org/rfc/rfc9180.html#section-7.1.1). Other attribution and public research remain in [related_work_sources.md](related_work_sources.md) and [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
