# First complete draft status

**Complete, compiled and visually reviewed. Ready for author/content review, not submitted and not certified publication-ready.**

- Branch: `main`. Starting/source-evidence revision: `87cc8c8394a1e1b370825cf565bb0e132da14954`, clean working tree. All changes are under `paper/icissp2027/`.
- Manuscript: [main.tex](main.tex); anonymous PDF: [review.pdf](review.pdf); bibliography: [references.bib](references.bib).
- **12 A4 pages**, **4 vector figures**, **3 tables**, **2 integrated retained-case examples**, **173-word abstract**.
- **42,732 extracted non-whitespace characters** after Unicode NFKC normalization. Charging 12 possibly missing plot-label characters gives **42,744**. Conservative screening upper estimate **44,987**, leaving **5,013 characters** below 50,000. The current minimum is 10,000.
- Official template files are unchanged; no margin, font or spacing compression was used. Body is the template's 10-point Times setup, tables/captions 9-point. Plots use embedded accessible-color/marker vector graphics.
- PDF author, creator, producer, subject and keyword metadata are empty. No author/affiliation/acknowledgment block, personal repository URL, test private key or fabricated anonymous artifact URL appears in the PDF.
- PDF SHA-256: `0bd5da5ec7559b40dc077a8775b7b4c88e71602892dde96435e4925d79d19d09`.

## Character count and uncertainty

[scripts/check_draft.py](scripts/check_draft.py) extracts the complete rendered PDF with `pdftotext`, normalizes Unicode compatibility ligatures, and counts non-whitespace Unicode characters. This includes title, abstract, all prose, equations as extracted, table contents, captions, footnotes, citations, references and extracted vector labels. It does not count LaTeX commands. Layout-preserving and ordinary extraction counts are both retained in [draft_checks.json](review/draft_checks.json).

The figure generator separately inventories every plot/diagram text label. Their combined inventory is 1,400 non-whitespace characters, many already present in the PDF count. Three `1.75` tick labels are flagged as not extracted, contributing 12 conservatively charged characters; they are outside the visible plotted axes. Rather than assume exact extraction, the screening estimate charges **all** figure labels again and adds 2% of extracted content for possible ligature, mathematical-symbol or extraction discrepancies. This intentionally double counts labels. The 2% is a pragmatic uncertainty allowance, not a proven bound or the conference submission system's official counter. The comfortable remaining margin avoids relying on an exact match between counters.

The [current guidelines](https://icissp.scitevents.org/Guidelines.aspx) retain 10,000–50,000 characters excluding whitespace, including references/tables/graphs/appendices. The **12-page accepted-full-paper proceedings limit is separate**. No policy change from the prior recorded requirement was found. Template instructions additionally specify a 70–200-word abstract, which this draft satisfies.

## Build and page review

`latexmk` completed pdfLaTeX/BibTeX successfully. There are no undefined citations or references, overfull boxes or LaTeX errors. 26 underfull-line notices arise from the narrow-column typography and were reviewed in the render; they are not clipping or missing content. The prior plot-font embedding warning was corrected. Final Poppler rendering emits no warnings.

Every page was rendered at 120 DPI and visually inspected. Full-resolution checks cover the result tables, capacity traces, stopping matrix, score plots and exact Unicode excerpts. Captions, labels, mathematical definitions, float placement and references are readable and within margins. [visual_review.json](review/visual_review.json) records page hashes and findings. This is an agent visual/layout review, not an independent human scientific endorsement. The anonymous template's empty-author spacing and ordinary end-of-document whitespace are retained.

Reproduction commands are in [README.md](README.md) and [commands.json](review/commands.json). Generation checks read retained public scoring tables, independently recompute reported point estimates and Stage 9 predicates, check the historical prefix extension and pair trajectories, and verify exact carrier/envelope/payload hashes. Saved bootstrap intervals retain their original rules and revisions.

## Evidence preservation and publication state

All **3,043 previously tracked files** match their pre-draft hashes, including every historical report, codec, experimental artifact, configuration and authoritative ledger/checkpoint. No earlier report or conclusion was rewritten. Experimental accounting remains **16,079.239397775 GPU-job seconds, 252,875 evaluated tokens and 283 cases** lifetime. This task used **0 inference jobs, 0 evaluated model tokens and 0 experimental cases**. No broad tests, benchmarks or training ran.

Ledger SHA-256 remains `e6df99cf56ac526bd38f1f92de2c65921b24e6c6f8045484d546242c660a51ae`. This paper's host analysis is not relabelled as a new GPU-tested revision. [EVIDENCE_MAP.md](EVIDENCE_MAP.md) links each result to its actual source revision.

Known submission status was checked in the repository and current instructions. The prior blueprint says not submitted; this is explicitly the first complete draft, and no contrary receipt/review status was found. Therefore there is no known active-review posting blocker to the authorized main push. No paper was submitted or posted to a separate preprint service; visibility was not changed. Recheck posting restrictions before future public changes after submission. The intended second-stage deadline remains **22 October 2026 AoE**, checked on the [official dates page](https://icissp.scitevents.org/ImportantDates.aspx).

## Remaining author decisions

1. Is the bounded finite-packet/stopping decomposition sufficiently distinct for a regular paper, given NLS, Meteor and prior tokenization-consistency work? Small, selected delivered samples do not support broad recognition or reliability claims.
2. Resolve submission-specific overlap and contribution allocation across related projects. No missing private manuscript blocked this draft, and no overlap clearance is claimed.
3. Approve the non-identifying AI disclosure placement. The venue asks for disclosure while anonymous review removes acknowledgments; the draft uses a separate section plus tool citations. [AI_USE_DISCLOSURE.md](AI_USE_DISCLOSURE.md) records the ambiguity and exact known tool identity.
4. Conduct human technical/citation/editorial review and determine any permitted anonymous artifact/supplement arrangement. No hosting address was invented.

The draft is complete without additional experiments. It retains contrary AUCs, the 128-byte capacity failures and the retrospective-only accepted prefix. No new study is recommended automatically.
