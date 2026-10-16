#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p artifacts/paper
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=artifacts/paper paper-preview.tex > metadata/latex-build.log 2>&1
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=artifacts/paper paper-preview.tex >> metadata/latex-build.log 2>&1
