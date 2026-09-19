#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/pages review
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex > review/build.log 2>&1
pdftoppm -r 120 -png build/main.pdf build/pages/final > review/render.log 2>&1
python scripts/check_draft.py > review/check_output.txt
cp build/main.pdf review.pdf
printf 'Built anonymous review.pdf; rendered every page in build/pages/.\n'
cat review/check_output.txt
