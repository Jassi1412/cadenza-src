# Cadenza local experimental evaluation

For the Git distribution, [SHARING.md](SHARING.md) documents omitted local backups, caches, duplicate logs and rendered previews. Frozen scientific data and manifests remain unchanged; explicit sharing exclusions keep validation usable without those expendable files.

This directory contains the local evaluation after repairing the articulation monitor's final marked-note exception. Performances are deterministic synthetic MIDI. The experiments exercise the existing converter, enrichment and compiled monitors; they do not validate live capture, independent alignment accuracy or complete musical assessment. The experiments ran locally; source sharing is documented in [SHARING.md](SHARING.md).

Read [REPORT.md](REPORT.md) for the paper-facing report, [RESULTS.md](RESULTS.md) for generated results, and [evaluation.tex](evaluation.tex) for the British English LaTeX section. [IMPLEMENTATION.md](IMPLEMENTATION.md) describes the current seven specifications and remaining limitations. The project's metrics README describes older behaviour.

## Preserved evidence and repair

[archive/v1-original/](archive/v1-original/) preserves the original evaluation, sources, compiled specifications, inputs, diagnostics, reports and provenance. Its `MANIFEST.json` hashes 421 files. The archive is immutable and is checked before comparison and final verification. The original frozen ledger remains unchanged at [results/expected-verdicts.json](results/expected-verdicts.json). The separately frozen [results/expected-verdicts-v2.json](results/expected-verdicts-v2.json) changes only `final_marked_note` articulation from expected monitor error (2) to acceptance (0); its other six outcomes and every other original case prediction stay unchanged. Expectations are manually reasoned before repaired execution, never copied from actual results.

The original failing input is replayed with the archived compiled specifications in [diagnostics/null-gap-original-reproduction.json](diagnostics/null-gap-original-reproduction.json). The original RML tries numeric duration alternatives before `noGap`; the generated Prolog preserves that order, so CLP(R) receives `null` before reaching the exemption. The repair moves the existing `noGap` alternative first in `Main`. A null successor gap makes this duration requirement inapplicable; acceptance does not verify the final note's duration. Numeric predicates remain byte-identical: staccato uses `duration <= 0.75 * gap`, and tenuto/legato use `duration >= 0.75 * gap`.

[metadata/repair.diff](metadata/repair.diff) contains the RML and regenerated Prolog diffs. [metadata/repair-provenance.json](metadata/repair-provenance.json) records original/repaired hashes and the Git limitation. Only `rml/metrics/articulation.rml` changes among the original project files; the generated articulation module changes accordingly. The service, converter, other six specifications, pitch/coverage policies and pedal tolerances are preserved. The accessible project `.git` directory has no usable history, and Git resolves to an unrelated enclosing repository. Its HEAD is not attributed to Cadenza; content hashes identify the evaluated snapshot.

## Reproduce

Run commands from the project root. Required programs are Python 3.11 with `venv`, Java, SWI-Prolog and Node/npm. Recorded versions are Python 3.11.0rc1, OpenJDK 21.0.12.1, SWI-Prolog 9.1.21, Node 20.15.0 and TypeScript 6.0.2. Python differs from the service Docker image's Python 3.12. Exact environment and package versions are in [metadata/environment.json](metadata/environment.json) and [metadata/python-freeze.txt](metadata/python-freeze.txt).

With the existing evaluation environment, run:

```bash
bash evaluation/scripts/run.sh
```

`run.sh` archives active evidence before overwriting it and verifies the immutable original archive. To create or reinstall dependencies, archive first because `setup.sh` also regenerates compiled files and environment metadata:

```bash
python3 evaluation/scripts/archive.py
bash evaluation/scripts/setup.sh
bash evaluation/scripts/run.sh
```

`setup.sh` installs the repository's five pinned Python requirements with recorded transitive constraints and installs the lockfile's TypeScript version under `evaluation/.node`. Dependency downloads require network access; evaluation is local. `prepare.py` compiles all seven current `.rml` files with the vendored compiler and stages byte-identical `server.py`, `join.py` and `batch.pl` together, matching the Docker layout. This avoids the source-tree import path looking for `batch.pl` in `server/alignment/`.

The complete evaluation sequence, also implemented by `run.sh`, is:

```bash
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
```

Generation refuses to revise an existing frozen ledger. `compare.py --prepare` verifies the source repair, original input hashes, MIDI event counts and actual parsed workload counts before execution. `compare.py` compares every one of the original suite's 196 metric outcomes. `check.py` independently cross-checks raw samples, derived statistics, saved verdicts, ledgers, input identity, regression evidence, compilation hashes and archive integrity. No seed is needed because generation uses no randomness.

For the optional PDF preview, run `bash evaluation/scripts/build-paper.sh` after evaluation; this requires pdfLaTeX and writes `artifacts/paper/paper-preview.pdf`.

## Behavioural cases and regressions

The original 28-case suite retains exactly the original inputs. [fixtures/exercise.musicxml](fixtures/exercise.musicxml) is the eight-note exercise; [fixtures/interpretation.md](fixtures/interpretation.md) defines its score interpretation and teacher-error rubric. `exercise-final-marked.musicxml` is its separate final marked-note variant. Each `artifacts/behaviour/<case>/` retains MIDI, decoded events, browser conversion output, complete service input, enriched JSONL and actual results. [results/behaviour.json](results/behaviour.json) contains the repaired expected/actual matrix; [results/behaviour-comparison.json](results/behaviour-comparison.json) identifies every changed outcome. [results/input-identity-v2.json](results/input-identity-v2.json) records comparison with original inputs.

The 29 additional focused cases stay separate from that suite. Their manual original/repaired predictions are frozen in [results/regression-expected-v2.json](results/regression-expected-v2.json); the readable before/after matrix is [REGRESSIONS.md](REGRESSIONS.md), with raw outcomes in [results/regressions.json](results/regressions.json) and inputs/diagnostics under `fixtures/regressions/` and `artifacts/regressions/`.

- Eighteen direct fixtures invoke the actual compiled RML articulation monitor with archived original and repaired specifications. They cover final null-gap staccato, tenuto and literal legato; an unmarked final event; durations 374, 375 and 376 ms for a numeric 500 ms gap; earlier duration violations followed by marked null-gap events; and malformed non-null numeric operands that must retain monitor errors (2).
- Eleven converter/service cases encode and decode actual MIDI, invoke the actual browser `toPerformance`, parse MusicXML, enrich events and run all seven checks through the unchanged local service. They cover staccato/tenuto and an unmarked final event, the same numeric boundary, and earlier violations that must still reject. Original/repaired enriched traces are compared byte for byte.

Final null-gap fixtures deliberately retain a 25,000 ms performed duration to demonstrate inapplicability of the requirement. Earlier numeric violations must remain rejected. Partitura 1.9.0's MusicXML importer exposes staccato and tenuto but not literal `legato`; `detached-legato` is a different unchanged token. Literal legato therefore has direct compiled-monitor coverage only. No new MusicXML articulation mapping is introduced.

## Workload construction and observation limits

The repository scores produce 216 and 2,324 actual parsed notes. Their original input hashes, MIDI event counts, parsed models and XML counts are retained in [results/workloads.json](results/workloads.json) and `artifacts/workloads/score-216/` / `score-2324/`. Reproduction verifies identity with the original evaluation before timing.

Workload onsets use the implementation's own `ScoreModel.ms_at` map with `tempo_factor=1`, so this construction does not independently validate alignment. Onsets are rounded to the nearest 0.5 ms. Staccato durations are half the next distinct score-onset gap; tenuto/legato durations are 90% of that gap; unmarked durations are 80% of mapped written duration. For generation only, the final attack's mapped written duration substitutes for its unavailable successor interval when choosing a synthetic performed duration; enrichment still supplies `gapMs:null`. Durations are rounded to 0.5 ms with a 0.5 ms minimum. Explicit dynamic targets use nearest-integer, ties-to-even rounding; otherwise velocity is 80. Each parsed pedal span gets CC64=127 at mapped start +10 ms and CC64=0 at mapped end. Inputs are never adjusted to monitor outcomes.

MIDI is encoded at 1,000 ticks per quarter and 500,000 microseconds per quarter, giving 0.5 ms per tick. This is an encoding timebase: the score's variable timing map already determines absolute event times. Actual browser FIFO pairing is retained for overlapping repeated pitches. The existing exported `toPerformance` is transpiled and invoked as a full module, with React/network access disabled and the unrelated Vite environment stubbed.

Synthetic timestamps already have the intended score-time origin. The live `useMidi` → `ScorePage` → `useVerdict` path retains device timestamps without an explicit playback-start rebase, so capture, React lifecycle behaviour and live capture/playback clock alignment remain unvalidated. Missing score obligations and extra attacks can escape the existing checks. Pedal endpoint association can impose a 0.05-beat window despite the assessment rule's nominal 0.25-beat tolerance. These limitations are separate from the corrected null-gap exception and remain visible in the report.

## Timing boundary and sampling

Total time uses `time.perf_counter_ns()` immediately around the unchanged local `server.analyse(body)` call, preserving the original boundary. It includes request validation, temporary MusicXML creation, Partitura parsing, enrichment, JSONL serialisation and writing, fresh Prolog startup, specification loading, all seven sequential checks, verdict decoding and temporary-file cleanup. It excludes Python import/startup, input JSON loading, MIDI encoding/decoding, browser conversion/capture, HTTP/JSON transport, rendering and ahead-of-time RML compilation.

The workloads run in fixed order (2,324 then 216 notes), sequentially in one Python process. Each has three warm-ups followed by 30 measured calls. The first warm-up has no stage wrappers; the second verifies wrapper delegation preserves success, verdicts and every enriched event. Measured calls time parsing, enrichment, `to_jsonl` and the Prolog subprocess interval. Serialisation timing excludes writing, which remains in the total. The separately measured total is never reconstructed from component medians. Wrapper overhead and warning capture are included and not subtracted; warnings use an `always` filter.

Each service request reparses the score and starts one fresh SWI-Prolog process, which loads/unloads all seven modules and rewinds the trace for each check. Python, library and OS caches may remain warm. Numerical-library thread limits are one; CPU affinity, frequency and exclusive reservation are not imposed. Every rerun produces new raw samples; earlier timings are evidence, never targets or substitutes. Rejecting monitors can stop early, so these are local execution costs without worst-case, real-time, general scalability or user-facing latency guarantees. Seven checks being invoked does not imply seven accepting, full-trace checks.

## Raw results and diagnostics

[results/timings.jsonl](results/timings.jsonl) stores all 66 calls, including warm-ups, total/stage times, every verdict, warning and complete Prolog output. `timings.csv` provides timing/verdict columns. `summary.json`, Markdown and LaTeX tables derive from raw samples; quartiles use NumPy's linear interpolation. No failed run or outlier is silently discarded. Exit 0 means acceptance, 1 rejection and 2 monitor error; Python request completion is recorded separately.

`diagnose.py` invokes the unchanged standalone monitor on saved workload traces to locate early syncopated-pedal rejection. Exact commands, hashes and printed diagnostics are in [diagnostics/early-rejection.json](diagnostics/early-rejection.json); these calls are outside the timed batch path. Reports preserve rejection rather than characterising the workloads as seven fully accepting checks.

Original installation and wrapper failures remain in the immutable archive. The initial wrapper lacked `PIPE`, so its 28 calls failed before any monitor ran; this is separately retained harness evidence, not behavioural or timing data. The original generated Python cache change and absent project history remain documented in archived provenance. Reproduction disables further bytecode writes.
