# Focused articulation regression results

29/29 additional regression cases matched their frozen original and repaired outcome vectors; 0 discrepancies. These cases remain separate from the original 28-case suite.

Exit codes: **0** acceptance, **1** rejection, **2** monitor error. Each matrix cell is **expected/actual articulation exit code**. Original means the archived compiled RML; repaired means the current compiler-generated RML monitor.

## Scope and interpretation

The 18 direct fixtures invoke only the actual compiled articulation monitor through the project batch runner. The 11 complete cases encode and decode synthetic MIDI, call the actual browser `toPerformance` conversion and local `analyse` service, and execute all seven checks in a fresh Prolog process per request. Complete cases do not exercise live MIDI capture, HTTP transport or independent alignment.

All six other checks accepted in both versions for all 11 complete service cases (22 checked version/case vectors). The saved original and repaired enriched service traces are byte-identical for each case.

Final null-gap fixtures use a deliberately long **25,000 ms** duration for each supported monitor articulation (staccato, tenuto and legato) and for an unmarked event. Acceptance means that the next-attack duration requirement is **inapplicable**; the final duration has not been verified. The complete MusicXML/service path covers staccato, tenuto and unmarked final events.

Numeric fixtures exercise 374, 375 and 376 ms at a 500 ms gap: staccato retains `duration <= 0.75 * gap`; tenuto and legato retain `duration >= 0.75 * gap`. Earlier violations still reject when followed by a marked null-gap event. Two malformed non-null operand controls retain exit 2 in both versions; arbitrary monitor errors have not been converted into acceptance.

Installed Partitura 1.9.0 MusicXML get_articulations recognises staccato and tenuto, but not literal legato. Detached-legato is a different unchanged token. Literal legato is tested only by direct compiled-monitor fixtures.

## Frozen expectations and provenance

- [Separate expectation ledger](results/regression-expected-v2.json), manually frozen at `2026-10-14T13:43:35.755712+00:00` before regression monitor execution.
- Ledger SHA-256: `8fc953636d0e1d68906e9bc02e99d7b551e35417d3d33b0db06666eaaa446ad4`.
- Execution: `2026-10-14T13:43:49.818079+00:00` to `2026-10-14T13:44:10.221238+00:00`.
- Original compiled articulation SHA-256: `e905cff6dcc7e365f268877f039cb3f2f8bee7ebe8c17cb0808f196b8bbe28a2`.
- Repaired compiled articulation SHA-256: `501ecf5d6e73fbc87ae403ee0ce4b91e5b4ea4bb514123568898c9628e7313f3`.
- [Raw expected/actual vectors and comparison](results/regressions.json); [fixture notes](fixtures/regressions/README.md).

5 additional cases change articulation from monitor error (2) to acceptance (0): the three marked direct null-gap cases and the staccato/tenuto complete final-null cases. These are the changes declared in advance in the separate regression ledger.

## Direct compiled articulation monitor (18 cases)

| Case | Original E/A | Repaired E/A | Status | Retained evidence |
|---|---:|---:|---|---|
| `direct_final_null_staccato` | 2/2 | 0/0 | pass | [input](fixtures/regressions/direct/direct_final_null_staccato.jsonl); [artefacts](artifacts/regressions/direct_final_null_staccato/); [original](artifacts/regressions/direct_final_null_staccato/original-actual.json); [repaired](artifacts/regressions/direct_final_null_staccato/repaired-actual.json) |
| `direct_final_null_tenuto` | 2/2 | 0/0 | pass | [input](fixtures/regressions/direct/direct_final_null_tenuto.jsonl); [artefacts](artifacts/regressions/direct_final_null_tenuto/); [original](artifacts/regressions/direct_final_null_tenuto/original-actual.json); [repaired](artifacts/regressions/direct_final_null_tenuto/repaired-actual.json) |
| `direct_final_null_legato` | 2/2 | 0/0 | pass | [input](fixtures/regressions/direct/direct_final_null_legato.jsonl); [artefacts](artifacts/regressions/direct_final_null_legato/); [original](artifacts/regressions/direct_final_null_legato/original-actual.json); [repaired](artifacts/regressions/direct_final_null_legato/repaired-actual.json) |
| `direct_final_null_unmarked` | 0/0 | 0/0 | pass | [input](fixtures/regressions/direct/direct_final_null_unmarked.jsonl); [artefacts](artifacts/regressions/direct_final_null_unmarked/); [original](artifacts/regressions/direct_final_null_unmarked/original-actual.json); [repaired](artifacts/regressions/direct_final_null_unmarked/repaired-actual.json) |
| `direct_staccato_374ms` | 0/0 | 0/0 | pass | [input](fixtures/regressions/direct/direct_staccato_374ms.jsonl); [artefacts](artifacts/regressions/direct_staccato_374ms/); [original](artifacts/regressions/direct_staccato_374ms/original-actual.json); [repaired](artifacts/regressions/direct_staccato_374ms/repaired-actual.json) |
| `direct_staccato_375ms` | 0/0 | 0/0 | pass | [input](fixtures/regressions/direct/direct_staccato_375ms.jsonl); [artefacts](artifacts/regressions/direct_staccato_375ms/); [original](artifacts/regressions/direct_staccato_375ms/original-actual.json); [repaired](artifacts/regressions/direct_staccato_375ms/repaired-actual.json) |
| `direct_staccato_376ms` | 1/1 | 1/1 | pass | [input](fixtures/regressions/direct/direct_staccato_376ms.jsonl); [artefacts](artifacts/regressions/direct_staccato_376ms/); [original](artifacts/regressions/direct_staccato_376ms/original-actual.json); [repaired](artifacts/regressions/direct_staccato_376ms/repaired-actual.json) |
| `direct_earlier_bad_then_null_staccato` | 1/1 | 1/1 | pass | [input](fixtures/regressions/direct/direct_earlier_bad_then_null_staccato.jsonl); [artefacts](artifacts/regressions/direct_earlier_bad_then_null_staccato/); [original](artifacts/regressions/direct_earlier_bad_then_null_staccato/original-actual.json); [repaired](artifacts/regressions/direct_earlier_bad_then_null_staccato/repaired-actual.json) |
| `direct_tenuto_374ms` | 1/1 | 1/1 | pass | [input](fixtures/regressions/direct/direct_tenuto_374ms.jsonl); [artefacts](artifacts/regressions/direct_tenuto_374ms/); [original](artifacts/regressions/direct_tenuto_374ms/original-actual.json); [repaired](artifacts/regressions/direct_tenuto_374ms/repaired-actual.json) |
| `direct_tenuto_375ms` | 0/0 | 0/0 | pass | [input](fixtures/regressions/direct/direct_tenuto_375ms.jsonl); [artefacts](artifacts/regressions/direct_tenuto_375ms/); [original](artifacts/regressions/direct_tenuto_375ms/original-actual.json); [repaired](artifacts/regressions/direct_tenuto_375ms/repaired-actual.json) |
| `direct_tenuto_376ms` | 0/0 | 0/0 | pass | [input](fixtures/regressions/direct/direct_tenuto_376ms.jsonl); [artefacts](artifacts/regressions/direct_tenuto_376ms/); [original](artifacts/regressions/direct_tenuto_376ms/original-actual.json); [repaired](artifacts/regressions/direct_tenuto_376ms/repaired-actual.json) |
| `direct_earlier_bad_then_null_tenuto` | 1/1 | 1/1 | pass | [input](fixtures/regressions/direct/direct_earlier_bad_then_null_tenuto.jsonl); [artefacts](artifacts/regressions/direct_earlier_bad_then_null_tenuto/); [original](artifacts/regressions/direct_earlier_bad_then_null_tenuto/original-actual.json); [repaired](artifacts/regressions/direct_earlier_bad_then_null_tenuto/repaired-actual.json) |
| `direct_legato_374ms` | 1/1 | 1/1 | pass | [input](fixtures/regressions/direct/direct_legato_374ms.jsonl); [artefacts](artifacts/regressions/direct_legato_374ms/); [original](artifacts/regressions/direct_legato_374ms/original-actual.json); [repaired](artifacts/regressions/direct_legato_374ms/repaired-actual.json) |
| `direct_legato_375ms` | 0/0 | 0/0 | pass | [input](fixtures/regressions/direct/direct_legato_375ms.jsonl); [artefacts](artifacts/regressions/direct_legato_375ms/); [original](artifacts/regressions/direct_legato_375ms/original-actual.json); [repaired](artifacts/regressions/direct_legato_375ms/repaired-actual.json) |
| `direct_legato_376ms` | 0/0 | 0/0 | pass | [input](fixtures/regressions/direct/direct_legato_376ms.jsonl); [artefacts](artifacts/regressions/direct_legato_376ms/); [original](artifacts/regressions/direct_legato_376ms/original-actual.json); [repaired](artifacts/regressions/direct_legato_376ms/repaired-actual.json) |
| `direct_earlier_bad_then_null_legato` | 1/1 | 1/1 | pass | [input](fixtures/regressions/direct/direct_earlier_bad_then_null_legato.jsonl); [artefacts](artifacts/regressions/direct_earlier_bad_then_null_legato/); [original](artifacts/regressions/direct_earlier_bad_then_null_legato/original-actual.json); [repaired](artifacts/regressions/direct_earlier_bad_then_null_legato/repaired-actual.json) |
| `direct_malformed_nonnull_gap` | 2/2 | 2/2 | pass | [input](fixtures/regressions/direct/direct_malformed_nonnull_gap.jsonl); [artefacts](artifacts/regressions/direct_malformed_nonnull_gap/); [original](artifacts/regressions/direct_malformed_nonnull_gap/original-actual.json); [repaired](artifacts/regressions/direct_malformed_nonnull_gap/repaired-actual.json) |
| `direct_malformed_duration` | 2/2 | 2/2 | pass | [input](fixtures/regressions/direct/direct_malformed_duration.jsonl); [artefacts](artifacts/regressions/direct_malformed_duration/); [original](artifacts/regressions/direct_malformed_duration/original-actual.json); [repaired](artifacts/regressions/direct_malformed_duration/repaired-actual.json) |

## Complete converter and service path (11 cases)

| Case | Original E/A | Repaired E/A | Status | Retained evidence |
|---|---:|---:|---|---|
| `service_final_null_staccato` | 2/2 | 0/0 | pass | [input](artifacts/regressions/service_final_null_staccato/service-input.json); [artefacts](artifacts/regressions/service_final_null_staccato/); [original](artifacts/regressions/service_final_null_staccato/original-actual.json); [repaired](artifacts/regressions/service_final_null_staccato/repaired-actual.json) |
| `service_final_null_tenuto` | 2/2 | 0/0 | pass | [input](artifacts/regressions/service_final_null_tenuto/service-input.json); [artefacts](artifacts/regressions/service_final_null_tenuto/); [original](artifacts/regressions/service_final_null_tenuto/original-actual.json); [repaired](artifacts/regressions/service_final_null_tenuto/repaired-actual.json) |
| `service_final_null_unmarked` | 0/0 | 0/0 | pass | [input](artifacts/regressions/service_final_null_unmarked/service-input.json); [artefacts](artifacts/regressions/service_final_null_unmarked/); [original](artifacts/regressions/service_final_null_unmarked/original-actual.json); [repaired](artifacts/regressions/service_final_null_unmarked/repaired-actual.json) |
| `service_earlier_bad_then_null_staccato` | 1/1 | 1/1 | pass | [input](artifacts/regressions/service_earlier_bad_then_null_staccato/service-input.json); [artefacts](artifacts/regressions/service_earlier_bad_then_null_staccato/); [original](artifacts/regressions/service_earlier_bad_then_null_staccato/original-actual.json); [repaired](artifacts/regressions/service_earlier_bad_then_null_staccato/repaired-actual.json) |
| `service_staccato_374ms` | 0/0 | 0/0 | pass | [input](artifacts/regressions/service_staccato_374ms/service-input.json); [artefacts](artifacts/regressions/service_staccato_374ms/); [original](artifacts/regressions/service_staccato_374ms/original-actual.json); [repaired](artifacts/regressions/service_staccato_374ms/repaired-actual.json) |
| `service_staccato_375ms` | 0/0 | 0/0 | pass | [input](artifacts/regressions/service_staccato_375ms/service-input.json); [artefacts](artifacts/regressions/service_staccato_375ms/); [original](artifacts/regressions/service_staccato_375ms/original-actual.json); [repaired](artifacts/regressions/service_staccato_375ms/repaired-actual.json) |
| `service_staccato_376ms` | 1/1 | 1/1 | pass | [input](artifacts/regressions/service_staccato_376ms/service-input.json); [artefacts](artifacts/regressions/service_staccato_376ms/); [original](artifacts/regressions/service_staccato_376ms/original-actual.json); [repaired](artifacts/regressions/service_staccato_376ms/repaired-actual.json) |
| `service_earlier_bad_then_null_tenuto` | 1/1 | 1/1 | pass | [input](artifacts/regressions/service_earlier_bad_then_null_tenuto/service-input.json); [artefacts](artifacts/regressions/service_earlier_bad_then_null_tenuto/); [original](artifacts/regressions/service_earlier_bad_then_null_tenuto/original-actual.json); [repaired](artifacts/regressions/service_earlier_bad_then_null_tenuto/repaired-actual.json) |
| `service_tenuto_374ms` | 1/1 | 1/1 | pass | [input](artifacts/regressions/service_tenuto_374ms/service-input.json); [artefacts](artifacts/regressions/service_tenuto_374ms/); [original](artifacts/regressions/service_tenuto_374ms/original-actual.json); [repaired](artifacts/regressions/service_tenuto_374ms/repaired-actual.json) |
| `service_tenuto_375ms` | 0/0 | 0/0 | pass | [input](artifacts/regressions/service_tenuto_375ms/service-input.json); [artefacts](artifacts/regressions/service_tenuto_375ms/); [original](artifacts/regressions/service_tenuto_375ms/original-actual.json); [repaired](artifacts/regressions/service_tenuto_375ms/repaired-actual.json) |
| `service_tenuto_376ms` | 0/0 | 0/0 | pass | [input](artifacts/regressions/service_tenuto_376ms/service-input.json); [artefacts](artifacts/regressions/service_tenuto_376ms/); [original](artifacts/regressions/service_tenuto_376ms/original-actual.json); [repaired](artifacts/regressions/service_tenuto_376ms/repaired-actual.json) |

## Reproduce

Run from the repository root, after compiling the repaired RML and preserving the archived original:

```bash
PYTHONDONTWRITEBYTECODE=1 evaluation/.venv/bin/python evaluation/scripts/regressions.py --generate-only
PYTHONDONTWRITEBYTECODE=1 evaluation/.venv/bin/python evaluation/scripts/regressions.py --run
PYTHONDONTWRITEBYTECODE=1 evaluation/.venv/bin/python evaluation/scripts/regression_report.py
```

Generation refuses to revise an existing frozen ledger. Raw results retain every original/repaired stdout, stderr, warning and verdict; the runner exits non-zero for an unexpected outcome or change. This document and the LaTeX matrix are derived from those saved results, without running monitors.
