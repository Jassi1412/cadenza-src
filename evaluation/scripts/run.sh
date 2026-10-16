#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMBA_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
evaluation/.venv/bin/python evaluation/scripts/archive.py
evaluation/.venv/bin/python evaluation/scripts/prepare.py
evaluation/.venv/bin/python evaluation/scripts/reproduce_original.py
evaluation/.venv/bin/python evaluation/scripts/generate.py
evaluation/.venv/bin/python evaluation/scripts/compare.py --prepare
evaluation/.venv/bin/python evaluation/scripts/regressions.py --generate-only
evaluation/.venv/bin/python evaluation/scripts/regressions.py --run
evaluation/.venv/bin/python evaluation/scripts/regression_report.py
evaluation/.venv/bin/python evaluation/scripts/validate.py
evaluation/.venv/bin/python evaluation/scripts/compare.py
evaluation/.venv/bin/python evaluation/scripts/benchmark.py
evaluation/.venv/bin/python evaluation/scripts/diagnose.py
evaluation/.venv/bin/python evaluation/scripts/summarise.py
evaluation/.venv/bin/python evaluation/scripts/paper.py
evaluation/.venv/bin/python evaluation/scripts/check.py
