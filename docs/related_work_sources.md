# Stage 5: inspected primary sources

Reviewed on **2026-09-18**, for a contribution decision, not a comprehensive survey or independent reproduction of other authors' results. Source statements below are separated from this project's interpretation. Exact file hashes, inspected sections, availability and revisions are in [stage5_sources.json](../manifests/stage5_sources.json). Downloaded papers and unpublished manuscript contents are not copied into this repository.

The bounded search followed four overlap questions: who already supplies rank inversion; who already checks the actual text boundary; what public-key/keyed constructions assume; and whether framing/observer/conditioning arguments add anything beyond those results. Primary papers and their official code were used. Search snippets were discovery aids, not evidence of a claim or of absence of prior work. No priority claim follows from this search.

## Related manuscripts

### CARTS

**Wissam Ghantous and Alexander V. Mantzaris, _CARTS: Contextual Autoregressive Rank Transcoding Steganography for Full-Capacity Keyed Text Encoding_.** [arXiv:2609.10744v1](https://arxiv.org/abs/2609.10744v1), 9 September 2026; [PDF](https://arxiv.org/pdf/2609.10744v1), [TeX archive](https://arxiv.org/src/2609.10744v1). This is an available **public preprint**, not an author-confirmed latest submission. The archive contains `main.tex` and `sample-base.bib`; the relevant mathematical sections are inline, not external TeX includes. PDF SHA-256: `808abbdfb6ef288c337b20cea5069a6a235e3ac5e0687903be829aca918d1e98`.

Source: §3.1, Lemma 1/Theorem 1, and §3.2/Theorem 2 (PDF p. 3) establish conditional rank inversion and its two-context extension. §4.2, Proposition 1 (p. 4) gives rank-coordinate conjugacy. §4.1 explicitly separates its secret-context questions from distributional indistinguishability. Inspected the corresponding TeX statements/proofs, empirical setup/correctness and conclusion as well.

Interpretation: neither the inverse nor its induction argument is our contribution. Making contexts public changes the threat model; it does not refute CARTS' stated secret-context results.

### RankCloak

**_RankCloak Conceals the Surface Form of Synthetic Cryptographic Artifacts in Language Model Generated Text_.** Local draft `../llm-rankcloak/paperV3/scientific_reports/main3.tex`, repository revision `ce853d42d6ba64065cb63c6bdfc0d825c62734cd`; [fixed source reference](https://github.com/mantzaris/llm-rankcloak/blob/ce853d42d6ba64065cb63c6bdfc0d825c62734cd/paperV3/scientific_reports/main3.tex). Main SHA-256: `6bcbd20fda1fda549b19c48417b95c4a6924b33d7bb9d9c40b4daa35cf515dee`. Inspected main Methods, Results, Discussion/limitations and relevant `supplementary3.tex` notes S1, S8, S13, with bibliography. These manuscript files match the commit; unrelated cover-letter changes in that sibling checkout were neither used to infer status nor modified.

Source: Methods `sec:payload-method` already encodes artifact representations with bounded bases 8 and 16. `sec:replay-method` separates saved-token and rendered-text evidence. Supplement S1 describes singleton token filters and their limits; S8 gives conditional finite-code inversion and overhead; S13 explicitly separates completion-conditioned capacity from all-attempt recovery and budget failures. The main detector sections evaluate model-aware/text observers and transfer limitations.

Interpretation: our complete HPKE envelope, stricter receiver boundary and full-prefix filter are concrete engineering distinctions from those singleton-filter variants. They do not make artifact concealment, radix 16, rank pressure or recovery/detection tradeoffs new. ImageCalgacus narrows the remaining distinction further.

Status: **local draft**; neither `paperV3` nor repository activity proves submission, acceptance, or latest submitted version. Author confirmation and the exact submitted main/supplement are still required.

### Cross-modal / ImageCalgacus

**_Exact Bidirectional Steganographic Transport with Language and Pixel Autoregressive Models_.** Local draft `../ImageCalgacus/paper/icaart2027/main.tex`, revision `2bec65dbe5509623f6658d8a231ec93f6d579b4e`; [fixed source reference](https://github.com/mantzaris/ImageCalgacus/blob/2bec65dbe5509623f6658d8a231ec93f6d579b4e/paper/icaart2027/main.tex). Main SHA-256: `ecb8df30c06b19f5147a30c1fca54910965f025fed227cf2e5b36aa5379be253`.

Inspected main §§2–6, particularly §§3.1–3.4, §§4.3–4.4 and §§5.1–5.4. Read companion `supplement.tex` S1–S5 and its relevant source includes: preamble, transport diagram, recovery/detection/overhead tables and context-comparison table. Main scientific sections are inline; unrelated photograph sections and figure binaries were not independently audited. File-level inspected scopes are in the manifest.

Source: §3.2, Eq. `eq:consistent`, checks **the complete proposed carrier prefix** by detokenizing and retokenizing. §3.3 includes high-nibble-first fixed radix 16 over eligible tokens, beside gated and arithmetic adaptations. §§3.1/3.4 require saved UTF-8 or PNG and a fresh receiver with no sender diagnostics. §§4.3/4.4 define failure-inclusive useful rates and public model/context observers. Companion S4 compares singleton versus sequence filtering and expressly attributes stepwise verification to earlier work. S2 retains failed arithmetic text carriers in detection and recovery denominators.

Interpretation: this is the closest overlap with a proposed transport/evaluation systems paper. Our public-key sender setup differs from its shared AES-GCM packet key, and our clear four-byte length field differs from its packet contract. Neither change establishes a new transport principle. Its top-256 scan versus our top-128 scan is a profile parameter, not a novel admissibility method.

Status: **local draft**, not author-confirmed submitted/latest. The companion itself says supplementary submission status is unconfirmed. We have inspected reported evidence, not reproduced that project's experiments or verified its publication status.

## Published and public primary references

### Calgacus

Norelli and Bronstein, [_LLMs can hide text in other text of the same length_](https://arxiv.org/abs/2510.20075v6), arXiv:2510.20075v6, 16 January 2026. Read §3 recipe (p. 4), hash example and probability comparison (p. 5), low-entropy-choice/precision limitations and §3.1 security (pp. 6–7). It already distinguishes rank preservation from probability matching and discusses difficult high-entropy inputs.

The [official notebook at `116123d4…`](https://github.com/noranta4/calgacus/tree/116123d4b7a74b3d56d15623355f9acf32a87165) is retained under `vendor/calgacus/` with MIT license. Actual cell 10 rank/extraction functions were inspected, including BOS/space handling, `argsort`, cache reset, detokenization and stripping. The notebook's serialization/tie behavior differs from our documented adaptation. Neither our encrypted baseline nor rank16 is silently relabelled “unmodified Calgacus.”

### Tokenization consistency

Yan and Murawaki, [_Addressing Tokenization Inconsistency in Steganography and Watermarking Based on Large Language Models_](https://aclanthology.org/2025.emnlp-main.361/), EMNLP 2025, pp. 7076–7098. **Algorithm 1, p. 7079, and §3.1, p. 7080** check the complete proposed sequence and apply identical candidate verification at both endpoints. Read §§2–3. This directly precedes the canonical-prefix rule used here; it is not merely a paper about a vaguely similar tokenizer problem. Our strict UTF-8/bounded-scan policy is a specified adaptation, not a priority claim.

### Classical public-key steganography

von Ahn and Hopper, [_Public-Key Steganography_](https://eprint.iacr.org/2003/233), ePrint 2003/233 / EUROCRYPT 2004. The inspected 21-page [ePrint PDF](https://eprint.iacr.org/2003/233.pdf), §2 (p. 3), §6 Construction 1 (p. 8), §6.1 Construction 2/Lemma 1/Theorem 1 (p. 10), uses IND$-CPA encryption, a public extraction function and channel assumptions. Source: ciphertext extraction can be public while concealment follows under those assumptions. Interpretation: public inversion alone cannot establish detectability; a distinguishing predicate and cover probability are necessary. Direct PDF download returned HTTP 403; browser PDF text was accessible. No downloadable-file hash is fabricated.

Hopper, Langford and von Ahn, [_Provably Secure Steganography_](https://www.cs.cmu.edu/~biglou/PSS.pdf), **CMU-CS-02-149, 6 September 2002**, inspected author-hosted technical-report version. §§2.2–2.3 and §3 define channel-based computational secrecy, separate from content encryption and robustness. This supplies established evaluation distinctions, not an LLM-specific experimental prescription.

Berndt and Liśkiewicz, [_On the Gold Standard for Security of Universal Steganography_](https://arxiv.org/abs/1801.08154v1), arXiv:1801.08154v1, 24 January 2018. **§7 Theorem 10 (p. 19)** concerns SS-CCA under memoryless-channel and additional cryptographic assumptions; **§8 Theorem 12 (p. 23)** gives a non-look-ahead impossibility under specified channel/primitive assumptions. Read these statements and surrounding scope. Neither is a blanket theorem for our autoregressive text profile. No independent proof audit was performed.

### Arithmetic and keyed generative methods

Ziegler, Deng and Rush, [_Neural Linguistic Steganography_](https://aclanthology.org/D19-1115/), EMNLP-IJCNLP 2019, pp. 1210–1215. Read §§2–4.2, especially arithmetic generation from uniform bits (§3, pp. 1212–1213) and the model-versus-natural-language distribution distinction (§4.2). The [official code revision `14e98256…`](https://github.com/harvardnlp/NeuralSteganography/tree/14e982564aeaf9a33f7b4de440deda2184d17f12), `arithmetic.py`, has finite-precision/truncation rules and GPT-specific exclusions plus decoding heuristics. This is not a validated drop-in comparator for our strict text contract.

Kaptchuk, Jois, Green and Rubin, [_Meteor: Cryptographically Secure Steganography for Realistic Distributions_](https://www.cs.umd.edu/users/kaptchuk/publications/ccs21_meteor.pdf), CCS 2021, [DOI](https://doi.org/10.1145/3460120.3484550). Read §§3–6, PDF pp. 3–9: channel/observer model, classical public-key/hybrid discussion, and synchronized secret PRG masks. §5.1 explains why once-encrypted bits do not automatically make arithmetic generation distribution preserving. The [author-linked demo](https://gist.github.com/tusharjois/ec8603b711ff61e09167d8fef37c9b86/1bba7c76710abcaa71db59724328ad4d9c314e65) implements HMAC-based DRBG with key/nonce inputs; it was inspected, not executed. Interpretation: exposing its key or replacing it with a public seed changes its assumptions.

Yan and Murawaki, [_Efficient Provably Secure Linguistic Steganography via Range Coding_](https://arxiv.org/abs/2604.08052v2), arXiv:2604.08052v2, 13 April 2026. Read §§2.4–5.2: Algorithms 3/4 require synchronized keyed offsets; §5.1 Propositions 1/2 give the ideal distribution argument. The [official revision `dae32625…`](https://github.com/ryehr/RRC_steganography/tree/dae326259e4fca8bc4fcf460dafdbc0e88a0a71a) has `random.Random(args.key)` in `RRC_embed.py` and `Decimal(prng.random())` in `rrc_core.py`. This inspected CLI path does not itself implement a cryptographic PRG. That limits comparator readiness, not the validity of every version of the paper's ideal analysis.

Schroeder de Witt et al., [_Perfectly Secure Steganography Using Minimum Entropy Coupling_](https://arxiv.org/abs/2210.14889v4), ICLR 2023; inspected arXiv v4, 30 October 2023. Read §2 (pp. 2–3) and §3 (p. 4), Definition 3.1/Theorems 1–2. Its coupling formulation makes the specified marginals central; the setup includes a shared private key and uniformly distributed transformed messages. Interpretation: observer/distribution precision already has substantive theoretical treatment. Those assumptions cannot be transferred automatically to our public HPKE envelope.

### Cryptographic and venue boundaries

[RFC 9180](https://www.rfc-editor.org/rfc/rfc9180.html), February 2022, §§5, 9.1–9.2, 9.7 and 10: HPKE's suite/mode and wire-format responsibilities. Table 6 does not give sender authentication to Base mode. Application framing and concealment remain separate responsibilities; our LLM is not a new encryption primitive.

The [official ICISSP 2027 dates](https://icissp.scitevents.org/ImportantDates.aspx), checked 18 September 2026, list **22 October 2026 AoE** for position papers / second-stage regular papers, matching the intended deadline in the research plan. That is 34 calendar days away. The first regular-paper date is 29 September; it is not the plan's target. A direct HTML fetch failed, but the official page was accessible through the browser. Deadlines can change.

## Limits and unresolved materials

There is no confirmed latest-submitted version for CARTS, RankCloak or ImageCalgacus. Their available texts are sufficient to identify substantial overlap now; missing newer versions prevent clearance, not engineering comprehension. No claim is made that this bounded search finds every prior framing result. No other project's empirical counts are counted as this project's measurements.

The targeted citations above resolve the immediate overlap questions. A new formal claim would require a claim-specific citation/proof review, not another general bibliography. Current arithmetic/keyed interfaces remain contracts; no reference implementation or security proof was newly validated or executed in Stage 5.
