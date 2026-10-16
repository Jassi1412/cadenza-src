#!/usr/bin/env python3
"""Render the factual report and British English paper section from checked raw data."""
import datetime
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

EVAL = Path(__file__).resolve().parents[1]
METRICS = ('articulation', 'chord-jitter', 'dynamics-adherence', 'pedal-toggle',
           'pitch-agreement', 'pitch-range', 'syncopated-pedal')


def read(name):
    return json.loads((EVAL / name).read_text())


def main():
    summary = read('results/summary.json')
    behaviour = read('results/behaviour.json')['cases']
    env = read('metadata/environment.json')
    timings = [json.loads(s) for s in (EVAL / 'results/timings.jsonl').read_text().splitlines()]
    rejection_data = read('diagnostics/early-rejection.json')
    rejections = {r['workload']: r for r in rejection_data['workloads']}
    workloads = sorted(summary['workloads'], key=lambda w: w['note_count'])
    small, large = workloads
    b = summary['behaviour']
    rows = []
    for w in workloads:
        rows.append('| ' + ' | '.join([str(w['note_count']), str(w['event_count']),
                    str(w['warmup_count']), str(w['measured_count'])] +
                    [f"{w[k]:.6f}" for k in ('median', 'q1', 'q3', 'min', 'max')]) + ' |')
    table = ('| Parsed notes | MIDI/enriched events | Warm-ups | Measured | Median (s) | Q1 (s) | Q3 (s) | Min (s) | Max (s) |\n'
             '|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n' + '\n'.join(rows))
    outcome_rows = []
    for m in METRICS:
        cells = []
        for w in workloads:
            counts = w['outcomes'][m]
            cells.append(', '.join(f"exit {code}: {n}" for code, n in counts.items() if n))
        outcome_rows.append('| ' + ' | '.join([m] + cells) + ' |')
    outcome_table = '| Metric | 216-note measured runs | 2,324-note measured runs |\n|---|---|---|\n' + '\n'.join(outcome_rows)
    start = min(r['started_utc'] for r in timings)
    endrow = max(timings, key=lambda r: r['started_utc'])
    start_local = datetime.datetime.fromisoformat(start).astimezone(ZoneInfo('Europe/Rome'))
    end_local = (datetime.datetime.fromisoformat(endrow['started_utc']) + datetime.timedelta(seconds=endrow['total_seconds'])).astimezone(ZoneInfo('Europe/Rome'))
    ram_kib = int(env['proc_and_cgroup']['/proc/meminfo'].splitlines()[0].split()[1])
    ram_gib = ram_kib / 1024**2
    cpu = next(line.split(':', 1)[1].strip() for line in env['proc_and_cgroup']['/proc/cpuinfo'].splitlines() if line.startswith('model name'))
    false_rejections = [r['name'] for r in behaviour if not r['teacher_error'] and any(c != 0 for c in r['actual'].values())]
    failures = sum(w['service_failures'] for w in workloads)
    timeouts = sum(w['timeouts'] for w in workloads)
    mon_errors = sum(w['monitor_error_runs'] for w in workloads)
    discrepancies = b['discrepancy_case_count']
    report = f'''# Local evaluation report for the Cadenza paper

The evaluation executed {b['case_count']} synthetic behavioural cases and {len(timings)} sequential service calls for timing (three warm-ups and 30 measured calls on each of two repository scores). All seven original RML specifications were compiled and exercised. There were {discrepancies} differences from the manually frozen expected verdict sets. This agreement includes an anticipated runtime error, so it is not a claim that every case completed all monitors successfully or that Cadenza detects every musical error.

The measured median analysis costs were **{small['median']:.6f} s for 216 parsed notes** and **{large['median']:.6f} s for 2,324 parsed notes**. These are new local measurements. The earlier draft's timings were not used as inputs, baselines or targets.

## Questions and method

We asked (1) which requirements the current implementation actually observes, (2) whether manually reasoned synthetic cases distinguish its boundaries and limitations, and (3) what its local analysis path costs on the two repository scores. Source inspection preceded fixture construction. Expected verdicts for every metric were saved before successful monitor execution and are retained separately from actual results. Teacher-error labels use the explicit exercise rubric, rather than opinions collected from teachers. There are no pianist recordings or user-study participants.

The original eight-note MusicXML exercise includes a two-note chord, mf/f dynamics, staccato, tenuto and a pedal span. Cases cover baseline, wrong pitch, pitch outside the piano range, wrong velocity, wrong duration, 29/30/31 ms chord spread, pedal endpoint association at 24/25/26 ms and around the nominal 125 ms window, omitted and duplicate notes, omitted pedal release, pre-attack pedal, absent pedal, delayed pedal, and adjacent dynamics/articulation boundaries. A separate final-marked exercise tests the null-gap defect. [The frozen ledger](results/expected-verdicts.json) explains each case and every per-specification expectation.

MIDI was generated and decoded deterministically at 0.5 ms resolution. Decoded events passed through the actual exported browser `toPerformance` function, followed by the byte-identical service implementation and compiled specifications. The browser module's unrelated Vite environment was stubbed; React hooks and network access were disabled. Browser MIDI capture and lifecycle are outside this evaluation. Synthetic timestamps already have the intended score-time origin; the live capture/conversion path has no explicit playback-start rebasing, so live timestamp-origin alignment remains unvalidated. Workload onsets use Cadenza's own score-to-time map; consequently, this is not independent alignment validation. Durations, integer velocities and pedal generation are specified exactly in [README.md](README.md), and every intermediate input and enriched trace is saved.

## What the behavioural evidence establishes

The baseline is accepted by all seven metrics. Wrong pitch, out-of-range pitch, dynamics and articulation violations produce the predicted rejections. Chord jitter accepts 29 ms and rejects 30/31 ms, confirming its strict inequality for this fixture. Staccato at 375 ms and tenuto at 375 ms accept; tenuto at 374 ms rejects. The mf target is 71.5 with an inclusive +/-8 band; integer velocity 64 accepts and 80 rejects.

Pedal-toggle accepts a press or late release at +25 ms but rejects +26 ms in this fixture. This is the composed effect of the enrichment layer's 0.05-beat association/snap window at 120 BPM, which is tighter than the RML's nominal 0.25-beat (125 ms) constraint. Presses at 124/125 ms are inside the declared teacher tolerance but rejected because no explicit boundary is associated. Exact physical thresholds can depend on tempo, floating-point snapping and score-map clamping; these observations do not establish a universal 25 ms threshold.

The missing-note and duplicate-note cases are accepted by every metric. They expose the absence of a general score-coverage or one-to-one matching obligation. A 300 ms delayed pedal press passes syncopated-pedal because it checks event order without a numerical deadline; pedal-toggle rejects it. A pre-attack press fails syncopated-pedal. Missing release fails pedal-toggle but passes syncopated-pedal. With all pedal events absent, pedal-toggle passes vacuously while syncopated-pedal rejects. These are separate, local obligations.

The final marked note produces articulation exit 2, with `type_error(clpr_expression,null)` on stderr. Its next-attack gap is null and the compiled arithmetic is attempted before the no-gap alternative. The other six metrics accept. The service still returns normally and Prolog's batch process returns zero, so raw per-metric codes and captured stderr are necessary to see this error. No specification or application repair was applied, and no corrected variant is mixed into the results.

Of {b['teacher_error_case_count']} teacher-error-labelled cases, {b['teacher_error_cases_accepted_by_all']} are accepted by all metrics ({', '.join(b['teacher_error_cases_accepted_by_all_names'])}). {len(false_rejections)} cases labelled without a teacher error fail to obtain all acceptances ({', '.join(false_rejections)}); these reflect tighter composed pedal checks or the final-note runtime defect. The full expected/actual matrix is in [RESULTS.md](RESULTS.md). Matching all manual predictions is evidence for the inspected semantics on these cases, not overall musical correctness.

## Local cost results

{table}

Quartiles use linear interpolation, with every measured duration retained. No outliers or failures were discarded. The 216-note score generated {small['event_count']} MIDI/enriched events, including {small['control_change_count']} controls; the 2,324-note score generated {large['event_count']} events, including {large['control_change_count']} controls. The larger XML has 2,418 pitched noteheads and 94 tie starts/stops; the implementation's tied-note interpretation yields 2,324 parsed notes. The smaller XML has 216 pitched notes and no ties. Full filenames and SHA-256 hashes are retained in [workloads.json](results/workloads.json).

{outcome_table}

Across the 60 measured calls there were {failures} Python service failures, {timeouts} timeouts and {mon_errors} calls with monitor exit 2. Acceptance/rejection outcomes above must be considered with the timings: any rejecting monitor may stop before consuming the whole trace. We do not describe these as worst-case or uniformly all-conforming costs.

Separate diagnostic calls to the original standalone monitor locate syncopated-pedal rejection at event **{rejections[small['name']]['unmatched_event_index']}/{small['event_count']}** in the smaller trace and **{rejections[large['name']]['unmatched_event_index']}/{large['event_count']}** in the larger trace. These calls use the same compiled specification and transition semantics as the timed batch path; they are excluded from timing samples. In these traces, a boundary attack is ordered before the release of the preceding pedal span at the same timestamp. The existing region greedily consumes the attack; release ends it, leaving the subsequent press without a fresh preceding pedal-marked attack. Exact commands, trace/specification hashes and printed rejection diagnostics are in [diagnostics/early-rejection.json](diagnostics/early-rejection.json). The generated event ordering and original specifications were retained.

The smaller score emitted {small['generation_warnings_count']} parsing warning occurrence during generation and {small['warnings_count']} across its measured calls; the larger emitted {large['generation_warnings_count']} during generation and {large['warnings_count']} across measured calls. Warnings concern ignored metronome directions, unsupported textual directions and, in the larger score, an unmatched pedal stop. Exact messages, repetition counts and all Prolog stderr are preserved. The compiled pedal-toggle module also emits a singleton-variable warning. Warnings were retained, not silently repaired or suppressed. [RESULTS.md](RESULTS.md) includes component medians and all warning messages.

## Timing boundary and environment

`perf_counter_ns` measures each total directly around the actual `server.analyse` call: input validation, temporary score creation, parsing, matching/enrichment, JSONL conversion and writing, fresh Prolog startup, seven sequential checks, verdict decoding and cleanup. HTTP transport, request JSON loading, browser capture/conversion, MIDI decoding, rendering, Python import/startup and ahead-of-time compilation are excluded. Component timers delegate to unchanged functions. Serialisation timing covers conversion, with file writing remaining in the total. The subprocess interval includes startup, specification loading/checks, output capture and diagnostic decoding. Component medians are never added to estimate a total. Timer-wrapper and warning-capture overhead is included, without subtraction.

Measurements ran on {start_local.strftime('%d %B %Y')} from {start_local.strftime('%H:%M:%S %Z')} to {end_local.strftime('%H:%M:%S %Z')} on {cpu}, {ram_gib:.2f} GiB reported RAM, Linux {env['uname'][2]}, Python 3.11.0rc1, Partitura {env['packages']['partitura']}, NumPy {env['packages']['numpy']}, SciPy {env['packages']['scipy']}, lxml {env['packages']['lxml']}, mido {env['packages']['mido']} and SWI-Prolog 9.1.21. Java 21.0.12.1 compiled the vendored RML compiler output; Node 20.15.0 and TypeScript 6.0.2 ran browser conversion. Resource limits, CPU affinity, package inventory and original hashes are recorded in [metadata/](metadata/). The local Python release candidate differs from the Docker image's Python 3.12.

Workloads ran sequentially in fixed order, 2,324 then 216 notes, with one numerical-library thread. Every request reparses its score and starts a fresh Prolog process; the same Python process, imported libraries, allocator and OS caches remain warm. The first of three warm-ups is uninstrumented, and the second checks that delegation preserves success, verdicts and the entire trace. There is no extra preflight request. CPU frequency, background activity and caches were not controlled, and the machine was not reserved exclusively.

## Provenance, checks and scope of claims

The accessible project `.git` is empty and Git resolves to an unrelated parent repository. A Cadenza commit or previous project diff could not be recovered, and the parent's commit is not attributed to Cadenza. A 100-file initial SHA-256 manifest anchors the snapshot; final checks verify all 99 original source/input files outside Python caches are unchanged. One existing generated `join.cpython-311.pyc` cache was regenerated during fixture inspection; its before/after hashes are retained in `results/checks.json`. Reproduction scripts disable further bytecode writes. Evaluation additions remain under `evaluation/`.

An initial harness attempt failed before Prolog because the subprocess proxy omitted `PIPE`. All 28 failed harness calls are preserved under [diagnostics/harness-attempt-01/](diagnostics/harness-attempt-01/). The evaluation wrapper was fixed and the same frozen expectations and inputs were used for the successful run. These harness-only failures are separate from the primary correctness and timing datasets. Dependency installation initially failed under restricted DNS, then succeeded in the isolated environment; logs are retained.

`check.py` independently recomputes timing statistics, verifies exactly three warm-ups and 30 measured runs per workload, checks every saved expected/actual verdict against the frozen ledger and detailed artefact, and verifies input and original-file hashes. Generated Markdown and LaTeX tables share the same raw-derived summary. The evidence supports the stated local predicates, specific observed limitations/defect, and local analysis costs on these two synthetic workloads. It does not establish independent score alignment accuracy, human assessment, general completeness, scalability, worst-case bounds, real-time guarantees or end-to-end user-facing latency.

As a separate reproducibility check, generation was repeated after retaining the original hashes: all 157 generated artefacts compared byte-for-byte equal, including MIDI, decoded browser events, conversion outputs, service inputs, score models, manifests and the unchanged expectation ledger. Actual verdicts and timing samples were left intact; [results/determinism.json](results/determinism.json) records this check.

Reproduction commands are in [README.md](README.md); the paper section is [evaluation.tex](evaluation.tex).
'''
    (EVAL / 'REPORT.md').write_text(report)
    tex = rf'''% Generated from retained local raw data by scripts/paper.py.
\section{{Experimental evaluation}}
\label{{sec:evaluation}}
We evaluated (i) the properties observed by the current implementation,
(ii) its behaviour on manually specified synthetic performances, and
(iii) the cost of its local analysis path. All performances were deterministic
synthetic MIDI, not pianist recordings or a user study. The earlier draft's
timings were not used as reference values or targets.

\paragraph{{Setup and provenance.}}
We compiled the seven unchanged RML specifications with the vendored compiler
and exercised the actual service and browser \texttt{{toPerformance}} export.
The service files were staged byte-for-byte in the existing Docker layout;
application code and specifications were not repaired. The accessible project
Git metadata did not identify a Cadenza commit, so SHA-256 manifests identify
the evaluated sources and inputs. The experiments ran on {start_local.strftime('%d %B %Y')},
on an Intel Core i7-7700HQ (2.80\,GHz; four cores/eight logical processors),
with {ram_gib:.2f}\,GiB reported RAM and Linux {env['uname'][2]}.
The isolated environment used Python 3.11.0rc1, Partitura 1.9.0,
NumPy 1.26.4, SciPy 1.17.1, lxml 6.1.3, mido 1.3.3 and SWI-Prolog 9.1.21.
Complete runtime versions, resource limits and dependency inventories are retained.
Numerical-library thread limits were one; CPU frequency and background load
were not controlled.

\paragraph{{Behaviour.}}
An original eight-note MusicXML exercise contains a two-note chord, dynamics,
staccato, tenuto and a pedal span. We froze manually reasoned per-specification
verdicts before execution, separately labelling musical errors under a declared
exercise rubric. Across {b['case_count']} cases there were {discrepancies} deviations from these predictions,
including one predicted articulation runtime error. The baseline was accepted
by all seven metrics. Wrong pitch, out-of-range pitch, velocity and duration
cases were rejected as predicted. Chord spread of 29\,ms was accepted and
30/31\,ms rejected. At 120 beats per minute, the composed pedal-boundary
association accepted +25\,ms and rejected +26\,ms for this fixture, despite
the RML's nominal 0.25-beat tolerance. Missing and duplicate-note cases were
accepted by all metrics, exposing the absence of general score coverage and
one-to-one matching obligations. Syncopated pedal checked event order without
an elapsed-time bound: a 300\,ms delayed press passed that metric, whereas
pre-attack pedal failed. Missing release failed pedal-toggle but passed
syncopated-pedal. A final marked note caused articulation exit~2 because its
null next-attack gap reached compiled arithmetic. This defect was retained,
and error diagnostics are provided separately from acceptance and rejection.

\paragraph{{Local analysis cost.}}
The repository scores \emph{{Great Fairy Fountain}} and
\emph{{Merry-Go-Round of Life}} yielded 216 and 2,324 parsed notes, respectively.
The latter contains 2,418 pitched XML noteheads and 94 ties, explaining the
parsed count. The generated traces contain {small['event_count']} and {large['event_count']}
note-on, note-off and control-change events. Onsets use the implementation's
own timing map; this is not independent alignment validation. Durations,
velocities and pedal events follow fixed documented rules, with no randomness
or adjustment based on verdicts. MIDI encoding resolution was 0.5\,ms.
Synthetic timestamps already have the intended score-time origin; live
capture/playback timestamp-origin alignment was not tested.

We used a monotonic high-resolution clock around each actual
\texttt{{analyse}} call, including validation, temporary score creation,
MusicXML parsing, enrichment, JSONL serialisation and writing, fresh Prolog
startup, seven checks, verdict decoding and cleanup. Browser capture and
conversion, MIDI decoding, HTTP transport, rendering, Python import/startup
and ahead-of-time RML compilation were excluded. Each workload received
three warm-ups and 30 measured calls, sequentially in one Python process;
every call started a new Prolog process. Python libraries and OS caches could
remain warm. Delegating stage timers and warning capture add retained
instrumentation overhead. Total request durations were independently measured,
not reconstructed by summing stage medians.

\begin{{table}}[t]
\centering
\resizebox{{\linewidth}}{{!}}{{\input{{tables/timing.tex}}}}
\caption{{Local analysis times in seconds, with linear-interpolation quartiles.
Every measured sample is retained; warm-ups are excluded from the statistics.}}
\label{{tab:local-cost}}
\end{{table}}

The median totals were {small['median']:.6f}\,s and {large['median']:.6f}\,s
(Table~\ref{{tab:local-cost}}). Across the 60 measured calls there were
{failures} service exceptions, {timeouts} timeouts and {mon_errors} calls with monitor errors.
The retained per-metric outcome table reports acceptance and rejection
alongside timing: syncopated-pedal rejected on both workloads, while the
other six metrics accepted on every measured call.
Separate original-monitor diagnostics locate these rejections at events
{rejections[small['name']]['unmatched_event_index']} of {small['event_count']} and
{rejections[large['name']]['unmatched_event_index']} of {large['event_count']}, respectively.
At adjacent pedal spans, a boundary attack is consumed by the preceding
region before its release; the following press lacks a fresh preceding attack.
These diagnostic calls are excluded from the timing samples.
Parsing warnings occurred on every call ({small['generation_warnings_count']} occurrences per smaller-score
parse and {large['generation_warnings_count']} per larger-score parse), including ignored/unsupported
directions and an unmatched pedal stop; Prolog also emitted a singleton-variable
warning. All messages and raw samples are retained. An initial evaluation-wrapper
failure occurred before monitoring and is archived separately; it did not change
inputs, specifications or the frozen expectations.

\paragraph{{Limits.}}
The evidence concerns these synthetic cases, the original specifications and
two local workloads. A rejecting monitor may stop before consuming the whole
trace, so the results are not worst-case costs. They establish neither general
musical completeness nor independent alignment accuracy, scalability,
real-time guarantees or end-to-end user-facing latency. Scripts, MusicXML,
MIDI, service inputs, enriched traces, expected/actual verdicts, hashes,
warnings and individual timing samples accompany the evaluation.
'''
    (EVAL / 'evaluation.tex').write_text(tex)
    inputs = ('results/summary.json', 'results/behaviour.json', 'results/timings.jsonl', 'metadata/environment.json', 'diagnostics/early-rejection.json')
    hashes = {p: hashlib.sha256((EVAL / p).read_bytes()).hexdigest() for p in inputs}
    (EVAL / 'results/report-inputs.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print('Generated REPORT.md and evaluation.tex from raw-derived results.')


if __name__ == '__main__':
    main()
