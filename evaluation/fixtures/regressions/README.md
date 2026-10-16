# Focused articulation regressions

These additional cases are separate from the original 28-case suite. Generate and freeze manual original/repaired expectations before executing monitors:

```bash
PYTHONDONTWRITEBYTECODE=1 evaluation/.venv/bin/python evaluation/scripts/regressions.py --generate-only
PYTHONDONTWRITEBYTECODE=1 evaluation/.venv/bin/python evaluation/scripts/regressions.py --run
```

`results/regression-expected-v2.json` is immutable once generated. Direct JSONL fixtures invoke the actual batch monitor with archived original and current compiled RML. Converter/service cases encode and decode MIDI, call the actual browser `toPerformance`, then call the actual local `analyse` service with all seven checks and a fresh Prolog process. The two paths are labelled in every result.

A 25,000 ms final duration deliberately demonstrates that null-gap acceptance means the duration requirement is inapplicable; it does not verify that duration. Numeric boundaries are 374/375/376 ms for a 500 ms gap. Earlier violations must reject even when the trace ends with a marked null-gap attack. Malformed non-null numeric operands must retain their monitor errors.

Partitura's MusicXML articulation importer exposes staccato and tenuto, but not the literal `legato` used by this monitor. `detached-legato` is a different unchanged token. Legato therefore has direct monitor coverage only; no unsupported MusicXML legato service coverage is claimed.
