# Repaired Cadenza evaluation for the paper

The final-note articulation exception was eliminated. Across the original **28 cases and 196 metric verdicts**, the only observed change was `final_marked_note` articulation: exit 2 (error) became exit 0 (acceptance under the existing no-gap exemption). The other 195 verdicts were unchanged. All cases matched the separately frozen repaired expectations. A further **29 focused regression checks** matched their expectations (18 direct monitor, 11 complete conversion/service).

New median local analysis costs were **0.779284 s for 216 parsed notes** and **6.037239 s for 2,324 parsed notes**. Both workload traces still reject `syncopated-pedal`; these are costs of the actual rejecting analysis path. Earlier timings were archived and were not reused as samples or targets. The repaired data are ready to replace the previous paper evaluation, subject to the stated scope and remaining limitations.

## Evidence preserved and repair

[The original evaluation archive](archive/v1-original/evaluation/REPORT.md) preserves the previous raw results, metadata, frozen ledger, diagnostics, compiled specifications and reports; `archive/v1-original/MANIFEST.json` records its contents. [Repair provenance](metadata/repair-provenance.json) records the original/repaired content hashes and Git state. Usable Cadenza Git history remains unavailable: the accessible project `.git` is empty, and Git resolves to an unrelated parent. Its commit is not attributed to Cadenza.

The original failing service input was [rerun before repair](diagnostics/null-gap-original-reproduction.json) and reproduced `type_error(clpr_expression,null)`. Enrichment intentionally supplies `gapMs: null` when there is no next distinct performed attack. In the original RML choice, the marked-note numeric predicate was tried before `noGap`; compiled Prolog therefore sent `null` to CLP(R) multiplication before reaching the exemption. This is an unsafe specification ordering exposed by the generated code; the compiler faithfully preserved that order.

The source change is limited to `rml/metrics/articulation.rml`: the existing `noGap` alternative moves before all arithmetic alternatives in `Main`. The vendored compiler regenerated the monitor; source/generated hashes and exact compiler commands are retained in [metadata/compilation.json](metadata/compilation.json), [executed commands](metadata/executed-commands-v2.json) record the evaluation commands, and [repair.diff](metadata/repair.diff) shows the application/specification diff. The compiler and service matching code were unchanged. Numeric constraints remain staccato duration ≤0.75 × gap and tenuto/legato duration ≥0.75 × gap. A no-gap acceptance states that this duration requirement is **inapplicable**; it does not verify the final note's duration. Pitch matching, score coverage and pedal policies were not changed.

## Behaviour and regressions

The original [expectation ledger](results/expected-verdicts.json) is preserved byte-for-byte. [Version 2](results/expected-verdicts-v2.json), frozen before repaired execution, changes only the expected articulation error for `final_marked_note` to no-gap acceptance. Its other six expectations and all other cases are unchanged. Teacher-error labels follow the declared synthetic exercise rubric; they are not ratings collected from teachers.

| Case | Metric | Archived exit | Repaired exit |
|---|---|---:|---:|
| final_marked_note | articulation | 2 | 0 |

[The exhaustive comparison](results/behaviour-comparison.json) checks every old/new case-metric outcome and confirms identical original suite inputs. [RESULTS.md](RESULTS.md) and [tables/behaviour.tex](tables/behaviour.tex) contain the new 28-case expected/actual matrix; exits 0, 1 and 2 mean acceptance, rejection and monitor error, respectively. Request completion is counted separately. There were 0 prediction discrepancies, 0 service failures and 0 cases with monitor errors.

The separately identifiable [focused regressions](results/regressions.json) compare original and regenerated RML monitors using [manual expectations](results/regression-expected-v2.json) frozen before those runs. The 18 direct fixtures cover null-gap final staccato, tenuto and legato events, an unmarked final event, numeric durations below/at/above the 0.75 boundary, and earlier genuine violations followed by null-gap events. The 11 complete-path fixtures also exercise MIDI decoding, the actual browser converter, score enrichment and service monitoring wherever the importer produces the relevant mark. The importer emits staccato and tenuto; literal `legato` is covered at the direct monitor boundary only. Earlier violations still reject, so the final-event exemption does not erase previous failures. Two deliberately malformed numeric fixtures retain monitor exit 2, confirming that arbitrary arithmetic errors are not converted into acceptance. All 29 checks matched the manual regression expectations.

The readable original/repaired regression matrix is [REGRESSIONS.md](REGRESSIONS.md), with per-case links to inputs and raw evidence.

The repaired baseline passes all seven metrics. The existing boundary cases retain their outcomes: chord spread 29 ms accepts and 30/31 ms reject; staccato and tenuto at the inclusive 375 ms boundary accept, while tenuto at 374 ms rejects. The mf target is 71.5 with an inclusive ±8 band: integer velocity 64 accepts and 80 rejects. Wrong pitch, out-of-range pitch, wrong velocity and applicable duration violations still reject as predicted.

## Remaining assessment limitations

The missing-note and duplicate-note cases still pass all seven metrics. The trace has no independent event for each unfulfilled score obligation, and pitch matching is not a one-to-one score/performance assignment. The repair therefore supplies no general completeness guarantee. Of 15 rubric-labelled error cases, 2 pass all metrics (missing_note, duplicate_note). 4 cases labelled without a teacher error fail to obtain every acceptance (pedal_press_26ms, pedal_press_124ms, pedal_press_125ms, pedal_release_late_26ms), owing to the tighter composed pedal association. The archived final-note error is no longer among them.

Pedal-toggle still accepts a press or late release at +25 ms and rejects +26 ms for this 120 BPM fixture. Enrichment associates/snaps endpoints within 0.05 beat, tighter than the RML's nominal 0.25-beat (125 ms) assessment tolerance; presses at 124/125 ms therefore reject despite lying within the declared teacher tolerance. Floating-point comparisons, tempo and score-map clamping affect the effective boundary. These cases do not establish a universal 25 ms threshold.

Syncopated-pedal still checks order without a numerical deadline: a 300 ms delayed press passes that metric but fails pedal-toggle; a pre-attack press fails syncopated-pedal. Missing release fails pedal-toggle but passes syncopated-pedal. With every pedal event absent, pedal-toggle accepts vacuously while syncopated-pedal rejects. These policies are unchanged.

## New local execution costs

| Parsed notes | Enriched events | Warm-ups | Measured | Median (s) | Q1 (s) | Q3 (s) | Min (s) | Max (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 216 | 464 | 3 | 30 | 0.779284 | 0.758785 | 0.799557 | 0.726207 | 0.868918 |
| 2324 | 4946 | 3 | 30 | 6.037239 | 5.956440 | 6.375752 | 5.754788 | 6.750570 |

Each workload received three warm-ups followed by 30 measured calls. All 60 measured samples contribute to the statistics; quartiles use linear interpolation and no outlier is discarded. Across these calls there were 0 service failures, 0 timeouts and 0 calls with monitor exit 2. [timings.jsonl](results/timings.jsonl) retains all 66 calls, including warnings, complete verdicts and subprocess output; [timings.csv](results/timings.csv) retains the tabular samples. [summary.json](results/summary.json) and all displayed statistics are generated from this new raw data.

| Metric | 216-note measured calls | 2,324-note measured calls |
|---|---|---|
| articulation | exit 0: 30 | exit 0: 30 |
| chord-jitter | exit 0: 30 | exit 0: 30 |
| dynamics-adherence | exit 0: 30 | exit 0: 30 |
| pedal-toggle | exit 0: 30 | exit 0: 30 |
| pitch-agreement | exit 0: 30 | exit 0: 30 |
| pitch-range | exit 0: 30 | exit 0: 30 |
| syncopated-pedal | exit 1: 30 | exit 1: 30 |

The 216-note score produces 464 decoded/enriched events (32 controls), and the 2,324-note score produces 4,946 events (298 controls). The larger XML contains 2,418 pitched noteheads and 94 tie starts/stops; actual parsing yields 2,324 sounding notes. Input SHA-256 hashes and event counts match the archived workloads; [workloads.json](results/workloads.json) records full filenames, hashes and parser counts.

The other six metrics accept on every measured workload call; syncopated-pedal rejects on both. Separate [standalone-monitor diagnostics](diagnostics/early-rejection.json), excluded from timing, locate rejection at event **28/464** and **29/4946**. At adjacent pedal spans, a boundary attack is consumed by the preceding region before its release; the following press lacks a fresh preceding marked attack. Rejecting monitors can stop early. The costs therefore do not represent seven fully accepting checks or worst-case trace consumption.

Warning occurrences numbered 1 during small-score generation and 24 during large-score generation, with 30 and 720 occurrences across their measured calls. Ignored metronome/unsupported text directions, the larger score's unmatched pedal stop and Prolog's pedal-toggle singleton-variable warning remain visible. Exact warnings and component statistics are in [RESULTS.md](RESULTS.md). No warnings were silently suppressed or repaired.

## Boundary, environment and reproduction

`time.perf_counter_ns()` measures the total immediately around the actual local `server.analyse(body)` call. This includes validation, temporary MusicXML creation, parsing, matching/enrichment, JSONL serialisation and writing, fresh Prolog startup, specification loading, seven sequential checks, verdict decoding and cleanup. It excludes Python import/startup, input JSON loading, MIDI encoding/decoding, browser capture/conversion, HTTP transport, rendering and ahead-of-time compilation. Delegating component timers and warning capture retain their overhead; serialisation excludes file writing, which remains in the total. Component medians are not summed to estimate a total.

Calls ran sequentially in fixed order (2,324 then 216 notes) in one Python process. Every call reparsed its score and started one fresh Prolog process; imports, allocator state and OS caches could remain warm. Numerical-library thread limits were one. The first warm-up was uninstrumented; the second checked that delegation preserved success, verdicts and every enriched event. CPU affinity/frequency and background activity were not controlled, and the machine was not reserved exclusively.

The new calls ran on 14 October 2026, 15:45:11 CEST–15:49:06 CEST, using Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz, 15.51 GiB reported RAM and Linux 6.8.0-138-generic. The recorded environment used Python 3.11.0rc1, Partitura 1.9.0, NumPy 1.26.4, SciPy 1.17.1, lxml 6.1.3, mido 1.3.3; runtime records report swipl: SWI-Prolog version 9.1.21 for x86_64-linux; java: openjdk version "21.0.12.1" 2026-08-18; node: v20.15.0. Full versions, CPU/resource information and thread settings are in [environment.json](metadata/environment.json); exact compilation and execution commands accompany the reproduction scripts. The local Python version differs from the Docker image's Python 3.12.

All service-path performances use deterministic synthetic MIDI at 0.5 ms resolution, with every original input and intermediate trace retained. They pass through the actual browser `toPerformance` export and unchanged service functions; direct monitor fixtures instead supply enriched JSONL events. Workload onsets depend on Cadenza's own timing map, so this does not independently validate alignment. Synthetic timestamps already use the intended score-time origin; browser capture/React lifecycle and the live capture/playback timestamp-origin relationship remain unvalidated. There are no pianist recordings or user-study participants.

[README.md](README.md) gives exact reproduction commands and [IMPLEMENTATION.md](IMPLEMENTATION.md) documents the observed semantics. The new concise British English section is [evaluation.tex](evaluation.tex). The preserved archive also contains the previous harness-only failures, installation diagnostics and determinism evidence; they are not new repaired-version observations. Hash and verdict checks retain the distinction between the intended source change and unrelated files.

The evidence supports elimination of the reproduced null-gap exception, preserved numeric articulation boundaries, unchanged other suite verdicts, and local costs for these two workloads. It does not establish general musical completeness, independent live alignment accuracy, scalability, real-time guarantees or end-to-end user latency. The repaired data are ready to replace the previous paper evaluation, subject to the stated scope and remaining limitations.
