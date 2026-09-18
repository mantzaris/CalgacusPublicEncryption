# Stage 5 contribution and next-study decision

**Recommendation: NO DISTINCT CONTRIBUTION IDENTIFIED YET.** Do not authorize a larger experiment matrix on the strength of the present results. This is a provisional publication-direction decision, not a claim that a distinct contribution is impossible. Latest submitted manuscript versions remain unconfirmed, but the inspected versions already show substantial overlap.

The strongest evidence supporting this decision is direct: ImageCalgacus already combines full-prefix tokenization checks, encrypted packet transport, fresh artifact-only receivers, useful-rate accounting and context-aware detection; RankCloak already studies bounded artifact encodings and recovery/detection tradeoffs. Published tokenization-consistency work precedes the admission rule. Replacing the encryption with HPKE, selecting a top-128/radix-16 profile, or exposing its deliberately clear header does not establish a distinct scientific contribution. [Inspected sources and exact locators](docs/related_work_sources.md); [claim-level comparison](docs/novelty_matrix.md).

The strongest opposing evidence—the reason to retain the project—is a particularly clear, reproducible example: actual encrypted payload recovery from saved UTF-8 and fresh receivers can coexist with a predictable public prefix. The three specified cover generators give substantially different model-based interpretations of that prefix. This is useful supporting evidence for an evaluation argument, but the general distinction is established and the present example is specific to our added profile.

**Strongest defensible statement:** on the frozen public rank16 profile, the retained development cases demonstrate exact encrypted-payload transport while exposing deterministic public framing, illustrating why recovery and confidentiality do not establish concealment. This is a bounded engineering observation, not yet a standalone research contribution or an attack on original Calgacus.

## Baseline and evidence boundary

Review date: **18 September 2026**. Actual starting main: **`a19d49f936c478d380ec38c27594a0fec501ca12`**, clean working tree. Latest GPU-tested revision: **`32edd3bf54712a8134659f298b8958462024c2a0`**. Repository: [mantzaris/CalgacusPublicEncryption](https://github.com/mantzaris/CalgacusPublicEncryption). Work is directly on main; no experimental source, profile, report, attempt, ledger or ceiling is changed.

Read the repository instructions, complete research plan, four stage reports and Stage 1 review, protocol/threat model, transport/prefix documents, related-material manifests and relevant summaries/records. Source identities and file hashes are in [stage5_sources.json](manifests/stage5_sources.json). This stage performs document/source inspection and retained-file arithmetic/hash reconciliation only. No model inference, experiment, benchmark, detector training, test-suite run or hardware rediscovery occurred. Earlier CPU/GPU results retain their original tested revisions.

All existing examples remain **development-only**, excluded from future held-out evaluation. Available related manuscripts are inspected sources, not independently reproduced experiments. Public test private keys in development bundles cannot protect real secrets.

| Evidence stratum | What the retained records establish | Limits and distinctions |
|---|---|---|
| Stage 1 original-function reference | Two of two reference-function examples passed on the selected local model/backend. | Reused upstream functions with a different execution profile; not replication of every paper claim or original environment. |
| Stage 1 adapted Calgacus encrypted baseline | 32-byte: **5/6** exact; 128-byte: **1/6** exact. Five segmentation failures and one invalid-UTF-8 failure are retained. Three successful fresh-process replays and three ordinary controls are separate. | Six recipient keys; no selective erasure of failures. The 21 charged cases include one preflight/carry-in case. Original provenance limitations and the declared 30-second carry-in remain documented in the review. |
| Stage 2 adapted Calgacus pilot | Four historical replays: three exact recoveries and one expected rejection. Four fresh transmissions: **2/2** at each size. Two fresh-process replays and two ordinary controls. | Correct rejection is not recovery. Later small-sample success does not erase Stage 1 failures or estimate a general recovery rate. |
| Stage 3 new public rank16 comparator | Two historical-envelope fixtures recovered their envelope bytes after **new encoding**. Four fresh transmissions: **2/2** at each size. Two fresh-process 128-byte replays passed. Two ordinary full-message controls. | Fixtures neither repair the old carriers nor establish new-profile HPKE binding. Fresh transmissions bind the new profile. Descriptive comparison, not randomized paired evidence of superiority. |
| Stage 4 prefix diagnostic | Three public predictions; six selected historical Stage 3 prefixes match. Eighteen six-token controls: **0/6 matches in each of A, B and C**, all valid nonmatches. | No new encrypted transmission or recovery. Six historical checks include two fixtures and four fresh carriers; replay copies are not independent samples. Prefix controls are not full-message traffic. |

Evidence links: [Stage 1 summary](artifacts/stage1/summary.json), [failure analysis](artifacts/stage1/failure_analysis.json), [Stage 1 review](STAGE1_REVIEW_REPORT.md), [Stage 2 summary](artifacts/stage2_pilot/summary.json), [Stage 3 summary](artifacts/stage3_transport/summary.json), [Stage 4 summary](artifacts/stage4_prefix/summary.json), [predictions](artifacts/stage4_prefix/public_predictions.json), [historical reanalysis](artifacts/stage4_prefix/historical_reanalysis.json). Source hashes and case indices are recorded in the Stage 5 manifest; original stage evidence manifests remain authoritative for execution provenance.

## What the observations mean scientifically

The main composition is **conventional encrypt-then-embed**. Confidentiality is delegated to the established HPKE implementation under its assumptions. Authenticating a ciphertext before delivery is distinct from authenticating its sender: anyone with the public key can create a fresh valid Base-mode message. Neither a new encryption primitive nor LLM-dependent cryptographic hardness is proposed. No proof of public-key steganographic security, sender authentication, edit robustness or operational concealment has been established. See [RFC 9180 §§5 and 9](https://www.rfc-editor.org/rfc/rfc9180.html#section-9) and the retained [threat model](docs/threat_model.md).

Public invertibility is **not a universal detection argument**. Classical public-key constructions already permit public extraction under explicit channel/ciphertext assumptions. For this project's Base64 adapter, the recognizable structure is canonical Base64 plus envelope-length constraints after public inversion. For rank16 it is the bounded frame and, more simply, six initial zero nibbles. Their occurrence under the chosen cover distribution matters; an observer cannot verify an HPKE tag without the key. A syntactic positive is not proof of a valid ciphertext. The [classical construction, §6.1](https://eprint.iacr.org/2003/233.pdf) is an important counterexample to the overly broad “public decoder implies detectable” argument.

For `public_utf8_rank16_v1` alone, lengths 68–196 fit in the last byte of a four-byte big-endian field. Its first six high-first nibbles are zero. Under the same public context, model, tokenizer, precision, cache and tie ordering, successful canonical emission therefore begins with the public zero path. This says nothing corresponding about unmodified Calgacus.

| Context | Historical rank16 prefix matches | B: model-derived six-zero probability | C: ideal uniform-admissible probability | Observed A / B / C matches |
|---|---:|---:|---:|---|
| Garden | 2/2 | 0.04173936315 | 16⁻⁶ ≈ 0.0000000596046 | 0/2 / 0/2 / 0/2 |
| Library | 1/1 | 0.11624181360 | 16⁻⁶ ≈ 0.0000000596046 | 0/2 / 0/2 / 0/2 |
| Rainfall | 3/3 | 0.00439316302 | 16⁻⁶ ≈ 0.0000000596046 | 0/2 / 0/2 / 0/2 |

A is temperature-one full-vocabulary generation; B renormalizes model probabilities over the 16 admitted choices; C samples their indices uniformly. B's probabilities are products along the publicly computed path. C assumes independent uniform draws and 16 available candidates on that path. These describe ideal specified generators; the two frozen seeds produce deterministic diagnostic examples. A's retained latent token-path scores cannot automatically be equated with the actual text observer event because alternative tokenizations can contribute. No population false-positive estimate follows from the table.

Abort conditioning is equally important. The structural statement concerns **successful transmissions**. In a declared attempt space with abort mapped to nonmatch on both sides, let `q_S` be the probability of producing a complete valid stego carrier. Its prefix acceptance is `q_S`; B's six-token acceptance is the path probability `p_B`. Conditioning both generators on successful output instead requires B's success probability `q_B`, yielding `p_B/q_B`. These are elementary bookkeeping identities, not a new theorem or a measured full-traffic advantage. A wire-only observer also needs a declared observation/scheduling model before an absent message can count as an observed abort. Existing samples do not establish those rates.

Thus a potentially interesting residual question is whether **finite packet framing, canonical text constraints and observer knowledge jointly change a useful-transport versus recognition decision across justified full-message channels**. A nontrivial, transferable answer could matter. At present the question is broader than the evidence and overlaps ImageCalgacus's existing comparison. Merely collecting more cases would not resolve that overlap.

## Three possible directions

The intended deadline is **22 October 2026 AoE**, 34 calendar days from this review, as listed for second-stage regular / position papers on the [official conference page](https://icissp.scitevents.org/ImportantDates.aspx). Feasibility estimates below are judgments about missing work, not measured implementation schedules or an authorization to execute it.

### A. Public encrypted-payload transport systems comparison

**Candidate contribution statement:** establish which public text codecs deliver useful authenticated payloads from literal UTF-8, at what cost, against explicitly informed observers under declared full-message cover channels.

Research questions:

1. Which transport choices preserve exact bytes without diagnostic side information, and what failure-inclusive payload rate remains after packet overhead?
2. Does the codec ranking by useful rate change when recognition is assessed under justified full-message distributions and public observer knowledge?
3. What does a shared-secret reference achieve under its additional setup assumption, without treating it as the same public-sender task?

**Strongest objection:** ImageCalgacus already has the artifact boundary, full-prefix rank coding, encrypted packet contract, multiple coders, useful rates and informed observers. RankCloak adds artifact representations and detector tradeoffs. Public-key wrapping alone is incremental.

**Potential non-incremental difference:** a validated, transferable public-sender deployment constraint that changes a substantive systems conclusion. No such constraint/result is currently established. The available work supplies infrastructure and selected counterexamples, not this contribution.

**Missing work/evidence:** a justified application/channel model; independent evaluation data; a validated public arithmetic adapter and a separately validated keyed reference; fair finite-packet termination and failure accounting; uncertainty at the independent payload/context level; manuscript-overlap clearance. These interfaces are not working baselines. No model or detector expansion is warranted until a question survives the overlap gate.

**Feasibility / disposition:** high schedule risk within 34 days, especially with comparator qualification still missing and only 1,151 evaluated tokens of original headroom. Reject as the immediate submission core. More repetitions of the current codec would not answer the strongest objection.

### B. Transferable framing and recognition analysis

**Candidate contribution statement:** characterize when publicly testable packet constraints survive actual text serialization as recognition signals, and how generator support and abort conditioning change the resulting comparison.

Research questions:

1. What efficiently recognizable constraint remains after extraction, and what is its acceptance probability under each explicitly specified cover channel?
2. Can a result extend beyond a fixed clear header while allowing public extraction cases with no distinguishing gap?
3. When does consistent inclusion of aborts reverse a substantive conclusion about recognition versus useful delivery?

**Strongest objection:** public-channel security definitions, distribution matching and conditioning are established; the six-zero header example is elementary and introduced by us. The local manuscripts already discuss support, failures and observer knowledge. A generic inverse-format bound alone is not enough.

**Potential non-incremental difference:** a sharp criterion or counterexample covering a meaningful class of finite public transports, including ambiguous serialization and consistent observation of aborts, with consequences not already implied by prior formulations. This remains a candidate problem, not a result, theorem or novelty-cleared study.

**Available evidence:** the most relevant current support is the Stage 4 model-derived prefix contrast and Stage 1 serialization failures, with Stage 3 exact transport. None measures full-message cover rates or establishes transfer across methods.

**Missing work/evidence:** first, a precise new statement and prior-work counterexample check; only if that survives, claim-specific implementations and full-message evaluation with independent development/evaluation separation. A deliberately randomized header ablation alone would just remove the constructed signal and would not demonstrate concealment.

**Feasibility / disposition:** a short analytical claim assessment is feasible before the deadline; a regular-paper result is not yet credible enough to authorize experiments. This is the most promising question to examine next, but **not a recommendation to proceed to a regular-paper study now**.

### C. Substantive position paper

**Candidate contribution statement:** argue for an attempt-level, actual-wire evaluation contract for public-sender linguistic steganography, showing which published evaluation choices can otherwise lead to consequentially wrong deployment decisions.

Research questions:

1. Which specific conclusions in existing evaluations would change under that contract rather than merely acquire extra reporting detail?
2. What concrete, falsifiable research agenda would distinguish public-sender transport from a shared-secret generative channel?

**Strongest objection:** separating encryption, concealment, recovery and robustness is longstanding; the tokenization paper and ImageCalgacus already implement important parts of the proposed contract. A checklist assembled from these points is not automatically a substantive position.

**Potential non-incremental difference:** a defensible argument about a currently unmet evaluation requirement with a consequential example across existing methods, plus a bounded agenda. The present profile-specific example alone does not supply that argument.

**Available evidence:** reproducible diagnostic examples and an auditable protocol can illustrate a position. **Missing evidence:** an accurate claim-level account of which existing conclusion is inadequate and why the proposed remedy changes it; author-confirmed overlap clearance; a reason the argument belongs in a separate paper rather than related work's limitations.

**Feasibility / disposition:** writing could fit 34 days, but schedule feasibility is not scientific distinctness. Reject an automatic position-paper fallback. Reconsider only after a distinct thesis survives the same overlap check; no finished paper is commissioned here.

## Decision and use of the existing work

Treat the implementation and evidence as **reusable infrastructure and supporting evidence for a narrower contribution**. They are not currently a cleared core for a separate regular or position paper. The concrete public-envelope/framing case may fit an extension or limitations discussion of RankCloak or ImageCalgacus better than another overlapping submission, subject to author agreement and submission policies. This is a proposal for discussion, not authorization to alter or submit those manuscripts.

The absence of confirmed latest versions is a genuine gate, but it would be misleading to suggest that supplying them automatically clears novelty. The current texts already defeat broad claims for rank inversion, radix-16 encoding, full-prefix verification and artifact-only recovery. A new claim must survive those actual sections.

Genuinely needed materials/confirmations:

- **CARTS:** author confirmation whether arXiv:2609.10744v1 matches the current submitted/under-review text; if not, the changed main source and relevant theoretical/evaluation sections.
- **RankCloak:** exact submitted/current main and supplement, or a confirmed diff against `ce853d42…` `main3.tex` / `supplementary3.tex`; whether public-prompt artifact recognition, sequence filtering or the evaluation contract are claimed there.
- **ImageCalgacus:** exact submitted/current main and companion, or a confirmed diff against `2bec65db…`; confirm which companion material is part of the submission and the intended claims for text correctness, observers and failed transmissions.
- **Authors of the related projects:** agreement on claim allocation and disclosure of overlapping infrastructure/results if any separate submission is pursued. Filenames, repository timestamps and compiled “submission” PDFs cannot establish these facts.

## Resource status and next action

| Resource | Before and after Stage 5 | Original ceiling | Remaining, not authorized for use here |
|---|---:|---:|---:|
| Conservative GPU-job seconds | 1,732.698757323 | 7,200 | 5,467.301242677 |
| Evaluated tokens | 23,849 | 25,000 | 1,151 |
| Attempted cases | 64 | 72 | 8 |

The authoritative ledger remains **32,183 bytes**, SHA-256 **`9cf35c86ee1aa96868f244bb4703835da4e7b866d192e0a135e265c08a45f304`**; checkpoint unchanged. Stage 5 increment: **0 seconds / 0 tokens / 0 cases**. Documentary file hashing is not model inference. Historical ledger reservations, failures and carry-in accounting are retained.

Measured prior costs explain why unused time is not a study plan: Stage 3's two fresh 128-byte encode/receive/public-extraction jobs took 60.800–60.802 seconds and 1,233–1,236 evaluated tokens including startup; either job used more tokens than remain. Stage 4's tiny prefix jobs spent about 305 of 331 charged seconds loading/verifying. These observations are not a forecast for unimplemented comparators and do not justify another allocation.

**One recommended next action:** a separately approved, at-most-five-working-day author/version reconciliation and analytical claim assessment focused on Direction B, with a stop decision if no distinct statement survives. Proposed additional experimental budget: **0 GPU-job seconds, 0 evaluated tokens, 0 cases**, and no CPU model inference or benchmark. The bounded deliverables, acceptance criteria and stopping rule are in [next_study_spec.md](docs/next_study_spec.md), marked **NOT AUTHORIZED OR EXECUTED**. No regular-paper experiment matrix is proposed because its scientific premise has not passed the gate.

## Documentation verification

The review checked section/theorem locators against actual primary text, manuscript includes and retained project summaries; compared all tracked non-deliverable files against the starting revision; checked local Markdown targets and JSON syntax; and reviewed the five-file diff for unsupported claims. These are documentation checks, not a CPU validation campaign. No earlier CPU results are attributed to new code, because no experimental code changed. The source manifest records evidence hashes so subsequent readers can distinguish this decision from the untouched historical reports.
