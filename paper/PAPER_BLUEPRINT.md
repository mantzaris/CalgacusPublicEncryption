# ICISSP 2027 paper blueprint — completed Stage 9 evidence

Working title: **Finite-Packet Limits and Public Recognition in LLM-Based Encrypted Text Transport**.

This is a blueprint, not a finished or submitted manuscript. It uses the completed Stage 9 study and keeps historical samples separate. **Draft direction: a narrowly scoped empirical systems/security case study. Submission readiness and novelty are not established.** Working cryptography, arithmetic coding and canonical text checks are established ingredients, not claimed inventions.

## Provisional abstract

Publicly embedding encrypted packets in model-generated text separates content confidentiality from recognition of communication. We examine finite-packet capacity and public recognition under an actual-UTF-8 receiver contract, using a frozen quantized language model and shared canonical admissible support. Earlier controlled rank and arithmetic experiments reveal substantial trajectory-dependent capacity costs; a single carrier-budget extension preserves historical trajectories while leaving all four fresh 128-byte arithmetic attempts incomplete. A new six-context study separates fixed-length probability-weighted controls from controls that stop when the public decoder first recovers 800 stable bits. Four of six encrypted messages recover exactly; three of six stopped controls complete. Stopping alignment removes the completion-boundary distinction on delivered controls, but canonical packet replay rejects all three; local filler and encapsulation predicates have different outcomes. Separately, one historical sampled prefix passes the full public format, showing that acceptance is not authentication. We provide failure-inclusive accounting and a predicate-level evaluation that distinguishes stopping, finite-packet conformance and delivery conditioning. These bounded observations establish neither human-traffic concealment nor a universal public-extraction attack.

## Precise contribution statement

**A controlled empirical account of how finite encrypted packets, a canonical text interface and explicit stopping rules jointly affect useful delivery and public recognition, including retained capacity failures and a public-predicate decomposition that prevents completion mismatch from being mistaken for packet authentication.**

Three supported contributions, with deliberately limited scope:

1. Reproducible diagnosis of low-information trajectories and finite-packet capacity under a common public model/support: independent integer reconstruction, one unchanged-prefix ceiling extension, and useful rates that retain failed sends. The result is measured behavior of this profile, not a new entropy theorem.
2. Separation of publicly predictable framing, conditional model scores, stable-bit completion, exact boundary, midpoint filler, canonical replay and honest-output KEM representation. Existing rank 16 and public arithmetic methods remain identifiable adaptations; no new encryption or steganographic security primitive is proposed.
3. A small prospective paired-control study that holds sampling fixed and changes stopping, with actual-text public observers and private receiver checks kept separate. Its completed controls remove the stopping predicate as a discriminator but retain packet-replay rejection. A retrospective accepted prefix demonstrates why that observed rejection is not a universal format-recognition guarantee.

## Stage 9 findings that constrain the argument

All 22 jobs used GPU-tested revision`a0e790647fe1b8dc052d9ac568b0733d25e309f7`: two historical-prefix checks,18 prospective attempts, two independent receivers. New R32 recovery is 4/6; B-fixed delivers 6/6 but completes 0/6 public packet targets; B-stop completes/delivers 3/6. All six seeded pairs have identical common trajectories. Each delivered B-stop extends its B-fixed partner. No prospective fixed control reaches its first-complete prefix within its original length.

The completion-and-boundary predicate accepts 0/6 delivered fixed controls and 3/3 delivered stopped controls, as expected by construction. Full public format accepts 4/4 delivered genuine messages but 0/6 fixed and 0/3 stopped controls. Canonical replay rejects all three stopped controls; filler rejects two, and KEM rejects two, with overlap retained. Consequently, this sample **does not show weakening of full format recognition after stopping alignment**. It identifies a residual canonical finite-packet condition, while three stopped-control aborts prevent an unconditional traffic comparison. The historical 938-token prefix passes full format; the other historical 1752-token prefix does not. Those two selected snippets are not added to prospective denominators.

R/B-fixed complete-message surprisal AUC is 1.0 on four delivered matched pairs, with a degenerate empirical cluster interval [1,1]. This is a different sample from Stage 8's two-pair AUC 0.5, not a pooled or replicated effect. Only three R/B-stop pairs are available, so the frozen analysis reports raw scores rather than AUC. R is shorter and has higher canonical-token surprisal in those three pairs; length-independent statistical recognition remains unresolved. Below-zero length differences are preserved, without flipping score orientation. No general rate/recognition tradeoff follows.

The new R successful-message mean is 0.306994 useful bits/token, failure-inclusive attempt mean 0.204662, and recovered bytes per inclusive encrypted-job second 0.150662. The whole stage costs 2927.091878852 GPU-job seconds and 45988 evaluated tokens. Five capacity aborts are measured outcomes, not erased retries. [Stage 9 report](../STAGE9_STOPPING_RULE_REPORT.md), [summary](../artifacts/stage9/summary.json), [predicates](../artifacts/stage9/predicates.csv), [paired trajectories](../artifacts/stage9/paired_trajectories.json), [manifest](../manifests/stage9_evidence.json).

## Proposed argument

A public encrypted-text transport must be evaluated as a finite-message protocol: serialization, accumulated packet information, stopping boundary, packet representation and the observer's cover generator jointly determine what is delivered and what is recognizable. Token-level probability matching or exact inversion alone does not establish the distribution of complete transmitted messages. Our contribution is a bounded empirical decomposition under a common canonical admissible support, with independently checked arithmetic, retained aborts and actual-text receiver/observer inputs. The ingredients themselves are established.

## Research questions and evidence roles

1. Does the serialization contract alter usable recovery? Stage 6 compares the audited adapted Calgacus baseline with canonical rank 16 profiles. Its independent receiver checks establish actual-text examples, not portability to all model backends.
2. What limits finite encrypted arithmetic packets? Stage 7's stopped qualification and Stage 8's independent interval reconstruction and unchanged-prefix extension separate low-information capacity failure from an incorrect inverse. Stage 8 fresh cases report recovery and useful rate over all attempts, including 128-byte failures.
3. What does a public format verdict recognize? Stage 8's delivery-conditioned fixed-length result motivates Stage 9's decomposed predicates and paired B-fixed/B-stop controls. Stage 9 isolates the boundary predicate and observes residual canonical replay rejection, with explicit unavailable predicates.
4. What generalizes? No cross-model, human-channel, operational false-positive or cryptographic steganographic-security conclusion is supported. The transferable item is the evaluation decomposition; the measured frequencies belong to the frozen profiles and contexts.

## Established ingredients and closest public work

- Ziegler, Deng and Rush, *Neural Linguistic Steganography*, EMNLP-IJCNLP 2019, §3 p1212 and §4.2 p1213, already reverse arithmetic coding, discuss finite termination and distinguish a model distribution from natural language. This study's first-stable-bit/midpoint packet convention is an adaptation, not a replication of their termination. The potential difference is a retained finite-HPKE-packet/control-boundary diagnostic, not probability matching itself. [Primary paper](https://aclanthology.org/D19-1115/); [audited official revision](https://github.com/harvardnlp/NeuralSteganography/tree/14e982564aeaf9a33f7b4de440deda2184d17f12). No upstream code was copied because that tree lacks a license file.
- Yan and Murawaki, *Addressing Tokenization Inconsistency in Steganography and Watermarking Based on Large Language Models*, EMNLP 2025, Algorithm 1 p7079 and §3.1 p7080, already give full-prefix detokenization/retokenization verification at both ends. Canonical admission is reused; our bounded scan and strict UTF-8 policy are profile choices. Their paper evaluates extraction, capacity, imperceptibility and cost. A generic claim that tokenization matters or affects efficiency would overlap directly. [Primary paper](https://aclanthology.org/2025.emnlp-main.361/).
- Kaptchuk et al., *Meteor*, CCS 2021, §4 and §5.1 (author PDF pp 6–8), already identify variable entropy, capacity costs and why simple encrypted-bit reuse need not preserve sampling distributions. §5.2 uses synchronized secret PRG state. Our public arithmetic packet experiment is a different contract; it does not refute Meteor or reproduce its security claim with a public seed. Its strongest objection is that low-information capacity and probability/security distinctions are known. [Author paper](https://www.cs.umd.edu/users/kaptchuk/publications/ccs21_meteor.pdf).
- Norelli and Bronstein, *LLMs can hide text in other text of the same length*, arXiv 2510.20075v6, §3 and §3.1, already distinguish conditional ranks, probability and high-entropy inputs. Our baseline is the documented backend/text adaptation; the introduced rank 16 header is not an attack on unmodified Calgacus. [Versioned paper](https://arxiv.org/abs/2510.20075v6); [MIT upstream reference](https://github.com/noranta4/calgacus/tree/116123d4b7a74b3d56d15623355f9acf32a87165).
- von Ahn and Hopper, *Public-Key Steganography*, EUROCRYPT 2004/ePrint 2003/233, §6 constructions, permits public extraction under specific channel and ciphertext assumptions. Extraction alone is not a universal distinguishing argument. Here each predicate must be paired with its generator and message-boundary contract. [Primary source](https://eprint.iacr.org/2003/233).
- HPKE and X25519 supply established cryptography and representation, not an LLM-dependent encryption primitive. The canonical encapsulation condition follows RFC 7748 §5 and HPKE serialization; it is neither authentication nor a proof of full-envelope uniformity. [RFC7748](https://www.rfc-editor.org/rfc/rfc7748.html#section-5), [RFC9180](https://www.rfc-editor.org/rfc/rfc9180.html).

The bounded primary-source audit is retained in [related_work_sources.md](../docs/related_work_sources.md) and [comparator audit](../docs/stage7_comparator_audit.md). Stage 9 rechecked the specific arithmetic, stepwise-verification and Meteor passages above, without starting a broad survey. Allocation across the author's other projects remains a later submission decision, not an execution gate or a declared novelty clearance.

## Regular-paper section plan

Target a concise 10–12-page proceedings-shaped draft, while applying the separate submission character requirement below.

| Section | Purpose and proposed space | Evidence |
|---|---|---|
| 1. Problem and contribution | ~1 page; finite delivered messages, not isolated token distributions | Precisely bounded contribution, failure-inclusive question |
| 2. Threat/traffic model and prior work | ~1.5 pages; public model/context/class, receiver secret, exact wire; related assumptions | Protocol; explicit A/B/C and B-fixed/B-stop definitions |
| 3. Transport and observer contract | ~2 pages; established F/R mechanisms, public finite size, separate predicates | Profile/code identities; independent checks; no new coder claim |
| 4. Study design and accounting | ~1 page; distinct stages, prospective assignments, paired trajectories, startup cost, abstention | Frozen allocations, leases, attempt records |
| 5. Results | ~3 pages; serialization, capacity, then stopping versus packet recognition | Stage 6, Stage 8, Stage 9 in separate panels/tables |
| 6. Interpretation and limitations | ~1–1.5 pages; which conclusions change with control model; missing evidence | Predicate decomposition, survivor sample limits, known principles |
| 7. Conclusion | ~0.25 page; bounded findings and reproducibility | No universal concealment or attack claim |
| References | remaining space; primary sources and anonymized artifact citation | Source audit and claim-evidence matrix |

Do not organize the paper as a chronological report of nine stages. Stages label provenance inside the three scientific questions. Stage 7 qualification is diagnostic context, not a competing independent cohort. Stage 1–4 examples need at most a short motivation paragraph; Stage 5 is research planning rather than experimental evidence.

## Figure and table plan

- Contract diagram: received UTF-8 → canonical support → stable packet completion → exact boundary; filler/replay and KEM as separate branches. Mark private HPKE opening outside public observer.
- Recovery/useful-rate table: Stage 6 Calgacus/L/F, Stage 8 F/R, Stage 9 R as separate strata; failures in attempt denominators; independent receivers in a separate row.
- Capacity figure: Stage 8 independent historical stable-bit curve plus unchanged-prefix extension, and fresh nested 512/1024/1536/1984 checkpoints. No repeated-checkpoint pseudoreplication.
- Recognition figure: Stage 6 generator-specific score distributions; Stage 8 fixed-length survivor comparison labelled n=2; Stage 9 paired boundaries and decomposed public outcomes, never one pooled headline AUC.
- Predicate table: attempted/delivered/scorable/first-complete, exact end, filler, replay, KEM; unavailable reasons and conditional denominators.
- Resource table: model startup plus encode/receive/public-score seconds, evaluated tokens, sampled memory and zero-useful-output aborts.

All figures should be regenerated from linked saved records. Existing code-native plots remain standalone PNG/SVG assets. No illustrative image generation is needed.

## Material limitations and genuinely missing evidence

One frozen quantized model/backend/GPU, constrained support, short selected public contexts, publicly agreed size classes, strict unchanged text and a hard model window limit the domain. The six new contexts all share a short note template; they are not six random human channels. Stage 8 has only two fresh R deliveries; extra controls and replays do not increase that count. B-stop is a diagnostic model distribution, not human traffic or the uniquely correct null. Deterministic midpoint termination is our adaptation; its public constraints cannot indict every arithmetic stegosystem. Ciphertext bytes need not be uniform; no content confidentiality theorem for this complete composition is supplied. Public test keys are reproducibility fixtures, not secret deployments.

A broad claim about concealment or a general rate/recognition tradeoff still lacks sufficient independent genuine deliveries, diverse channels/models and a validated keyed comparison under its real shared-secret assumptions. Those are limits, not an automatic new experiment proposal. A narrowly scoped empirical diagnostic paper instead needs a crisp causal/accounting argument and a claim-specific prior-work check showing why the retained stopping-boundary counterexample adds to known finite-coding principles. No missing private manuscript is an execution blocker.

## Venue and schedule, checked 18 September 2026 local time

[Official guidelines](https://icissp.scitevents.org/Guidelines.aspx) require regular submissions of **10,000–50,000 characters excluding whitespace**, including references, tables, figures and appendices, ready for double-blind review. Proceedings limits are separate: **12 pages for accepted full papers, 8 for accepted short papers**, with up to 4 paid extra pages. Use the official template. Respect anonymity/public-preprint restrictions during review, original-work rules and the stated AI-text disclosure/citation policy; review the official wording before submission.

The [official dates](https://icissp.scitevents.org/ImportantDates.aspx) confirm the intended **22 October 2026 AoE second-stage regular-paper submission**, notification 4 December and camera-ready/registration 18 December. Suggested nonexperimental work: scope/claims and artifact review by 25 September; a bounded draft by 8 October if the final recommendation supports it; technical/citation/anonymity review by 15 October; character/template checks and submission decision by 20 October. No submission is performed by this task. Dates/policies can change; [retrieval metadata](../artifacts/stage9/venue_sources.json) records this check.

## Draft decision and the smallest remaining requirement

**Supporting evidence:** the implementation/inverse is independently checked; real UTF-8, fresh receivers, failed sends and startup costs are retained; the F/R common-support comparison and prospective paired controls isolate concrete protocol choices. The stopped controls show that completion matching alone does not erase the observed finite-packet replay condition. The accepted historical prefix prevents overclaiming that public format proves ciphertext. These form a coherent, bounded measurement argument rather than a proposed secure construction.

**Strongest objection:** arithmetic probability matching, finite termination, tokenization consistency, low-entropy difficulty and observer/distribution assumptions are already established by the cited work. Our precise midpoint convention, restricted alphabet and chosen contexts may make the findings too implementation-specific for a distinct regular contribution. Four new genuine deliveries and three stopped controls do not resolve a broad recognition tradeoff, and the earlier stages cannot be pooled to manufacture independent replication.

The next action is **one narrowly scoped regular-paper draft followed by a claim-and-evidence review**, using these existing artifacts only. Concentrate on the validated finite-message decomposition and adverse capacity findings; retain the three rejected stopped controls and all five new aborts. The draft review must decide whether the empirical result adds enough beyond the known principles and this particular profile. That is the genuinely missing submission decision. It requires no additional experimental allocation: proposed inference budget **0 GPU-job seconds,0 evaluated tokens,0 attempted cases**. No draft beyond this provisional abstract/blueprint is written in this task, and no experimental stage is automatically commissioned. Allocation of contributions across the author's projects can be decided later without reopening an execution gate.

Broad deployment/security assertions would need additional evidence—independent channels/models, adequately supported genuine deliveries and comparators retaining their actual secret assumptions—but they are outside the proposed narrow paper. The 128-byte arithmetic failures may remain negative findings; making them work is not a prerequisite to an honest bounded result. A new theorem is not required for this draft decision. Novelty and submission readiness remain unconfirmed.

**Recommendation: Proceed to a narrowly scoped regular-paper draft.**
