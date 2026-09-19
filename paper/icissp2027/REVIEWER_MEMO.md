# First-draft reviewer objections and remaining decisions

The complete draft is a bounded empirical systems/security case study, not a secure-stegosystem proposal. Its strongest contribution is the evidence-backed separation of information accumulation, text recovery, message boundaries and finite-packet replay under an actual UTF-8 contract. Whether that constitutes enough new insight for a standalone regular paper remains an author and reviewer judgment.

| Likely objection | Evidence and present response | Remaining judgment |
|---|---|---|
| The mechanisms are known. | Reverse arithmetic coding, low-entropy trouble, public ciphertext extraction and full-prefix verification are explicitly attributed. No new coder, cryptographic primitive, theorem or generic filter is claimed. | The joint retained diagnosis and paired boundary experiment may still be too implementation-specific. Decide whether the causal/accounting decomposition adds enough beyond NLS, Meteor and tokenization work. |
| Too few arithmetic messages deliver. | S8 R32 is 2/4 and R128 is 0/4. S9 R32 is 4/6. Historical diagnostics and replays stay outside denominators. The two-pair AUC 0.5 and four-pair AUC 1.0 both remain. | These data cannot support a broad statistical-recognition tradeoff. The paper must remain a bounded case study. No additional experiment is required for its current descriptive claims. |
| Controls are engineered, not normal traffic. | A/B/C are named model distributions. S9 pairs B-fixed and B-stop at the same seed. Neither is called human cover traffic or the uniquely correct null. | Decide whether the diagnostic generator question is consequential enough for the intended security audience. |
| The finite-packet signal is a chosen convention. | The deterministic midpoint extension and integer canonical replay are precisely described and explicitly limited to this adapter. One selected historical prefix passes, so no universal recognizer is claimed. | Alternative termination conventions are untested. Do not imply that all arithmetic steganography shares this signal. |
| Capacity failures select the recognition sample. | Rates include failed attempts; observer outcomes use delivered/scorable denominators. Internal aborts are not treated as network observations. S9 has only three delivered stopped controls. | No population false-positive or length-independent score claim follows. Keep the explicit conditional interpretation. |
| The model/runtime is unusually restricted. | One quantized model, common 16-candidate support, short selected contexts, one GPU, public size classes and unchanged text are disclosed. Backend binaries are hashed but native source-build provenance is incomplete. | General reliability, portability, human-like language and robustness remain unestablished. |
| Reuse and author-specific project overlap. | MIT helper provenance from RankCloak/ImageCalgacus remains in the repository notices. The original Calgacus reference is MIT; no unlicensed NLS code is copied. The old Stage 5 assessment remains intact. | Execution gates were explicitly set aside. Authors still need a submission-specific contribution-allocation and overlap decision. No manuscript request or novelty clearance is implied here. |
| Anonymity or AI disclosure is incomplete. | The PDF contains no author details or personal repository links. Citations and a non-identifying disclosure remain. Source hashes and attribution live outside the PDF. | Public project/title linkage cannot be undone by stripping metadata. Resolve the acknowledgment/disclosure policy ambiguity and review pre-submission anonymity in light of already public work. |

## Source and interpretation corrections made while drafting

- Kept arithmetic qualification, repeated historical packets, fresh transmissions and retrospective prefixes separate.
- Kept all four fresh S8 R128 failures and both S9 R capacity failures in recovery counts.
- Used complete-message scores for the main figure; the S6 body score of 0.410 against uniform controls is identified separately. Its complete-message value is 0.3671875, not 0.410.
- Preserved higher-is-carrier orientation, including below-chance results. No pooled cross-stage AUC or threshold tuning is introduced.
- Kept packet completion separate from local filler, canonical replay and KEM. Unavailable downstream checks on incomplete controls are not converted into failures.
- Interpreted the necessary X25519 representation check as an honest-output encoding constraint, not point validity, authentication or an HPKE break.
- Clarified mean per-message useful rate, all-attempt useful rate and aggregate delivered bit/token ratios; none is relabelled as the other.
- The shortened historical 938-token control is an illustrative counterexample, not a prospective false-positive sample.

## Material author decisions before submission

1. Accept or narrow the empirical contribution in light of the known-mechanism objection. The first complete draft supports review; it does not certify novelty or acceptance readiness.
2. Decide overlap and allocation among related projects without attributing our profile-specific findings to all Calgacus or arithmetic methods. Private manuscript reconciliation was not a prerequisite to this draft.
3. Read and approve all source interpretations, numerical claims and the exact generated-text excerpts. The excerpts contain fictional model statements and synthetic binary payloads, not actual museum facts or personal messages.
4. Confirm the venue's anonymous AI-disclosure placement and any desired supplement/artifact policy. No anonymous hosting URL is invented.
5. Confirm no review has begun before future public manuscript revisions. The known repository state says not submitted. Keep the planned **22 October 2026 AoE** second-stage submission deadline separate from camera-ready requirements.

No new experimental stage is prescribed. Existing records support every deliberately bounded empirical claim in this draft. Broader concealment, robustness or general comparative superiority would require different evidence, so those claims are absent.
