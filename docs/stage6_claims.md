# Stage 6 claim boundary

This document accompanies the measured results in [STAGE6_FRAMING_STUDY_REPORT.md](../STAGE6_FRAMING_STUDY_REPORT.md). It is an interpretation of one frozen exploratory study, not a security proof or a novelty clearance.

## What changes, and what does not

On 18 September 2026 the user authorized Stage 6 despite Stage 5's recommendation. The new question concerns complete-message residual recognition after removing the deliberately clear outer length header. Internal CARTS, RankCloak and ImageCalgacus manuscript reconciliation is not a prerequisite for this stage. The [historical Stage 5 assessment](../STAGE5_CONTRIBUTION_DECISION.md) remains unchanged. Submission-level allocation of contributions remains a later author decision.

L and F share the existing canonical-prefix rank16 selection function. F removes the external four-byte length, infers envelope length from the received even token count, and binds its own public profile through HPKE. It retains the authenticated inner payload length. This is conventional encrypt-then-embed using an established HPKE implementation, not a new encryption primitive. It proposes neither LLM-dependent cryptographic hardness nor a secret prompt.

The transport invariant is conditional: every emitted prefix has strict UTF-8 bytes whose canonical tokenization is precisely that prefix; both endpoints must reproduce the same model state, logits, tie ordering and admissible set. Finite candidate exhaustion remains possible. Removing eight header tokens does not improve that numerical reproducibility assumption or establish robustness to arbitrary edits.

F removes a known public constraint, but still reveals received message length, uses a constrained token alphabet, and transports a structured encapsulation followed by an encrypted body. Both boundary variants have independently authenticated profile bindings. Historical ciphertexts are not reused across these bindings.

## Claim-to-evidence contract

| Claim | Evidence allowed to support it | Interpretation limit |
|---|---|---|
| F supports actual-text authenticated recovery in this setting | Main attempt-level recovery and eight predetermined independent receiver slots; saved UTF-8, profile-bound encryption, no receiver diagnostics | Four public contexts, one model/backend, small payloads; qualifications and replays are not additional independent main transmissions |
| F removes L's designed six-zero prefix and saves eight tokens | Framing source and independently generated public predictions; measured carrier lengths | Expected engineering consequence, not the research contribution; not an attack on original Calgacus |
| Residual recognition depends on the declared cover generator | Complete-message public scores and fixed, matched A/B/C controls with all attempts retained | These generators are not human traffic, and uniform admissible generation is a diagnostic reference only |
| A public format test can accept data without authenticating it | Independent public extraction and necessary encapsulation-representation predicate | No private key, tag verification, sender authentication or proof of valid ciphertext |
| Some signal can remain beyond length and the clear header | Matched intended lengths; fixed suffix/body scores; separate byte-length diagnostic | Conditional descriptive comparisons, not universal detectability; no threshold fitting or post hoc sign reversal |
| Exact recovery can coexist with recognizable communication | Recovery results alongside public diagnostics on the same actual messages | Recovery, content confidentiality and concealment are different properties; none implies the others |
| Measured cost includes the receiver and observer | Conservative per-job charges, phase meters, loading/startup, sampled GPU memory, failed attempts | Sampling is a lower-resolution memory measurement; one backend is not a scalability benchmark |

## Recognizable encapsulation is not a cryptographic break

The observer's additional KEM predicate checks whether the first 32 publicly recovered bytes, interpreted little-endian, are less than `2**255-19`. [RFC 7748 §5](https://www.rfc-editor.org/rfc/rfc7748.html#section-5) specifies the generated u-coordinate representation; [RFC 9180 §4.1](https://www.rfc-editor.org/rfc/rfc9180.html#section-4.1) puts the serialized ephemeral public key in `enc`, with the X25519 convention in [§7.1.1](https://www.rfc-editor.org/rfc/rfc9180.html#section-7.1.1). The frozen pyhpke 0.6.5 code uses OS-generated X25519 keys and raw public-key serialization.

This is a necessary property of the frozen honest sender's encapsulation output. It is not full curve/key validation, authentication, or a claim that the receiver rejects every noncanonical X25519 input. The ideal uniform-byte acceptance probability is `(2**255-19)/2**256`, close to one half. That calculation alone does not establish the rate of successfully emitted admissible controls: completion conditioning and the specified random-generator model must be retained. An entire HPKE envelope is not justified as indistinguishable from uniform bytes merely by invoking content encryption.

A positive format or representation test never authenticates a message. Anyone knowing the public key can generate a new valid HPKE Base-mode ciphertext; that is not a tag forgery. No concealment, sender-authentication or edit-robustness claim is supported by these tests.

## Prior methods versus a possible empirical contribution

The existing [primary-source audit](related_work_sources.md) remains the attribution record. Calgacus already supplies rank transport and discusses high-entropy inputs; the audited local adapter is explicitly adapted. Yan and Murawaki's EMNLP 2025 Algorithm 1 and §3.1 precede whole-prefix tokenization checks. Public-key steganographic constructions and arithmetic/keyed generative work already make the channel distribution and cryptographic assumptions central. Meteor specifically cautions against transferring properties of encrypted bits to a complete generated distribution. Rank16, HPKE integration, full-prefix checking, inverse rank decoding and elementary header recognition are not claimed as new methods.

The potentially useful contribution is a carefully delimited *joint measurement*: after a fixed outer-header ablation, measure actual-message recovery, residual public recognition under three explicit full-message generators, and inclusive encode/receive/observer costs without using hidden receiver state or dropping failed attempts. Its scientific value depends on the measured contrasts and their consequences. It can remain an informative implementation case study without establishing a distinctive regular-paper result.

Four contexts cannot justify operational false-positive rates, human-cover realism, model generality or absence of stronger observers. The fixed public scores do not exhaust distinguishers. Below-chance AUCs retain their predeclared orientation; they are not silently flipped into favorable detection results. Complete separation or all-success resampling intervals are not population guarantees. A canonical-token likelihood is not automatically the likelihood of the transmitted UTF-8 string.

All prior cases remain development evidence. Stage 6 is a prospective frozen exploratory allocation, not retrospectively promoted final-test data. No substantial detector is trained. Existing arithmetic and keyed interfaces remain unqualified implementations for future comparison; a public seed cannot replace a secret key while preserving a keyed construction's security claim.

## Provisional paper organization and remaining evidence

1. **Task and observation model:** public-sender encrypted text transport, actual message boundaries, permitted observer knowledge, and the three cover generators.
2. **Existing mechanisms and the framing comparison:** attributed rank/admissibility transport, established HPKE, L versus F, protected inner length and numerical/text assumptions.
3. **Frozen study and attempt accounting:** new contexts/keys, paired inputs, preserved aborts, independent receivers, ledger and reproducibility.
4. **Results:** recovery/useful rate, prefix versus complete-message recognition, encapsulation versus encrypted-body signals, generator-dependent conclusions and inclusive costs.
5. **Interpretation and limits:** which findings are expected, what measured consequence remains, and what is not established about concealment or scientific distinctness.

A final submission would need a consequential claim that survives comparison with published tokenization-consistency and distribution-matching work, plus evaluation support appropriate to that claim. One model, four selected contexts and simple public scores do not establish transfer or practical traffic recognition. The existing arithmetic/keyed interfaces must not appear as validated baselines. If a distribution-matching comparator becomes essential to the claim, its real termination, text-serialization and shared-secret assumptions must first be qualified under a separately approved scope; this document does not authorize that work.

The immediate next action is review of the complete retained Stage 6 evidence and the proposed claim, including unfavorable or inconclusive contrasts. Do not infer that more repetitions, more GPU time, or another internal-manuscript reconciliation automatically supplies the missing scientific result. No further experiments or manuscript submission are authorized by this package.
