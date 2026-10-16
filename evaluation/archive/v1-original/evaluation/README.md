# Cadenza local experimental evaluation

This directory contains the executed evaluation of the existing project on this machine. All performances are **deterministic synthetic MIDI**, rather than pianist recordings or a user study. Application sources and original specifications are preserved. Nothing was published or pushed.

Start with [REPORT.md](REPORT.md) for the paper-facing report, [RESULTS.md](RESULTS.md) for generated tables, and [evaluation.tex](evaluation.tex) for the British English LaTeX section. [IMPLEMENTATION.md](IMPLEMENTATION.md) documents the seven current specifications and their limitations. The metrics README in the project describes older behaviour.

## Reproduce

Run from the project root. Required system programs are Python 3.11 with `venv`, Java 21, SWI-Prolog and Node/npm. The actual recorded runtimes are Python **3.11.0rc1**, OpenJDK **21.0.12.1**, SWI-Prolog **9.1.21**, Node **20.15.0** and TypeScript **6.0.2**. Python differs from the service Docker image's Python 3.12. Exact package versions and machine details are in [metadata/environment.json](metadata/environment.json) and [metadata/python-freeze.txt](metadata/python-freeze.txt).

```bash
bash evaluation/scripts/setup.sh
bash evaluation/scripts/run.sh
```

`setup.sh` uses only the repository's five pinned Python requirements, constrains their transitive dependencies to the versions actually installed here, and installs the lockfile's TypeScript version separately under `evaluation/.node`. It compiles all seven original `.rml` files with the vendored compiler and stages byte-identical `server.py`, `join.py` and `batch.pl` together, following the existing Docker layout. This is necessary because importing `server/alignment/server.py` directly would look for `batch.pl` in the wrong local directory. No application repair is applied. Dependency downloads require network access; evaluation itself is local.

The step-by-step commands are:

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMBA_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
evaluation/.venv/bin/python evaluation/scripts/prepare.py
node evaluation/scripts/replay.mjs --self-test
evaluation/.venv/bin/python evaluation/scripts/generate.py
evaluation/.venv/bin/python evaluation/scripts/validate.py
evaluation/.venv/bin/python evaluation/scripts/benchmark.py
evaluation/.venv/bin/python evaluation/scripts/diagnose.py
evaluation/.venv/bin/python evaluation/scripts/summarise.py
evaluation/.venv/bin/python evaluation/scripts/paper.py
evaluation/.venv/bin/python evaluation/scripts/check.py
```

Generation freezes all manually reasoned expected verdicts before running a monitor. It refuses to change an existing ledger. Expected and actual verdicts remain separate. `run.sh` replaces primary raw results on a rerun; preserve `results/`, `artifacts/`, `tables/` and `metadata/` elsewhere first if retaining multiple measurement sessions. The original fixture and case generator document the declared teacher-error rubric. No seed is needed because generation uses no randomness.

## Inputs and execution

- [fixtures/exercise.musicxml](fixtures/exercise.musicxml) is the original eight-note exercise; [fixtures/interpretation.md](fixtures/interpretation.md) explains pitches, marks, timing, teacher-error labels and all manual predictions. A separate `exercise-final-marked.musicxml` tests the final marked-note defect without modifying the original exercise.
- Each `artifacts/behaviour/<case>/` contains MIDI, decoded browser events, actual browser-conversion output, complete service input, enriched JSONL and detailed actual results. The 27 main cases plus one defect diagnostic cover every requested category.
- `artifacts/workloads/score-216/` and `score-2324/` contain the same intermediate artefacts for the repository scores, including parsed score models. Filenames, full SHA-256 hashes, raw XML counts and actual parsed counts are in [results/workloads.json](results/workloads.json).
- The existing browser export `toPerformance` is transpiled from its actual source and invoked as a full module. React hooks and network access are disabled, and the unrelated Vite environment object is stubbed. This exercises conversion, without claiming to exercise browser capture or the React lifecycle.

Synthetic timestamps already have the intended score-time origin. The live `useMidi` stream forwards device-event timestamps, `ScorePage` supplies the recording directly to `useVerdict`, and `toPerformance` retains those timestamps; none of these functions explicitly rebases to playback start. The experiments therefore leave the live capture/playback clock relationship unvalidated.

For the timing workloads, onsets use the implementation's own `ScoreModel.ms_at` map with `tempo_factor=1`. This deliberately **does not independently validate alignment**. Onsets are rounded to the nearest 0.5 ms. Staccato notes last half the gap to the next distinct score onset; tenuto/legato notes last 90% of that gap; unmarked notes last 80% of their mapped written duration. The final attack uses its mapped written duration as the gap. Durations are rounded to 0.5 ms with a 0.5 ms minimum. Explicit dynamics use the nearest integer target (Python's ties-to-even rounding); otherwise velocity is 80. Each parsed pedal span gets CC64=127 at mapped start +10 ms and CC64=0 at mapped end. No input is adjusted in response to monitor outcomes. MIDI is encoded at 1,000 ticks per quarter with 500,000 microseconds per quarter: 0.5 ms per tick. Its tempo is an encoding timebase; the score's own variable timing map already determined the absolute MIDI times. Actual browser FIFO pairing is retained if repeated pitches overlap.

## Timing boundary and sampling

The total is measured with `time.perf_counter_ns()` immediately around the unchanged local `server.analyse(body)` call. It includes validation, temporary MusicXML creation, Partitura parsing, score/performance enrichment, JSONL serialisation and writing, fresh Prolog startup, specification loading, seven sequential checks, verdict decoding and temporary-file cleanup. It excludes Python module import/startup, input JSON loading, MIDI encoding/decoding, browser conversion/capture, HTTP/JSON transport and response rendering, and ahead-of-time RML compilation.

The two workloads run in fixed order (2,324 then 216 notes), sequentially in one Python process. Each has exactly three warm-up calls followed by 30 measured calls. The first warm-up runs without stage wrappers; the second checks that wrapper delegation preserves success, verdicts and every enriched event. Every measured call has delegating timers for parsing, enrichment, `to_jsonl` and the Prolog subprocess interval. The latter includes output capture and diagnostic decoding. Serialisation timing excludes file writing, which remains in the total. Outer total timing is measured separately; it is never reconstructed from component medians. Wrapper overhead and warning capture are included and not subtracted. Warnings are captured with an `always` filter for complete diagnostics.

Each request reparses the score and starts **one new SWI-Prolog process**, which loads/unloads the seven compiled modules and rewinds the trace for each. Python imports, libraries, allocator state and OS filesystem caches can remain warm. No CPU affinity, frequency control or exclusive machine reservation is imposed; numerical-library thread limits are one. These samples characterise this local analysis path under the observed conditions. A rejecting monitor may stop early, so they establish neither worst-case cost nor real-time guarantees, general scalability, independent alignment accuracy or user-facing latency.

## Raw results, diagnostics and provenance

`results/timings.jsonl` contains all 66 calls, including warm-ups, total/stage times, warnings, complete Prolog output and per-metric exits. `timings.csv` provides the timing/verdict columns. `summary.json`, Markdown and LaTeX tables are generated from those raw files. Quartiles use NumPy's linear percentile interpolation. No outlier or failed run is silently discarded. Exit 0 means acceptance, 1 rejection, and 2 monitor error; Python request completion is counted separately from monitor acceptance.

`diagnose.py` invokes the original standalone monitor on the saved workload traces to locate early syncopated-pedal rejection; exact commands and printed diagnostics are in `diagnostics/early-rejection.json`. These diagnostic calls are separate from the timed batch path. To build the optional three-page PDF with the evaluation section and full behavioural matrix, run `bash evaluation/scripts/build-paper.sh` (requires pdfLaTeX); output is `artifacts/paper/paper-preview.pdf`.

[metadata/provenance-before.json](metadata/provenance-before.json) records the initial 100-file manifest and Git limitation: the project's accessible `.git` directory is empty, and `git` resolves to an unrelated parent repository. That parent's commit is explicitly **not** a Cadenza commit. A project commit and previous project working-tree diff therefore cannot be established here; content hashes anchor the evaluated snapshot. `check.py` verifies that all 99 original source/input files outside Python caches are unchanged and independently recomputes the table statistics and saved verdicts. One existing generated `join.cpython-311.pyc` cache was regenerated during fixture inspection; its before/after hashes are reported in `results/checks.json`. Reproduction scripts disable further bytecode writes.

[diagnostics/harness-attempt-01/](diagnostics/harness-attempt-01/) preserves the initial evaluation-wrapper failure: the subprocess proxy omitted `PIPE`, so 28 calls failed before any monitor ran. The wrapper was corrected; sources, inputs and frozen expectations were retained. These are harness diagnostics, kept separately from the successful behavioural evaluation and timing dataset. Initial restricted-network installation failures and subsequent successful dependency-install logs are also retained in `metadata/`.
