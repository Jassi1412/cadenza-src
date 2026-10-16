# Local evaluation report for the Cadenza paper

The evaluation executed 28 synthetic behavioural cases and 66 sequential service calls for timing (three warm-ups and 30 measured calls on each of two repository scores). All seven original RML specifications were compiled and exercised. There were 0 differences from the manually frozen expected verdict sets. This agreement includes an anticipated runtime error, so it is not a claim that every case completed all monitors successfully or that Cadenza detects every musical error.

The measured median analysis costs were **0.703565 s for 216 parsed notes** and **5.788159 s for 2,324 parsed notes**. These are new local measurements. The earlier draft's timings were not used as inputs, baselines or targets.

## Questions and method

We asked (1) which requirements the current implementation actually observes, (2) whether manually reasoned synthetic cases distinguish its boundaries and limitations, and (3) what its local analysis path costs on the two repository scores. Source inspection preceded fixture construction. Expected verdicts for every metric were saved before successful monitor execution and are retained separately from actual results. Teacher-error labels use the explicit exercise rubric, rather than opinions collected from teachers. There are no pianist recordings or user-study participants.

The original eight-note MusicXML exercise includes a two-note chord, mf/f dynamics, staccato, tenuto and a pedal span. Cases cover baseline, wrong pitch, pitch outside the piano range, wrong velocity, wrong duration, 29/30/31 ms chord spread, pedal endpoint association at 24/25/26 ms and around the nominal 125 ms window, omitted and duplicate notes, omitted pedal release, pre-attack pedal, absent pedal, delayed pedal, and adjacent dynamics/articulation boundaries. A separate final-marked exercise tests the null-gap defect. [The frozen ledger](results/expected-verdicts.json) explains each case and every per-specification expectation.

MIDI was generated and decoded deterministically at 0.5 ms resolution. Decoded events passed through the actual exported browser `toPerformance` function, followed by the byte-identical service implementation and compiled specifications. The browser module's unrelated Vite environment was stubbed; React hooks and network access were disabled. Browser MIDI capture and lifecycle are outside this evaluation. Synthetic timestamps already have the intended score-time origin; the live capture/conversion path has no explicit playback-start rebasing, so live timestamp-origin alignment remains unvalidated. Workload onsets use Cadenza's own score-to-time map; consequently, this is not independent alignment validation. Durations, integer velocities and pedal generation are specified exactly in [README.md](README.md), and every intermediate input and enriched trace is saved.

## What the behavioural evidence establishes

The baseline is accepted by all seven metrics. Wrong pitch, out-of-range pitch, dynamics and articulation violations produce the predicted rejections. Chord jitter accepts 29 ms and rejects 30/31 ms, confirming its strict inequality for this fixture. Staccato at 375 ms and tenuto at 375 ms accept; tenuto at 374 ms rejects. The mf target is 71.5 with an inclusive +/-8 band; integer velocity 64 accepts and 80 rejects.

Pedal-toggle accepts a press or late release at +25 ms but rejects +26 ms in this fixture. This is the composed effect of the enrichment layer's 0.05-beat association/snap window at 120 BPM, which is tighter than the RML's nominal 0.25-beat (125 ms) constraint. Presses at 124/125 ms are inside the declared teacher tolerance but rejected because no explicit boundary is associated. Exact physical thresholds can depend on tempo, floating-point snapping and score-map clamping; these observations do not establish a universal 25 ms threshold.

The missing-note and duplicate-note cases are accepted by every metric. They expose the absence of a general score-coverage or one-to-one matching obligation. A 300 ms delayed pedal press passes syncopated-pedal because it checks event order without a numerical deadline; pedal-toggle rejects it. A pre-attack press fails syncopated-pedal. Missing release fails pedal-toggle but passes syncopated-pedal. With all pedal events absent, pedal-toggle passes vacuously while syncopated-pedal rejects. These are separate, local obligations.

The final marked note produces articulation exit 2, with `type_error(clpr_expression,null)` on stderr. Its next-attack gap is null and the compiled arithmetic is attempted before the no-gap alternative. The other six metrics accept. The service still returns normally and Prolog's batch process returns zero, so raw per-metric codes and captured stderr are necessary to see this error. No specification or application repair was applied, and no corrected variant is mixed into the results.

Of 15 teacher-error-labelled cases, 2 are accepted by all metrics (missing_note, duplicate_note). 5 cases labelled without a teacher error fail to obtain all acceptances (pedal_press_26ms, pedal_press_124ms, pedal_press_125ms, pedal_release_late_26ms, final_marked_note); these reflect tighter composed pedal checks or the final-note runtime defect. The full expected/actual matrix is in [RESULTS.md](RESULTS.md). Matching all manual predictions is evidence for the inspected semantics on these cases, not overall musical correctness.

## Local cost results

| Parsed notes | MIDI/enriched events | Warm-ups | Measured | Median (s) | Q1 (s) | Q3 (s) | Min (s) | Max (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 216 | 464 | 3 | 30 | 0.703565 | 0.688775 | 0.726932 | 0.674853 | 0.776490 |
| 2324 | 4946 | 3 | 30 | 5.788159 | 5.689245 | 5.820485 | 5.579121 | 6.109774 |

Quartiles use linear interpolation, with every measured duration retained. No outliers or failures were discarded. The 216-note score generated 464 MIDI/enriched events, including 32 controls; the 2,324-note score generated 4946 events, including 298 controls. The larger XML has 2,418 pitched noteheads and 94 tie starts/stops; the implementation's tied-note interpretation yields 2,324 parsed notes. The smaller XML has 216 pitched notes and no ties. Full filenames and SHA-256 hashes are retained in [workloads.json](results/workloads.json).

| Metric | 216-note measured runs | 2,324-note measured runs |
|---|---|---|
| articulation | exit 0: 30 | exit 0: 30 |
| chord-jitter | exit 0: 30 | exit 0: 30 |
| dynamics-adherence | exit 0: 30 | exit 0: 30 |
| pedal-toggle | exit 0: 30 | exit 0: 30 |
| pitch-agreement | exit 0: 30 | exit 0: 30 |
| pitch-range | exit 0: 30 | exit 0: 30 |
| syncopated-pedal | exit 1: 30 | exit 1: 30 |

Across the 60 measured calls there were 0 Python service failures, 0 timeouts and 0 calls with monitor exit 2. Acceptance/rejection outcomes above must be considered with the timings: any rejecting monitor may stop before consuming the whole trace. We do not describe these as worst-case or uniformly all-conforming costs.

Separate diagnostic calls to the original standalone monitor locate syncopated-pedal rejection at event **28/464** in the smaller trace and **29/4946** in the larger trace. These calls use the same compiled specification and transition semantics as the timed batch path; they are excluded from timing samples. In these traces, a boundary attack is ordered before the release of the preceding pedal span at the same timestamp. The existing region greedily consumes the attack; release ends it, leaving the subsequent press without a fresh preceding pedal-marked attack. Exact commands, trace/specification hashes and printed rejection diagnostics are in [diagnostics/early-rejection.json](diagnostics/early-rejection.json). The generated event ordering and original specifications were retained.

The smaller score emitted 1 parsing warning occurrence during generation and 30 across its measured calls; the larger emitted 24 during generation and 720 across measured calls. Warnings concern ignored metronome directions, unsupported textual directions and, in the larger score, an unmatched pedal stop. Exact messages, repetition counts and all Prolog stderr are preserved. The compiled pedal-toggle module also emits a singleton-variable warning. Warnings were retained, not silently repaired or suppressed. [RESULTS.md](RESULTS.md) includes component medians and all warning messages.

## Timing boundary and environment

`perf_counter_ns` measures each total directly around the actual `server.analyse` call: input validation, temporary score creation, parsing, matching/enrichment, JSONL conversion and writing, fresh Prolog startup, seven sequential checks, verdict decoding and cleanup. HTTP transport, request JSON loading, browser capture/conversion, MIDI decoding, rendering, Python import/startup and ahead-of-time compilation are excluded. Component timers delegate to unchanged functions. Serialisation timing covers conversion, with file writing remaining in the total. The subprocess interval includes startup, specification loading/checks, output capture and diagnostic decoding. Component medians are never added to estimate a total. Timer-wrapper and warning-capture overhead is included, without subtraction.

Measurements ran on 14 October 2026 from 13:12:24 CEST to 13:16:03 CEST on Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz, 15.51 GiB reported RAM, Linux 6.8.0-138-generic, Python 3.11.0rc1, Partitura 1.9.0, NumPy 1.26.4, SciPy 1.17.1, lxml 6.1.3, mido 1.3.3 and SWI-Prolog 9.1.21. Java 21.0.12.1 compiled the vendored RML compiler output; Node 20.15.0 and TypeScript 6.0.2 ran browser conversion. Resource limits, CPU affinity, package inventory and original hashes are recorded in [metadata/](metadata/). The local Python release candidate differs from the Docker image's Python 3.12.

Workloads ran sequentially in fixed order, 2,324 then 216 notes, with one numerical-library thread. Every request reparses its score and starts a fresh Prolog process; the same Python process, imported libraries, allocator and OS caches remain warm. The first of three warm-ups is uninstrumented, and the second checks that delegation preserves success, verdicts and the entire trace. There is no extra preflight request. CPU frequency, background activity and caches were not controlled, and the machine was not reserved exclusively.

## Provenance, checks and scope of claims

The accessible project `.git` is empty and Git resolves to an unrelated parent repository. A Cadenza commit or previous project diff could not be recovered, and the parent's commit is not attributed to Cadenza. A 100-file initial SHA-256 manifest anchors the snapshot; final checks verify all 99 original source/input files outside Python caches are unchanged. One existing generated `join.cpython-311.pyc` cache was regenerated during fixture inspection; its before/after hashes are retained in `results/checks.json`. Reproduction scripts disable further bytecode writes. Evaluation additions remain under `evaluation/`.

An initial harness attempt failed before Prolog because the subprocess proxy omitted `PIPE`. All 28 failed harness calls are preserved under [diagnostics/harness-attempt-01/](diagnostics/harness-attempt-01/). The evaluation wrapper was fixed and the same frozen expectations and inputs were used for the successful run. These harness-only failures are separate from the primary correctness and timing datasets. Dependency installation initially failed under restricted DNS, then succeeded in the isolated environment; logs are retained.

`check.py` independently recomputes timing statistics, verifies exactly three warm-ups and 30 measured runs per workload, checks every saved expected/actual verdict against the frozen ledger and detailed artefact, and verifies input and original-file hashes. Generated Markdown and LaTeX tables share the same raw-derived summary. The evidence supports the stated local predicates, specific observed limitations/defect, and local analysis costs on these two synthetic workloads. It does not establish independent score alignment accuracy, human assessment, general completeness, scalability, worst-case bounds, real-time guarantees or end-to-end user-facing latency.

As a separate reproducibility check, generation was repeated after retaining the original hashes: all 157 generated artefacts compared byte-for-byte equal, including MIDI, decoded browser events, conversion outputs, service inputs, score models, manifests and the unchanged expectation ledger. Actual verdicts and timing samples were left intact; [results/determinism.json](results/determinism.json) records this check.

Reproduction commands are in [README.md](README.md); the paper section is [evaluation.tex](evaluation.tex).
