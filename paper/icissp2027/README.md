# ICISSP 2027 first complete regular-paper draft

Start with [review.pdf](review.pdf). The [LaTeX source](main.tex), [bibliography](references.bib), four vector figures, three tables and two exact carrier excerpts form a complete anonymous draft. The existing blueprint and its claim matrix remain unchanged in the parent directory.

This package uses saved evidence at `87cc8c8394a1e1b370825cf565bb0e132da14954`. It runs **no inference, experimental cases, benchmarks, detector training or software test suite**. The manuscript's R, F and control results belong to their original tested revisions. The drafting commit is not GPU-tested research code.

See [DRAFT_STATUS.md](DRAFT_STATUS.md) for final counts and visual checks, [EVIDENCE_MAP.md](EVIDENCE_MAP.md) for every reported result, [REVIEWER_MEMO.md](REVIEWER_MEMO.md) for material objections, and [AI_USE_DISCLOSURE.md](AI_USE_DISCLOSURE.md) for disclosure and the author-review policy question.

## Regenerate figures and tables from existing records

Run from the repository root in the already installed working environments:

```bash
PYTHONPATH=.venv/lib/python3.10/site-packages \
MPLCONFIGDIR=/tmp/icissp-paper-mpl \
../llm-rankcloak/.venv/bin/python paper/icissp2027/scripts/generate_assets.py \
  > paper/icissp2027/review/asset_generation.log 2>&1
PYTHONPATH=.venv/lib/python3.10/site-packages \
../llm-rankcloak/.venv/bin/python paper/icissp2027/scripts/evidence_map.py \
  > paper/icissp2027/review/evidence_check.log 2>&1
bash paper/icissp2027/scripts/build.sh
```

The first command uses the existing sibling matplotlib environment and project dependencies. It reads the local artifact files, never a model or private key. The second command reconciles the claim-to-evidence map. The third runs `latexmk`/BibTeX, renders **every page** with `pdftoppm`, checks visible characters and anonymity, and copies the final PDF to `review.pdf`. No network is needed after the template is present. The invoked Python libraries are matplotlib 3.10.9 and the project's existing NumPy/HPKE dependency environment. HPKE is imported indirectly by the existing public predicate helper but no encryption or decryption is executed for these paper calculations.

A portable environment needs Python 3.10+, matplotlib, NumPy and the pinned project dependencies, plus pdfLaTeX, BibTeX/latexmk, the template packages and Poppler (`pdftotext`, `pdftoppm`, `pdfinfo`, `pdffonts`). Font families are the official template's Times setup and embedded Liberation Serif in vector plots. Do not change margins, template styles or font sizes to reproduce the page count.

To build without regenerating already committed figures:

```bash
bash paper/icissp2027/scripts/build.sh
```

Individual commands from this directory are:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex
pdftoppm -r 120 -png build/main.pdf build/pages/final
python scripts/check_draft.py
cp build/main.pdf review.pdf
```

`build/` holds disposable TeX intermediates and page renders and is ignored. The reviewed PDF and compact build/check outputs are committed. `generate_assets.py` writes only inside this paper directory and regenerates two numerical tables, one descriptive profile table, four PDF/SVG figures, exact UTF-8 excerpts, raw score/rate CSVs and their evidence hashes. It recomputes point estimates and Stage 9 predicates from retained records. Reported bootstrap intervals are the saved, source-linked analyses; this task does not silently replace their resampling rules.

## Official template and limits

The template was downloaded from the LaTeX link on the current [ICISSP template page](https://icissp.scitevents.org/Templates.aspx). All four required formatting files are copied **byte-for-byte**, including the supplied `article.cls` and `apalike` style. The source instructions identify the example as June 2026 and the style as May 2023. [Template/policy provenance](review/template_and_policy.json) records the archive and file hashes. These files retain the publisher's notices; this project does not claim authorship of them.

Current [guidelines](https://icissp.scitevents.org/Guidelines.aspx) specify 10,000–50,000 non-whitespace characters for a regular submission, including all manuscript components. The 12-page accepted-full-paper allowance is separate. [Current dates](https://icissp.scitevents.org/ImportantDates.aspx) retain **22 October 2026 AoE** for second-stage regular submission. This package does not submit a paper.

## Anonymous PDF and public posting

The review PDF contains no author block, affiliations, acknowledgments, personal repository links, private keys or identifying PDF metadata. No anonymous artifact URL has been invented. Internal source commits, exact attempt identifiers, reused-code attribution and author-specific overlap questions remain in this repository-side package, outside the review PDF. The PDF is anonymous in its contents, not unlinkable to an already public project or title.

Known status was checked before publication of this draft. The existing blueprint explicitly says no manuscript had been submitted, and this task requests the first draft. No submission receipt or evidence that this paper is under review was found. Thus no known current-review posting restriction blocks the authorized push. The conference prohibits public posting of submitted papers during review. Recheck status before **future** public revisions once submission occurs; do not infer permission for those revisions from this pre-submission push. No repository visibility was changed and nothing was uploaded to a separate preprint service.
