# Evaluation

## Purpose

Reproducible synthetic behavioural validation and local service-cost measurements for the Cadenza paper.

## Ownership

- `scripts/` generates inputs, calls actual project functions, benchmarks and derives reports.
- `REGRESSIONS.md` and `tables/regressions.tex` are rendered from the separate focused regression raw results.
- `fixtures/` holds the original exercise, its interpretation and the separate final-marked defect diagnostic.
- `results/`, `artifacts/`, `tables/` and `metadata/` retain raw evidence, summaries and provenance.
- `diagnostics/` preserves harness-only failed attempts separately from application results.
- `archive/v1-original/` preserves the complete original evaluation and original project snapshot, verified against its manifest.
- `SHARING.md` and the archive's `SHARING-EXCLUSIONS.json` document expendable files omitted from Git. The frozen manifest is preserved; missing scientific evidence must still fail verification.

## Local contracts

- The authorised null-gap repair is limited to moving `noGap` ahead of numeric articulation alternatives. Preserve numeric constraints and unrelated application/assessment policies.
- Preserve the original frozen ledger unchanged; repaired predictions use `results/expected-verdicts-v2.json`. Keep the additional regression suite separate from the original 28 cases.
- Expected verdicts are manually reasoned and frozen before execution. Never revise them to fit observations.
- Parsing, matching, browser conversion and monitoring must call the actual implementation.
- Preserve every timing sample, failure, warning and discrepancy. Distinguish request completion from metric acceptance and monitor errors.
- Derive reported numbers from raw data. Label all performances synthetic and retain the own-timing-map dependence and provenance limitation.

## Verification

Run `evaluation/.venv/bin/python evaluation/scripts/check.py` after generation, validation, benchmarking, summarisation and paper rendering. Reproduction commands and timing boundaries are in `README.md`.

## Child DOX index

None.
