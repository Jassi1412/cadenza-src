#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
eval_python="${EVAL_PYTHON:-python3.11}"
"$eval_python" -m venv evaluation/.venv
evaluation/.venv/bin/python -m pip install --no-cache-dir -r server/requirements.txt -c evaluation/metadata/python-freeze.txt
mkdir -p evaluation/.node
node - <<'JS'
const fs = require('fs');
const lock = JSON.parse(fs.readFileSync('web-app/package-lock.json'));
const version = lock.packages['node_modules/typescript'].version;
fs.writeFileSync('evaluation/.node/package.json', JSON.stringify({private:true,dependencies:{typescript:version}}, null, 2)+'\n');
JS
npm install --prefix evaluation/.node --ignore-scripts --no-audit --no-fund
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMBA_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
evaluation/.venv/bin/python evaluation/scripts/prepare.py
node evaluation/scripts/replay.mjs --self-test > evaluation/metadata/browser-self-test.json
evaluation/.venv/bin/python -m pip check
