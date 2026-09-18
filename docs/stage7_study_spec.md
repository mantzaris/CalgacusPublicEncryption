# Stage 7 prospective specification — frozen before qualification

Authorized 18 September 2026. Starting main c2b4f91f0cc6842c37133ce31576ae2fa455b2a6. Historical observations remain development evidence; no pooling with this prospective exploratory comparison. Internal manuscript overlap is not an execution gate. No claim of novelty is cleared.

## Question and fixed methods

Under identical model, context, candidate ordering and canonical-prefix admission, does probability-matching arithmetic mapping change recovery, finite capacity, complete-message recognition and cost relative to uniform nibble mapping?

F inherits the existing length-inferred rank16 implementation. R is an independently written adaptation of the public arithmetic mapping in Ziegler et al. (2019), with the differences in stage7_comparator_audit.md. Both inherit the exact existing first16/top128 candidate function. No model, precision, cache, batching, temperature, candidate-pool or tokenizer changes. R has a fixed **1536 carrier-token ceiling**, F retains its 512 bound and actual 200/392 tokens. Context window remains2048. No parameter search, replacement tokens, normalization or retries.

Four new contexts, fixed without outcome selection:

1. `A field guide describing the shape of a maple leaf:`
2. `A kitchen note on arranging clean cups on a shelf:`
3. `A station bulletin about maintaining a platform clock:`
4. `A garden journal describing rain beside a clay pot:`

The public channel class is32 or128 payload bytes, corresponding to100 or196 envelope bytes. It is **pre-agreed public configuration**, not transmitted metadata; neither method claims self-delimiting transport or length concealment. Each complete method/size/context profile is bound through unchanged HPKE info/AAD. No cross-profile ciphertext reuse. HPKE Base mode remains unauthenticated as to sender; authentication precedes plaintext delivery, including the inner u32be payload length. Size-class envelope bounds imply the required authenticated inner size under the unchanged no-padding record. Test keys are published fixtures, not operational secrets.

## Arithmetic packet contract

32-bit inclusive integer intervals; cumulative partition edges `low+floor(width*cumulative/total)`. E1/E2 equal-half and E3 middle-half underflow renormalization. Conditional float32 logits are converted to float64 softmax over exactly the ordered16 candidates. Frequencies sum65536: allocate one unit to each candidate, floor `p*(65536-16)`, and allocate the remaining units by descending fractional remainder, ties by candidate index. Thus all16 retain positive intervals; an unexpected zero width is rejected.

Packet bits are MSB first. The finite packet is followed by a **public midpoint suffix: 1 then infinite zeros**. Stop at the first token that makes at least `8*public_envelope_bytes` stable bits available. Excess stable bits must agree with the suffix. Public decoding repeats the integer mapping using the recovered packet and already publicly computed tables to verify canonical termination, with no extra inference. Reject incomplete terminal intervals, extra tokens after the first terminal token, invalid candidate choices, noncanonical bytes, wrong class, and carriers over1536 tokens. Intermediate pending-underflow state is retained diagnostically, not passed to receivers.

The initial CPU-only zero-suffix draft failed independent boundary checks; its failed output is retained. It was corrected before profile/qualification freeze. This suffix is a public signal to evaluate, not a concealment mechanism. Finite integer rounding approximates conditional probabilities; the complete HPKE packet is not assumed uniformly random. Canonical X25519 representation and termination may remain recognizable.

## Allocation and gate

Additional ceiling:14400 conservative startup-inclusive GPU-job seconds,300000 evaluated tokens,128 attempts. Anchor the shared ledger at7541.8848853629825 seconds,124994 tokens,214 attempts; authorization is explicit and no unused previous allowance is carried. Imports/model loading, prompt prefill, every emitted/scored/reconstructed token, failure and shutdown count. Full fixed reservations precede worker startup; shared lock, inherited one-shot leases, absolute deadlines and prefix checkpoints remain mandatory. No CPU model inference.

Qualification: two synthetic raw-envelope fixtures (100/196 bytes), two fresh real HPKE cases (32/128), and up to two independent receiver replays, six slots. Exact32-byte synthetic+HPKE+fresh-process reception must pass. Any inverse, authentication, invariant, unexplained numerical, accounting, provenance, lease or deadline failure stops. Retain pure capacity failures; a large-payload capacity failure alone does not invalidate a qualified small-payload comparator. No main study if meaningful recovery is not qualified. At most16 qualification slots and8 specifically justified investigations are authorized; only the six declared qualification slots are scheduled.

Main:32 encrypted attempts = F/R ×4 contexts ×2 sizes ×2 repetitions. Eight independent recipient keys assigned `2*context+rep`; same payload/key/context paired across methods with fresh independent HPKE randomness. Payloads are SHAKE256 of `ICISSP2027 Stage7 binary c={c} n={n} r={rep}`, digest(n). Method order is counterbalanced by context+rep+size. The allocation file gives immutable case IDs, exact seeds and reservations.

Controls:64, A and B for every planned encrypted setting, including failures. **Length-conditioned analysis**: target associated delivered carrier's retokenized token count; failed-source fallback1536 R,200/392 F. The observer receives only the public size class, never the target count/evaluator association. A samples the full vocabulary at temperature1; EOS is an ordinary token and no early stop or filtering occurs. B samples exact conditional probabilities renormalized over the same16 admitted candidates. PCG64 seeds are frozen reproducibility parameters. Neither uses encryption or headers. No resampling invalid UTF-8, drift, exhaustion or early failure. Successful internal completion and observable wire events remain distinct.

Eight replay slots: contexts0 and2, repetition0, both methods/sizes. Unavailable predetermined sources leave slots unused; no substitution. Replays are not independent messages. Main implementation/allocation/analysis must be committed after qualification and its startup-inclusive forecast before release. If forecast is too high, reduce repetitions symmetrically before main; never remove difficult conditions based on main outcomes.

## Observers and analysis

One complete public scoring pass starts from received UTF-8, public profile/context, model/tokenizer and recipient public key. No private key, payload, expected hash, sender traces, receiver outcome or family label is an observer input. Compute canonical token negative log2 likelihood, full-vocabulary log2 rank, candidate membership, token/byte lengths, public frame/termination acceptance and necessary `u < 2**255-19` encapsulation representation. Format is not tag authentication. No body-region score is used: F's64-token KEM offset is not applied to R. Canonical-token likelihood is not a proven UTF-8-string probability.

Fixed higher-is-carrier orientations: mean surprisal, mean log2 rank, membership fraction, format acceptance, format+canonical-KEM, token and UTF-8-byte lengths. Report reverse-direction outcomes without flipping. Report conditional-admissible surprisal where every token is a member; otherwise unavailable. Primary AUCs use complete-message scores against A and B separately, within method, over delivered scorable matched pairs, without selecting on authentication. Explicitly list absent wire events and unavailable scores. Present statistical and structural recognition separately; length-conditioned AUCs do not remove byte-length signals or establish incremental independence from all length information. No thresholds tuned, no detector trained.

Recovery denominators include **all attempted encrypted transmissions**. Capacity failures are failures. Report successful-message bits/token separately from attempt means (zero usefulness for aborts), aggregate recovered bits/delivered tokens and recovered bytes/charged encrypted-job time. Abort attempts have no transmitted token denominator; assigning zero useful rate does not make an internal abort a visible traffic event. Keep qualification, main controls and replays separate.

Uncertainty:2000 hierarchical bootstrap draws, fixed seed2026091907; resample four contexts then two repetition/key blocks inside each context, keeping sizes/methods/controls jointly grouped. Report per-context outcomes and paired R-minus-F AUC differences. Do not treat tokens/replays as independent. Collapsed all-success or separated-score intervals are descriptive degeneracy, not population guarantees. Four selected contexts sharply limit generalization.

Report phase timings, charged job time, sampled peak memory, complete candidate search cost, stable-bit progress/termination, all failure categories. Stop main on correctness/accounting/numerical/lease/deadline/provenance failures; capacity and ordinary-control serialization failures are retained. Stop if a next full reservation cannot fit. No discretionary retries or automatic Stage8.
