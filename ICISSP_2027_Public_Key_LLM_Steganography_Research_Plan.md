# ICISSP 2027 research and paper plan

Planning date: September 18, 2026. Target submission: October 22, 2026.

Status: research design only. No experiments, implementation, or manuscript have been produced for this project. All numerical experiment outcomes remain unknown. Compute estimates are planning assumptions, not benchmarks.

Compute constraint: use Alex's LOCAL GPU. No RunPod, cloud GPU, paid model API, or multi-GPU requirement. GPU model, VRAM, available hours, and operating environment still need confirmation.

## 1. Recommendation and publishability

Pursue a security-analysis and experimental-systems paper about **the composition limits of public-key encryption with Calgacus-style rank transcoding**. Use established cryptography for confidentiality. Make the research contribution a precisely scoped analysis and evaluation of public extraction, recognizable ciphertext representations, channel mismatch, and recovery under an actual text transport.

The central question is: **When an LLM steganographic encoder becomes publicly executable, which properties survive encrypt-then-embed, and which new detection opportunities arise?**

Do not propose a new encryption primitive based on the supposed hardness of recovering a prompt. Do not label a working HPKE-plus-Calgacus demonstration a novel public-key stegosystem without establishing the relevant concealment property.

Publishability assessment:

- An encryption-library wrapper with successful round trips is a weak contribution.
- Showing only that ciphertext gives Calgacus poor-looking output is also weak: the original paper already describes a high-entropy hash example and a rank/probability mismatch.
- A regular paper is plausible if it contributes a clearly delimited composition result or attack, validates it across independent keys and held-out contexts, compares against a competent generative steganography baseline, and produces an actionable account of the tradeoffs. This remains conditional on checking overlap with Alex's other papers.
- A well-controlled negative result can support a regular paper. Successful concealment is not a prerequisite; adequate novelty and evidence are.
- If the only findings duplicate known mismatch observations, use the position-paper fallback only if there is a distinct, evidence-supported argument. Otherwise, do not force this project into a submission.

Primary research direction: category A below, investigated against the requirements of category B. Feasible fallback: an evidence-backed position paper arguing for separate confidentiality, channel, extraction, and implementation contracts in public-key LLM steganography, supported by the audited prototype and bounded counterexamples.

Candidate titles:

1. **Public-Key Encrypted Communication through LLM Steganography: Composition Limits and Practical Tradeoffs**
2. **Public Decoding as a Steganalysis Tool for Rank-Transcoded Ciphertexts**
3. **What Public-Key LLM Steganography Must Guarantee: A Composition Framework and Research Agenda** (position-paper fallback)

Use title 2 only if the public-decoding result is substantial and survives comparison with prior work.

## 2. Verified venue constraints

| Item | Official position verified on the planning date |
|---|---|
| Second submission stage | Regular and position papers: October 22, 2026, Anywhere on Earth |
| Notification | December 4, 2026 |
| Camera-ready and registration | December 18, 2026 |
| Event dates | February 22-24, 2027 |
| Regular submission | PDF; 10,000-50,000 characters excluding whitespace; all components count |
| Position submission | PDF; 8,000-40,000 characters excluding whitespace; all components count |
| Proceedings limits | Regular accepted as full: 12 pages; regular accepted as short: 8 pages; position: 8 pages |
| Extra pages | Up to four, subject to fees; do not depend on them |
| Format | English, PRIMORIS; official SCITEPRESS Word/LaTeX template strongly advised at submission and mandatory at camera-ready |

Sources: [Important Dates](https://icissp.scitevents.org/ImportantDates.aspx), [Call for Papers](https://icissp.scitevents.org/CallForPapers.aspx), [Guidelines](https://icissp.scitevents.org/Guidelines.aspx), [Templates](https://icissp.scitevents.org/Templates.aspx).

Review is double blind. Remove identifying information and acknowledgments from the review version. The guidelines prohibit posting the submitted paper publicly while under review and prohibit substantial overlap with published or concurrently submitted work. Keep the new manuscript private during that period; prepare an anonymous artifact if permitted. Track the venue's AI-text disclosure requirements when writing the eventual manuscript. [Submission guidelines](https://icissp.scitevents.org/Guidelines.aspx).

Remote presentation is supported, but the homepage describes it as an exception for speakers unable to travel. Online presentation instructions include live Zoom participation; a backup recording does not replace attendance. Because remote participation is mandatory for Alex, obtain written confirmation of the applicable arrangement and its satisfaction of publication requirements before committing registration fees. No organizer has been contacted by this planning work. [Homepage](https://icissp.scitevents.org/), [Online presentation details](https://icissp.scitevents.org/presentationdetails.aspx).

Both full and short proceedings papers are sent for indexing consideration, including Scopus and Google Scholar. This covers accepted position papers, which are short papers. The organizer does not guarantee inclusion or timing: the indexers decide. The abstracts track is not a proceedings/indexing substitute. [Glossary](https://icissp.scitevents.org/Glossary.aspx), [Indexing FAQ](https://icissp.scitevents.org/FAQ.aspx).

## 3. Calgacus identification and evidence boundary

The exact source is Antonio Norelli and Michael Bronstein, **LLMs can hide text in other text of the same length**, arXiv:2510.20075. The current version found is v6, January 16, 2026. Its official implementation is [noranta4/calgacus](https://github.com/noranta4/calgacus), linked by the [paper](https://arxiv.org/html/2510.20075v6).

Verified mechanism: tokenize the source, extract each token's conditional probability rank, then generate under another context by selecting those ranks. Reverse the process to recover the source. Equal length means token count, not original payload bytes. The paper discusses statistical differences, dependence on source predictability, and identical inference conditions; it explicitly does not supply a formal steganographic security model. Its prompt-search and deniability discussion is not an IND-CPA/CCA proof or a trapdoor construction.

The repository exposes an MIT-licensed notebook. Its README specifies NVIDIA Ada and `llama-cpp-python==0.3.12` for reproducing the paper's exact stegotexts. The repository and README were inspected; the browser did not expose the notebook's source cells. Source-level implementation audit and execution are therefore Stage 1 work, not completed verification. [Official implementation](https://github.com/noranta4/calgacus).

A search surfaced **CARTS: Contextual Autoregressive Rank Transcoding Steganography for Full-Capacity Keyed Text Encoding**, Wissam Ghantous and Alexander V. Mantzaris, [arXiv:2609.10744](https://arxiv.org/abs/2609.10744). Only the indexed abstract was accessible in this session. It describes rank-coordinate bijections, deterministic correctness, and key-related questions. Its full manuscript is needed before treating any rank-space argument here as novel.

Alex's existing code/results have not been audited. A prior repository pointer, `mantzaris/LlmStenoExplore`, is a retrieval lead, not proof that it is the correct current implementation. Request the intended repository, branch/commit, current manuscripts, and result manifests.

## 4. The three different technical ambitions

| Direction | Meaning and feasibility | Assumptions and validation burden | Novelty assessment |
|---|---|---|---|
| A. Encrypt then embed | Encrypt with a conventional public-key/hybrid scheme; encode its ciphertext as text. Feasible in the available time. | Confidentiality relies on the cryptographic scheme and implementation. Concealment needs a separate channel argument and evaluation. Serialization and extraction must be included. | Integration alone is insufficient; composition failures, a meaningful protocol improvement, or a new validated measurement result could contribute. |
| B. Public-key steganography | Anyone with public parameters can create a stegotext; the receiver's private key is required to recover the protected message. | Specify a channel and an indistinguishability game. No pre-shared secret may be silently required by the public sender. Address ciphertext representation, sampling, termination, and adversarial knowledge. | This area already has formal constructions. A can implement B's syntax, but not automatically its security definition. |
| C. LLM-dependent encryption primitive | The LLM supplies a new hardness assumption or public/private trapdoor. | Requires actual key generation, public encryption, private decryption, correctness, a parameterized hardness assumption, reductions or serious cryptanalysis, and attacks beyond prompt guessing. | Not defensible on this schedule. LLM complexity, hidden prompts, and failed attacks do not establish a trapdoor. |

A and B are not mutually exclusive implementation labels. Their important distinction is the claimed security contract. Public extraction of ciphertext can coexist with private plaintext recovery; it becomes a concealment problem if the extracted values have efficiently recognizable structure.

A secret natural-language prompt is not a cryptographic private key. If all senders must know it, the system has pre-shared-secret requirements and is not the intended public-sender system. A KEM-derived secret prompt would require a bootstrap channel to convey the encapsulation. Publishing that encapsulation without hiding it would defeat the concealment claim; embedding it introduces a separate construction problem.

## 5. Precise contribution and research questions

Provisional contribution statement:

> We characterize and measure how public extraction and ciphertext representation affect the concealment of hybrid-encrypted messages carried by rank-transcoding LLM steganography, while separating inherited cryptographic confidentiality from channel security and text-transport correctness. We compare these compositions with public distribution-aware coding and a stronger keyed reference under explicitly different setup assumptions.

This is a target statement, not an achieved result or a priority claim.

Research questions and registered primary measurements:

1. **RQ1: Does public inversion reveal a recognizable serialization even when surface text appears plausible?** Compare inverse-format distinguishers against model-likelihood and surface-text classifiers. Primary quantity: paired change in held-out AUROC; also report the fixed format test's TPR and FPR.
2. **RQ2: Which part of the pipeline creates the discrepancy?** Separate source predictability, binary-to-text representation, fixed metadata, cryptographic envelope structure, stopping policy, and prompt knowledge. Use uniform random bytes as a diagnostic control, not as a substitute for actual ciphertext.
3. **RQ3: What end-to-end utility is achieved?** Measure exact UTF-8 transport recovery, failures, payload bytes per carrier token, latency, VRAM, and local GPU hours across payload lengths and keys.
4. **RQ4: Which assumptions change the answer?** Compare public extraction with a keyed generative reference. Report its extra secret setup explicitly. Evaluate local process restart, backend drift, and limited text modification separately.

Hypotheses: public extraction will provide a useful detection signal for the Base64/hex rank-transcoding profiles; confidentiality will survive passive observation despite that signal; distribution-aware coding will improve some detectability/capacity tradeoffs but may require assumptions that cannot be supplied by a public-key wrapper alone. All are untested in this project.

### Analytical deliverables

1. **Conditional public-format distinguisher.** Let `Embed` and public `Extract` be a specified profile, and let `Valid` test its recoverable public format, without a decryption key. Let delta be the probability that a genuine transmission does not extract to a valid format, and let alpha be the probability that ordinary covertext does. Then the test `Valid(Extract(text))` has TPR at least `1-delta`, FPR `alpha`, and distinguishing gap at least `1-delta-alpha`. Measure alpha on held-out covers. Do not replace it with an unjustified independence estimate. This elementary observation is an analysis tool; its application and empirical importance must supply novelty.
2. **Rank-space identity.** For fixed token length n, a full vocabulary, deterministic total ordering, and invertible rank maps `R_source` and `R_cover`, define `T = inverse(R_cover) composed with R_source`. For source distribution P and cover distribution Q, both TV and KL discrepancy are preserved when both distributions are expressed through the same bijective coordinates. In particular, `KL(T#P || Q) = KL(R_source#P || R_cover#Q)`. This explains why rank preservation does not imply probability preservation. Treat this as a standard change-of-variables fact, and check whether CARTS already supplies the relevant specialization.
3. **Confidentiality composition boundary.** In a passive, equal-public-length setting, efficient public processing of a secure encryption output cannot create a plaintext distinguisher absent plaintext-dependent side channels. Specify all encoder randomness and abort behavior. This does not prove concealment. A stegotext decryption oracle also introduces equivalent-encoding and replay issues, so do not claim chosen-covertext security from the inner encryption's guarantees.

The source and cover distributions, framing, tokenization, and termination are part of these statements. None establishes concealment relative to arbitrary human communication.

## 6. Proposed protocol and security scope

Use an audited implementation of RFC 9180 HPKE rather than implementing cryptographic primitives. Provisional suite: DHKEM(X25519, HKDF-SHA256), HKDF-SHA256, ChaCha20-Poly1305; base mode for public senders. Verify published test vectors. [RFC 9180](https://www.rfc-editor.org/rfc/rfc9180.html).

Proposed one-message flow:

1. Receiver generates a cryptographic key pair locally. Sender obtains an authenticated recipient public key; public-key distribution is an explicit external assumption.
2. Publish a fixed profile containing model and tokenizer hashes, inference/backend settings, source and cover contexts, serialization, token ordering, maximum tokens, and framing rules. Prompt secrecy contributes nothing in the main public-sender profile.
3. Construct an inner record with a 16-byte random message identifier, a 4-byte payload length, the payload, and optional padding to a declared bucket. Place these application fields inside encryption. Buckets and profile selection are public metadata.
4. HPKE encrypt with fresh encapsulation randomness. Bind protocol version/profile/context identifiers through `info` and/or associated data using an unambiguous encoding. Only public information goes in these fields.
5. Serialize the full encapsulation-plus-ciphertext. Main Calgacus baseline uses canonical Base64 without a deliberately conspicuous magic header. Hex and external-header variants are ablations. Never map arbitrary bytes directly to UTF-8 by lossy conversion.
6. Encode with the chosen codec. Transmit the actual UTF-8 text. Token IDs and traces are diagnostic artifacts, not hidden communication side channels.
7. Receiver retokenizes that text, extracts the complete envelope, and calls HPKE open. Deliver plaintext only after successful authentication and length checks. Apply a replay cache to authenticated message identifiers; duplicates are not new deliveries.

For the chosen suite, the cryptographic envelope adds 32 bytes of encapsulation and a 16-byte authentication tag. The proposed inner record adds 20 bytes, giving `envelope_bytes = payload_bytes + 68 + padding_bytes`. Base64 requires `4*ceil(envelope_bytes/3)` characters before LLM tokenization. The HPKE nonce is derived internally for this one-shot use; do not add an invented transmitted nonce. For 32, 128, and 512 payload bytes without padding, envelopes are 100, 196, and 580 bytes, represented by 136, 264, and 776 Base64 characters. These are arithmetic design quantities, not measured token capacities.

Public distribution-aware comparison: replace Base64 plus rank transcoding with a documented arithmetic/range-coding bit interface to the same HPKE envelope. This is a comparison profile, not automatically a secure repair. Secure encryption does not imply that every serialized ciphertext bit is uniformly distributed, and finite precision, termination, and public parsing can still leak.

Keyed reference: a published distribution-preserving method such as RRC, with all shared-secret assumptions respected. Keep the steganographic secret independent of the HPKE receiver key. A fixed example seed is not a cryptographic key. Inspect whether the implementation uses a cryptographic generator and manages fresh per-message randomness; an adaptation must be labelled separately from the original baseline.

| Property | Main claim and supporting evidence |
|---|---|
| Confidentiality | Inherited from the selected cryptographic profile under its assumptions, plus a stated passive composition argument. No new LLM hardness claim. |
| Detectability | Empirical result relative to named cover channels and observer knowledge. A conditional analytical distinguisher is possible. No conclusion of formal security from detector failure. |
| Recovery | Conditional token-level correctness plus measured exact recovery after actual text serialization. Failures remain in denominators. |
| Integrity | Authentication rejects corrupted ciphertext under the cryptographic assumptions. Never release unauthenticated plaintext. |
| Sender authentication | Absent in base mode: anyone can encrypt to the receiver. A valid replacement from another sender is not an AEAD forgery. Optional HPKE authenticated mode or an encrypted signature changes the setup and overhead. |
| Replay | Handled by application state, not by one-shot encryption alone. |
| Text robustness | No default promise of survival through edits or paraphrases. Measure changes, decode outcomes, and rejection separately. |
| Forward secrecy, deniability, recipient anonymity, traffic hiding | Not claimed. Static recipient compromise, timing, message lengths/buckets, and network endpoints remain outside the main guarantees. |

### Actors and knowledge

- Sender: knows the recipient public key and all public profile information; has fresh local randomness; has no receiver secret key.
- Receiver: knows the private key and profile; can run the identical local inference implementation; maintains replay state if enabled.
- Observer O0: sees UTF-8 text and overt metadata; no target-model logits. Can train surface classifiers on separately generated public training data.
- Observer O1: additionally knows the model, tokenizer, algorithm, serialization, public key, and cover-context distribution, but not the per-message context. This is only a weaker diagnostic observer when exact context is actually public.
- Observer O2: knows the exact public context and all public parameters; can execute embedding and extraction and generate chosen-message training examples. This is the primary observer for public-sender claims.
- Active attacker: can insert, delete, replace, normalize, replay, or reorder text and can create fresh valid public-key ciphertexts. It has no private keys. An isolated test receiver can expose acceptance/rejection for evaluation; no claim of security against a general decoding oracle follows.

All weights, tokenizer, prompts, algorithms, profiles, public keys, and public nonces are public in the principal setting. Receiver private keys and ephemeral encryption randomness are secret. The keyed comparator adds a pre-shared steganographic key and must be displayed as a different setup.

## 7. Focused related-work and novelty comparison

This is a focused review, not an exhaustive priority search. The completed-paper novelty gate must additionally search each specific proposed result and inspect the user's overlapping manuscripts.

| Closest work | Construction/assumptions and reported claim | What this project could add | Merely incremental if... |
|---|---|---|---|
| [von Ahn and Hopper, Public Key Steganography](https://eprint.iacr.org/2003/233) | Formal public-key steganographic definitions and constructions under cryptographic assumptions and channel access; also studies decoding-oracle security. | Instantiate an explicit deployment question for an LLM rank codec and identify where its assumptions fail. | We claim public-key steganography or encrypt-then-embed itself as new. |
| [Berndt and Liskiewicz, EUROCRYPT 2018](https://arxiv.org/abs/1801.08154) | Chosen-covertext security for memoryless channels and a limitation on universality in their channel model. | Clearly bounded active-attacker tests and attention to a stateful autoregressive channel. | We extrapolate a passive experiment or AEAD rejection into chosen-covertext security. |
| [Ziegler, Deng and Rush, EMNLP 2019](https://aclanthology.org/D19-1115/) | Neural arithmetic-coding steganography; approximately matching a model's distribution; uniform-bit message setup and human evaluations. [Official code](https://github.com/harvardnlp/NeuralSteganography). | Actual full cryptographic envelopes, public inverse-format tests, transport failures and overhead under one common harness. | We only embed random or encrypted bits and count recovered messages. |
| [Schroeder de Witt et al., ICLR 2023](https://arxiv.org/html/2210.14889v4) | Couplings preserve prescribed marginals; minimum-entropy coupling targets throughput; cover distribution is assumed known. [Official code](https://github.com/schroederdewitt/perfectly-secure-steganography). | Test deployment conditions that differ from those idealized distribution assumptions. | We rebrand coupling or claim generic formal concealment from a few detectors. |
| [Liao et al., USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/liao) | Framework for provably secure schemes using shared white-box samplers; includes Discop(base). | An explicit account of which setup assumptions a public-sender composition can satisfy. | We offer only another probability-aware encoder without a distinct result. |
| [Bai et al., Shimmer, USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/bai-minhao) | Residual-entropy collection with capacity/security claims under its formal setup. | Measure full-message utility and assumptions instead of comparing gross bitrate alone. | We claim high capacity without accounting for crypto, framing, failure and setup overhead. |
| [Yan and Murawaki, 2026](https://arxiv.org/html/2604.08052v2) | Rotation range coding with a shared seed/key and fresh offsets; distributional guarantees under its model. [Official code](https://github.com/ryehr/RRC_steganography). | Separate the benefits of a private sampling key from public-key content encryption. | We publish the seed and incorrectly retain the original security guarantee. |
| [Norelli and Bronstein, Calgacus](https://arxiv.org/abs/2510.20075) | Rank transcoding; inspect its source and probability assumptions as described above. | Public-sender composition, structural extraction tests, controlled protocol accounting and transport evidence. | We only repeat the paper's high-entropy or rank/probability mismatch observations. |
| [Ghantous and Mantzaris, CARTS](https://arxiv.org/abs/2609.10744) | Accessible abstract describes correctness, rank-space bijections and key-related analyses; full manuscript not inspected. | Potentially the public-key-envelope and public-observer composition question, subject to audit. | The argument, attacks, datasets or experimental contribution are already in CARTS or another submission. |

Meteor, CCS 2021, is also relevant: [publisher DOI](https://doi.org/10.1145/3460120.3484550). Its full primary text was not accessible in this session. Reading its exact claims and checking its implementation are explicit Stage 1 literature tasks; do not reconstruct a theorem from secondary summaries.

Before passing novelty review, create a claim-by-claim overlap table for Calgacus, CARTS, RankCloak, the cross-modal project, and every closely related submitted manuscript provided by Alex. Distinguish reused software from new scientific claims and label any reused data. No conclusion of acceptable overlap has yet been reached.

## 8. Experiment matrix on the local GPU

Provisional hardware: one local NVIDIA GPU with 24 GB VRAM. Use one frozen 7B/8B checkpoint, preferably the exact compatible Calgacus model once inspected. An 8B model has roughly 16 GB of 16-bit weights before caches and runtime allocations; BF16 operation at the intended context length is not guaranteed to fit. A pinned quantized profile is acceptable, but becomes part of the evaluated protocol. Do not load two large models simultaneously. On 12-16 GB, use a compatible quantized profile or a smaller 3B/4B model and narrow claims. No fine-tuning is essential.

Core profiles:

| ID | Profile | Purpose |
|---|---|---|
| C0 | Ordinary sampling from the same model under the same cover contexts | Primary cover distribution; include native-length and matched-length analyses |
| C1 | Unmodified Calgacus with natural-language payloads | Fidelity and unencrypted rank-transcoding baseline; not a confidentiality comparator |
| C2 | HPKE envelope, canonical Base64, public-context Calgacus | Straightforward encryption-plus-embedding baseline; no artificial magic header |
| C3 | Same HPKE envelope with a public arithmetic/range bit codec | Distribution-aware public comparison; no inherited uniform-bit security claim |
| C4 | Same envelope with a vetted modern keyed reference, provisionally RRC | Stronger comparison with an explicitly additional pre-shared secret |

For C1, use natural-language payload slices at the same payload-byte targets where possible, respecting UTF-8 boundaries and logging actual length; if exact target length requires padding, record and analyze it. Also report matched source-token comparisons so the plaintext/crypto expansion is not obscured.

Provisional full core: 3 payload sizes (32, 128, 512 bytes) x 2 context domains x 80 independent units x 4 steganographic profiles = **1,920 stegotexts**. Generate up to **1,920 matched ordinary controls**. Additional natural-length controls can reuse a prespecified independently sampled subset rather than adding an unrestricted generation campaign.

An independent unit consists of a source document/context, message, and receiver key pair. Pair the same unit across profiles; create 480 independently generated receiver key pairs for this matrix. Use fresh encapsulation randomness per encryption. Do not inflate the independence count by treating all profiles for one unit as independent observations.

Split each size/domain cell into 32 detector-training, 16 validation, and 32 final-test units, for 192 held-out units per profile pooled across the six cells. Split source documents/topic clusters, context templates, messages, and key pairs before any codec tuning. Where a document provides both payload and context candidates, keep its entire family in one split. Report per-cell intervals as exploratory; this sample size is not adequate for strong very-low-FPR claims.

| Priority and task | Planned scale | Planning GPU hours | Stop or acceptance rule |
|---|---|---:|---|
| P0: foundations | Source audit, toy-model/CPU tests, at most 72 tiny GPU encode/decode or replay cases | <=2 | Stop at cap; no benchmark sweep; record failures and first divergence |
| P0: pilot and preregistration | <=120 development-only transmissions spanning size/codec profiles | 2-4 | Freeze viable profiles, sizes, budget and split plan before final data generation |
| P1: core generation | 1,920 stegotexts and up to 1,920 controls | 15-35 | Budget governor; all attempted cases logged; no selective retry or filtering |
| P1: recovery and public inversion | Actual text decoding and inverse-format detector on stego and controls | 10-25 | Count every capacity/serialization/replay failure; no token-ID-only success claims |
| P1: detection and statistics | Likelihood features plus CPU classifiers; optional small surrogate scored sequentially | 5-10 | Select features/thresholds on train/validation; evaluate the final test once |
| P1: focused stress/ablations | Approximately 200 selected units/variants; CPU crypto cases can be larger | 2-4 | Prespecified perturbations; valid stranger ciphertext distinguished from corruption |
| P2: second model or larger held-out sample | Only after core claims are supported | +10-30 each | Optional and requires a revised local compute allocation |

These estimates are not additive precision measurements. Reserve roughly **50-100 local GPU hours** for a complete core study including reruns and scoring. Propose an **80-hour local GPU ceiling**, pending Alex's budget. If the pilot forecast exceeds it, shrink the design before opening final-test data. A reduced study with 32/128-byte messages, one context domain, and 80 units per cell produces 640 stegotexts plus controls, with a rough **20-35-hour** budget and correspondingly narrower claims.

Forecast from measured local operations, not model-card throughput. Record separate encode/decode/public-inversion/scoring rates. Estimate total work as the sum of operation-specific counts divided by measured rates, plus at least 25% contingency. CPU rank sorting, model startup, and poor batching can dominate; a rate from ordinary text generation is not sufficient. Long 512-byte messages can require many carrier tokens; set a provisional 4,096-token cap and count exhaustion as failure.

Cloud compute cost is zero under the plan. Electricity is a sensitivity calculation: `local GPU hours * measured system kW * local electricity price`. For illustration only, 80 hours at a hypothetical 0.4 kW system draw is 32 kWh. Do not treat either the draw or tariff as measured.

### Essential measurements and ablations

- Exact recovered bytes, token-stream agreement, text round-trip agreement, authenticated recovery, decode failures, token-cap failures, and timeouts. Report intention-to-send success as well as conditional success for produced carriers.
- Plaintext bytes, ciphertext bytes, Base64/hex characters, source tokens, carrier tokens, bits embedded per carrier token, useful plaintext bytes per carrier token, and byte expansion. Useful throughput includes overhead and failed attempts.
- Encode/decode latency distributions (median and p95), cold-start versus warm timings, GPU active and allocated wall time, peak VRAM, and CPU time.
- O0 surface classifier: character n-grams plus logistic regression. O1/O2: normalized log-likelihood, conditional-rank and entropy features. O2 additionally runs public extraction and tests alphabet/format/length constraints. Do not let any observer validate an AEAD tag without the required key.
- Naive profile versus hex; with/without unnecessary public headers; real ciphertext versus same-length random bytes; public exact prompt versus unknown prompt; padded versus unpadded records; stop-on-completion versus a prespecified length-budget policy.
- Length-only detector as a baseline. Report both matched-length linguistic detection and full operational detection including length. Neither substitutes for the other.
- Native Calgacus plaintext versus encrypted serialization at matched original bytes and, separately, matched source tokens. This avoids crediting an encoder for hiding its expansion in the input.
- A repeated-recipient stress subset uses independent ephemeral randomness across multiple messages. Analyze this separately from the unique-key core.
- Byte modifications, one-word deletion/insertion, punctuation change, whitespace collapse, Unicode normalization, truncation, and replay. Some transformations are identity operations on some samples; count actual changes separately. Success is either correct authenticated delivery or rejection as appropriate, never plausible garbage.
- Wrong receiver key, wrong public context, wrong tokenizer hash, changed quantization, and a clean process restart. Incompatible profiles should be rejected when detectable from the agreed configuration. Cross-backend replay is a portability stress test, not the primary correctness contract.

Do not add paraphrase-resilient coding, error-correcting codes, multi-recipient protocols, post-quantum KEMs, a second modality, or detector fine-tuning to the core. They answer different questions and can consume the schedule. Adding signatures or a post-quantum KEM also changes the capacity accounting materially.

### Data, confidence intervals, and leakage controls

Use real public text prefixes in two topic domains, such as technical explanations and general informational prose, from a frozen, licensed Wikipedia-derived snapshot. Use source article identifiers and revision metadata, not private correspondence. Add a small set of researcher-authored scheduling/research-note examples as a realistic communication stress set; label them synthetic. Wikipedia continuation is a modelled writing channel, not evidence of indistinguishability from ordinary private email. Inspect the exact snapshot's license and attribution requirements before redistribution. [Dataset provenance and licensing](https://huggingface.co/datasets/wikimedia/wikipedia).

For performance intervals, use exact binomial or Wilson intervals for independent Bernoulli trials and paired cluster bootstrap for cross-profile differences, retaining each document/key unit together. With zero failures in n independent cases, the one-sided 95% failure upper bound is `1 - 0.05^(1/n)` (approximately `3/n`). For example, 0/192 failures only bounds the underlying rate by about 1.55%, and says nothing about an untested backend or channel.

Report ROC-AUC, balanced accuracy at a validation-fixed threshold, and TPR at a preselected attainable FPR. At this scale 5% FPR is more interpretable than 0.1% or 1%; include uncertainty and counts. Never describe AUC near 0.5 as a proof. If using an operational equivalence margin, choose it before testing and require the whole confidence interval to lie inside it.

Predeclare the principal comparison as the additional value of public inverse-format detection over the best validation-selected surface/likelihood detector on C2. Secondary comparisons are descriptive or multiplicity-adjusted. Check both detection directions using training data only. Include domain-transfer testing, such as training on one domain and evaluating the other, only as a separately registered analysis.

Use distinct CSPRNG streams for cryptographic randomness and experiment sampling. Reproducible deterministic key material is permitted only as explicitly insecure test-vector material. Never reuse experimental seeds/keys in deployed communication. Detectors receive only their stated observations, not filenames, label-correlated formatting, log fields, plaintexts, or private keys. Report known or uncertain foundation-model training overlap; a recent dataset snapshot does not imply that its underlying text is new.

## 9. Paper structure and planned evidence

Plan for 12 formatted pages for the regular-paper target while also satisfying the submission character range. There is no guarantee of full-paper classification; maintain an 8-page compression plan. References, figures, and appendices count toward the proceedings page budget.

| Content | Regular target pages | Position fallback pages |
|---|---:|---:|
| Abstract, problem and contribution | 1.0 | 1.0 |
| Related work and novelty boundary | 1.25 | 1.25 |
| Threat model and security definitions | 1.0 | 1.0 |
| Composition analysis and protocol | 2.25 | 1.5 |
| Experimental design / bounded evidence | 1.25 | 0.75 |
| Results / research agenda and falsifiable milestones | 2.25 | 1.0 |
| Limitations and conclusion | 1.0 | 0.5 |
| References | 2.0 | 1.0 |
| Total | 12.0 | 8.0 |

Adjust the layout after an actual template render. Do not hide essential evidence in an external appendix whose review status is unknown. The fallback advances an argued position and testable agenda; it must not present planned experiments as results.

| Planned exhibit | Evidence required before drafting claims |
|---|---|
| Figure 1: protocol, public/secret boundaries and observer access | Final specification and reviewed threat model; no measured result required |
| Figure 2: public-inversion versus surface detection | Held-out scores, actual negative covers, train-selected thresholds and paired confidence intervals |
| Figure 3: useful capacity, recovery and latency tradeoff | Complete attempt ledger, full overhead accounting and actual timing logs |
| Optional Figure 4: failure location under text/backend changes | First-divergence traces and prespecified perturbation outcomes |
| Table 1: closest-work and setup comparison | Primary-paper audit and user-manuscript overlap matrix |
| Table 2: protocol overhead and success by size | Envelope definitions and verified round trips, with all failures included |
| Table 3: observer knowledge and ablations | Locked dataset split and cross-profile evaluation outputs |
| Table 4: local reproducibility profile and compute | Model/tokenizer/backend hashes, GPU details, precision/cache settings and cumulative usage |

Select at most three main figures and three compact tables if needed for space. Figures are generated from machine-readable results; no illustrative numerical result is to be inserted as an experiment outcome.

## 10. Schedule and decision points

| Dates in 2026 | Work and exit condition |
|---|---|
| September 18-20 | Confirm exact repo/hardware, collect related manuscripts, verify remote arrangement, complete claim-overlap audit. Stop the proposed novelty claim if duplicated. |
| September 21-24 | Bounded Stage 1 below. Inspect source audit, correctness traces, HPKE vectors, transport behavior and local timing report. |
| September 25-28 | Small pilot; audit a modern baseline; specify the conditional composition argument and detector; lock corpus, splits, profiles and forecast. |
| September 29-October 5 | Core local-GPU run in resumable batches; ongoing data-integrity checks that do not inspect final-test comparisons. |
| October 6-8 | Frozen test evaluation, planned ablations, uncertainty estimates and claim review. |
| October 9 | Formal regular-versus-position decision. Keep regular if there is a distinct result, adequate controls and interpretable evidence, even if negative. Switch if evidence is incomplete but the argument is substantive. Otherwise stop. |
| October 10-14 | Draft selected paper type from verified evidence; references and figures complete; no open-ended experiments. |
| October 15-18 | Adversarial self-review, overlap review, security-claim audit and narrowly justified repairs. |
| October 19-21 | Freeze results; render template; verify page/character limits, anonymity, citations and artifact access. Submit internally by October 21. |
| October 22 | Deadline buffer and PRIMORIS receipt verification; official cutoff is AoE. |

Position-paper switch criteria: no stable text-transport prototype, missing independent comparator, unresolved overlap, substantial final-test leakage, or insufficient sample coverage to substantiate the proposed regular-paper claim. Detector performance need not favor the proposed pipeline. Null findings with narrow enough uncertainty and a novel conclusion may still justify a regular paper.

## 11. Bounded first implementation stage

This stage is specified for a later local Codex session. It is not being executed by this planning task.

Objective: establish audited, reproducible foundations and a small reviewable evidence bundle. Do not run the full matrix, train a large detector, fine-tune a model, create a new cryptographic primitive, or write a finished manuscript.

Bounds: two focused working days; **at most 2 cumulative local GPU hours**; at most 25,000 generated tokens and 72 planned smoke/replay cases, whichever limit is reached first. All inference must use the confirmed local GPU. Stop at the cap with a report. No cloud fallback or paid API. CPU testing and document/source inspection should not consume GPU allocations.

### Deliverables and repository organization

| Path | Purpose |
|---|---|
| `README.md` | Task, setup, public/secret boundary, local-only commands and current limitations |
| `pyproject.toml` and dependency lock | Reproducible environment with pinned versions |
| `docs/source_audit.md` | Calgacus paper/version and official code commit; licenses; code-to-paper mapping; unresolved implementation details |
| `docs/novelty_matrix.md` | Claim-level comparison with user manuscripts and closest work |
| `docs/threat_model.md` | Actors, public/secret fields, channel definition and excluded guarantees |
| `docs/protocol.md` | Wire format, HPKE suite, context binding, errors, padding and tokenization contract |
| `docs/evaluation_plan.md` | Proposed splits, primary endpoints, ablations, failures and budget; pilot data explicitly excluded |
| `configs/` | Separate frozen crypto, local model, corpus and smoke-run profiles |
| `src/llm_stego_public_key/cryptography/` | Adapter to established HPKE implementation; no hand-written primitives |
| `src/llm_stego_public_key/codecs/` | Calgacus adapter, explicit byte serialization and codec interfaces |
| `src/llm_stego_public_key/transport/` | UTF-8 boundary, canonicalization policy and parsing limits |
| `src/llm_stego_public_key/evaluation/` | Format test, metric definitions, run ledger and budget governor |
| `tests/` | Published crypto vectors, malformed frames, toy-rank correctness, text round trips and failure handling |
| `scripts/` | Local hardware inventory, bounded smoke run and evidence-report generation |
| `manifests/` | Source, model, tokenizer, dataset and environment provenance |
| `artifacts/stage1/` | Machine-readable cases, summary, traces, CPU test report and local GPU usage |
| `paper/` | Outline and references only at this stage |

Keep changes small and understandable. Maintain the original upstream method as a reference. Do not silently fix or replace its decoding semantics and still call it unmodified Calgacus. If the same model must run through different backends for a comparator, account for backend as a confound rather than as a method improvement.

### Required foundation work

1. Read repository instructions, inspect the supplied code and results, and record what can actually be reused. Record the existing git state before changes and preserve unrelated work.
2. Obtain and audit the official Calgacus notebook source, including token ranks, ties, special tokens, prompts, cache reset, detokenization and stopping. Record the exact commit. Read the full relevant CARTS and other manuscripts before finalizing novelty. If unavailable, label the overlap gate unresolved.
3. Capture the real local GPU model/VRAM, driver, CUDA/runtime, OS, Python, CPU/RAM and free disk. Check whether the original reproduction backend fits. Do not infer local hardware from a previous cloud session.
4. Implement a small HPKE wrapper around an existing library, validate RFC vectors, and test framing and rejection on CPU. Test empty/max/invalid lengths, malformed Base64, truncation, wrong associated data, wrong receiver key and record duplication.
5. Implement an explicit token-level Calgacus interface with an independent toy-model test. Test stable tie ordering and the requirement that serialized text retokenizes to the intended sequence. Never hide a retokenization failure behind token-ID transport.
6. Create a local end-to-end smoke harness: up to 12 original-method examples; up to 48 encrypted examples covering two lengths, four cover contexts and six receiver keys; and up to 12 clean-process replays. Cap each message and total work. Use only harmless synthetic/research text.
7. Implement the public inverse-format detector on those tiny cases and matched toy/ordinary controls. Its outcome is diagnostic only. Do not estimate publication-grade detectability from the smoke sample.
8. Define the modern-comparator adapter and audit its setup/randomness. It need not run a full experiment in Stage 1. Provide an honest feasibility estimate and exact unmet requirements.
9. Produce a machine-generated Stage 1 report and stop. Later experiments need the evidence review below and an agreed local budget.

### Acceptance criteria

- Published HPKE vectors pass; selected serialization cases recover exact bytes; negative CPU cases reject without releasing unauthenticated plaintext.
- Toy rank tests pass with an independently specified inverse. The real transport path starts with UTF-8 text at the receiver and uses no hidden token-ID side channel.
- For the proposed supported profile, all admitted smoke cases either recover exactly or have a documented failure with a first-divergence trace. Any unexplained failure blocks scale-up. If exclusions are required, justify them before preregistration and retain the excluded cases in the audit.
- A clean receiver process can replay admitted transcripts under the recorded environment. No requirement of exact cross-GPU/back-end identity is claimed.
- Logs separate successful extraction, authenticated delivery, capacity exhaustion, tokenization drift, numerical drift and malformed input. Failed attempts are never erased by retries.
- The budget governor stops at the stated limits. The report proves which GPU performed inference and accounts for total local usage.
- Novelty and comparator-readiness gates are explicitly passed, failed or unresolved. Passing crypto/round-trip tests alone does not authorize the whole research program.

### Reproducibility records

Record source commits and any dirty diff, dependencies/lock, model weight hashes, tokenizer files and special-token settings, quantization, precision, backend commit/build flags, GPU/driver/CUDA, deterministic flags, rank tie-break rule, batch/prefill/cache settings, exact prompt bytes and token IDs, payload and ciphertext lengths/hashes, transport text and tokens, experiment seeds, test-only crypto keys or clearly labelled deterministic vectors, encode/decode first-divergence position, and measured timings/VRAM.

Use a schema-versioned JSONL record per attempt with immutable attempt IDs. Store machine-readable summaries and the commands that regenerate them. Test keys may accompany a reproducibility bundle, but must be visibly labelled insecure and remain separate from any real keys. Do not log unrelated credentials.

### Evidence to inspect before later experiments

Inspect the source audit and code diff; full manuscript overlap matrix; cryptographic vector results; at least one ordinary and one encrypted complete encode/transport/decode trace; all failed cases; process-restart replay; actual local GPU/VRAM and operation-specific timings; provenance manifests; corpus-license and split manifests; detector input audit; modern-comparator assumptions; and a forecast with an enforceable cumulative GPU ceiling.

Proceed only when the supported profile is understandable and reproducible, the proposed claim is distinct, the baseline comparison is fair, and the projected local cost fits the agreed budget. No bulk run is authorized by the mere existence of this plan.

## 12. Materials still needed

1. The intended current repository URL or local path, branch/commit, and relevant result manifests. If `mantzaris/LlmStenoExplore` is outdated, supply its replacement. The original Calgacus reference has now been identified; provide a different reference only if another variant was intended.
2. The current CARTS manuscript and abstracts/manuscripts of RankCloak, the cross-modal work, and any closely related submitted papers, sufficient to audit exact overlap.
3. Local GPU model, VRAM, OS/runtime, maximum GPU hours, and available hours per day through October 22. Also identify any already-downloaded compatible model checkpoints.
4. Any existing written ICISSP confirmation that remote presentation is available for your circumstances; otherwise this remains a venue logistics item to resolve before a financial commitment.
