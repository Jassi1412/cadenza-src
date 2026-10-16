#!/usr/bin/env python3
"""Render repaired-version reports only from fresh, retained evaluation evidence."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from summarise import latex

EVAL = Path(__file__).resolve().parents[1]
METRICS = ('articulation', 'chord-jitter', 'dynamics-adherence', 'pedal-toggle',
           'pitch-agreement', 'pitch-range', 'syncopated-pedal')
ARCHIVE = 'archive/v1-original/evaluation'


def read(folder, name):
    return json.loads((folder / name).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def date(value):
    return datetime.datetime.fromisoformat(value)


def command_version(env, name):
    command = next(row for row in env['runtime_commands'] if row['argv'][0] == name)
    return (command['stdout'] or command['stderr']).strip().splitlines()[0]


def behavioural_changes(before, after):
    old = {row['name']: row for row in before['cases']}
    new = {row['name']: row for row in after['cases']}
    if old.keys() != new.keys():
        raise ValueError('The repaired report requires the unchanged original case set')
    return [dict(case=name, metric=metric, before=old[name]['actual'].get(metric),
                 after=new[name]['actual'].get(metric))
            for name in old for metric in METRICS
            if old[name]['actual'].get(metric) != new[name]['actual'].get(metric)]


def timing_table(workloads):
    rows = ['| Parsed notes | Enriched events | Warm-ups | Measured | Median (s) | Q1 (s) | Q3 (s) | Min (s) | Max (s) |',
            '|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for row in workloads:
        cells = [str(row[k]) for k in ('note_count', 'enriched_event_count', 'warmup_count', 'measured_count')]
        cells += [f'{row[k]:.6f}' for k in ('median', 'q1', 'q3', 'min', 'max')]
        rows.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(rows)


def outcome_table(workloads):
    rows = ['| Metric | ' + ' | '.join(f"{w['note_count']:,}-note measured calls" for w in workloads) + ' |',
            '|---|' + '---|' * len(workloads)]
    for metric in METRICS:
        cells = [metric]
        for workload in workloads:
            cells.append(', '.join(f'exit {code}: {count}' for code, count in workload['outcomes'][metric].items() if count))
        rows.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evaluation-dir', type=Path, default=EVAL)
    folder = parser.parse_args().evaluation_dir
    inputs = ('results/summary.json', 'results/behaviour.json', 'results/timings.jsonl',
              'results/workloads.json',
              'results/expected-verdicts-v2.json', 'results/regressions.json',
              'results/regression-expected-v2.json',
              'results/behaviour-comparison.json', 'metadata/repair-provenance.json',
              'metadata/environment.json', 'metadata/compilation.json',
              'diagnostics/early-rejection.json',
              'diagnostics/null-gap-original-reproduction.json',
              ARCHIVE + '/results/behaviour.json', ARCHIVE + '/results/workloads.json')
    for name in inputs:
        if not (folder / name).is_file():
            raise SystemExit(f'Missing repaired evaluation evidence: {name}')
    summary = read(folder, 'results/summary.json')
    behaviour = read(folder, 'results/behaviour.json')
    ledger = read(folder, 'results/expected-verdicts-v2.json')
    regression = read(folder, 'results/regressions.json')
    comparison = read(folder, 'results/behaviour-comparison.json')
    provenance = read(folder, 'metadata/repair-provenance.json')
    env = read(folder, 'metadata/environment.json')
    timings = [json.loads(s) for s in (folder / 'results/timings.jsonl').read_text().splitlines() if s.strip()]
    rejections = {r['workload']: r for r in read(folder, 'diagnostics/early-rejection.json')['workloads']}
    changes = behavioural_changes(read(folder, ARCHIVE + '/results/behaviour.json'), behaviour)
    if changes != comparison['changed_outcomes']:
        raise ValueError('Independent behavioural comparison differs from saved comparison')
    # Reject stale original data before writing any repaired-version claims.
    frozen = date(ledger['frozen_utc'])
    if not timings or any(date(row['started_utc']) <= frozen for row in timings):
        raise ValueError('Every timing call must follow the repaired expectation freeze')
    for name in ('workloads.json', 'behaviour.json', 'timings.jsonl'):
        if summary['raw_inputs'][name]['sha256'] != digest(folder / 'results' / name):
            raise ValueError('Summary does not describe the current raw ' + name)
    workloads = sorted(summary['workloads'], key=lambda row: row['note_count'])
    if [w['note_count'] for w in workloads] != [216, 2324] or any(not w['protocol_complete'] for w in workloads):
        raise ValueError('Expected two workloads, each with 3 warm-ups and 30 measured calls')
    small, large = workloads
    old_workloads = {w['name']: w for w in read(folder, ARCHIVE + '/results/workloads.json')['workloads']}
    for workload in read(folder, 'results/workloads.json')['workloads']:
        for key in ('score_sha256', 'input_sha256', 'parsed_note_count', 'midi_event_count', 'control_change_count'):
            if workload[key] != old_workloads[workload['name']][key]:
                raise ValueError(f"Timing workload changed: {workload['name']} {key}")
    for workload in workloads:
        if workload['event_count'] != workload['enriched_event_count']:
            raise ValueError('Generated and enriched event counts differ; review reporting')
        for metric in METRICS:
            expected_code = '1' if metric == 'syncopated-pedal' else '0'
            if workload['outcomes'][metric][expected_code] != workload['measured_count']:
                raise ValueError('Review unexpected measured monitor outcomes before paper rendering')
    b = summary['behaviour']
    expected_change = [dict(case='final_marked_note', metric='articulation', before=2, after=0)]
    if changes != expected_change or comparison['unexpected_changes']:
        raise ValueError('Review unexpected behavioural changes before generating the repaired paper')
    if not comparison['inputs_identical'] or not comparison['archive_verified']:
        raise ValueError('Input identity and archive verification are required for the paper')

    # Additional regressions remain distinct from the original behavioural suite.
    regression_count = len(regression['cases'])
    direct_n = regression['direct_monitor_count']
    service_n = regression['converter_and_service_count']
    if direct_n + service_n != regression_count or not regression['ok'] or any(not row['ok'] for row in regression['cases']):
        raise ValueError('Regression discrepancies remain; review before generating the repaired paper')
    if b['discrepancy_case_count'] or b['service_failures'] or b['monitor_error_cases']:
        raise ValueError('The repaired behavioural suite contains unresolved failures')

    start_local = min(date(row['started_utc']) for row in timings).astimezone(ZoneInfo('Europe/Rome'))
    end_local = max(date(row['started_utc']) + datetime.timedelta(seconds=row['total_seconds'])
                    for row in timings).astimezone(ZoneInfo('Europe/Rome'))
    ram = int(env['proc_and_cgroup']['/proc/meminfo'].splitlines()[0].split()[1]) / 1024**2
    cpu = next(line.split(':', 1)[1].strip() for line in env['proc_and_cgroup']['/proc/cpuinfo'].splitlines()
               if line.startswith('model name'))
    package_text = ', '.join(f'{name} {env["packages"][name.lower()]}'
                             for name in ('Partitura', 'NumPy', 'SciPy', 'lxml', 'mido'))
    runtime_text = '; '.join(f'{name}: {command_version(env, name)}' for name in ('swipl', 'java', 'node'))
    source_changes = ', '.join(f'`{row["path"]}`' for row in provenance['source_changes'])
    false_rejections = [row['name'] for row in behaviour['cases'] if not row['teacher_error']
                        and any(code != 0 for code in row['actual'].values())]
    failures = sum(w['service_failures'] for w in workloads)
    timeouts = sum(w['timeouts'] for w in workloads)
    monitor_errors = sum(w['monitor_error_runs'] for w in workloads)
    measured_count = sum(w['measured_count'] for w in workloads)
    timing = timing_table(workloads)
    outcomes = outcome_table(workloads)
    changed_table = '| Case | Metric | Archived exit | Repaired exit |\n|---|---|---:|---:|\n' + '\n'.join(
        f"| {row['case']} | {row['metric']} | {row['before']} | {row['after']} |" for row in changes)
    ready = failures == timeouts == monitor_errors == 0
    readiness = ('The repaired data are ready to replace the previous paper evaluation, subject to the stated scope and remaining limitations.'
                 if ready else 'The repaired data retain timing failures or monitor errors and require review before replacing the paper evaluation.')

    report = f'''# Repaired Cadenza evaluation for the paper

The final-note articulation exception was eliminated. Across the original **{b['case_count']} cases and {comparison['metric_verdicts_compared']} metric verdicts**, the only observed change was `final_marked_note` articulation: exit 2 (error) became exit 0 (acceptance under the existing no-gap exemption). The other {comparison['unchanged_outcome_count']} verdicts were unchanged. All cases matched the separately frozen repaired expectations. A further **{regression_count} focused regression checks** matched their expectations ({direct_n} direct monitor, {service_n} complete conversion/service).

New median local analysis costs were **{small['median']:.6f} s for {small['note_count']:,} parsed notes** and **{large['median']:.6f} s for {large['note_count']:,} parsed notes**. Both workload traces still reject `syncopated-pedal`; these are costs of the actual rejecting analysis path. Earlier timings were archived and were not reused as samples or targets. {readiness}

## Evidence preserved and repair

[The original evaluation archive]({ARCHIVE}/REPORT.md) preserves the previous raw results, metadata, frozen ledger, diagnostics, compiled specifications and reports; `archive/v1-original/MANIFEST.json` records its contents. [Repair provenance](metadata/repair-provenance.json) records the original/repaired content hashes and Git state. Usable Cadenza Git history remains unavailable: the accessible project `.git` is empty, and Git resolves to an unrelated parent. Its commit is not attributed to Cadenza.

The original failing service input was [rerun before repair](diagnostics/null-gap-original-reproduction.json) and reproduced `type_error(clpr_expression,null)`. Enrichment intentionally supplies `gapMs: null` when there is no next distinct performed attack. In the original RML choice, the marked-note numeric predicate was tried before `noGap`; compiled Prolog therefore sent `null` to CLP(R) multiplication before reaching the exemption. This is an unsafe specification ordering exposed by the generated code; the compiler faithfully preserved that order.

The source change is limited to {source_changes}: the existing `noGap` alternative moves before all arithmetic alternatives in `Main`. The vendored compiler regenerated the monitor; source/generated hashes and exact compiler commands are retained in [metadata/compilation.json](metadata/compilation.json), [executed commands](metadata/executed-commands-v2.json) record the evaluation commands, and [repair.diff](metadata/repair.diff) shows the application/specification diff. The compiler and service matching code were unchanged. Numeric constraints remain staccato duration ≤0.75 × gap and tenuto/legato duration ≥0.75 × gap. A no-gap acceptance states that this duration requirement is **inapplicable**; it does not verify the final note's duration. Pitch matching, score coverage and pedal policies were not changed.

## Behaviour and regressions

The original [expectation ledger](results/expected-verdicts.json) is preserved byte-for-byte. [Version 2](results/expected-verdicts-v2.json), frozen before repaired execution, changes only the expected articulation error for `final_marked_note` to no-gap acceptance. Its other six expectations and all other cases are unchanged. Teacher-error labels follow the declared synthetic exercise rubric; they are not ratings collected from teachers.

{changed_table}

[The exhaustive comparison](results/behaviour-comparison.json) checks every old/new case-metric outcome and confirms identical original suite inputs. [RESULTS.md](RESULTS.md) and [tables/behaviour.tex](tables/behaviour.tex) contain the new {b['case_count']}-case expected/actual matrix; exits 0, 1 and 2 mean acceptance, rejection and monitor error, respectively. Request completion is counted separately. There were {b['discrepancy_case_count']} prediction discrepancies, {b['service_failures']} service failures and {b['monitor_error_cases']} cases with monitor errors.

The separately identifiable [focused regressions](results/regressions.json) compare original and regenerated RML monitors using [manual expectations](results/regression-expected-v2.json) frozen before those runs. The {direct_n} direct fixtures cover null-gap final staccato, tenuto and legato events, an unmarked final event, numeric durations below/at/above the 0.75 boundary, and earlier genuine violations followed by null-gap events. The {service_n} complete-path fixtures also exercise MIDI decoding, the actual browser converter, score enrichment and service monitoring wherever the importer produces the relevant mark. The importer emits staccato and tenuto; literal `legato` is covered at the direct monitor boundary only. Earlier violations still reject, so the final-event exemption does not erase previous failures. Two deliberately malformed numeric fixtures retain monitor exit 2, confirming that arbitrary arithmetic errors are not converted into acceptance. All {regression_count} checks matched the manual regression expectations.

The readable original/repaired regression matrix is [REGRESSIONS.md](REGRESSIONS.md), with per-case links to inputs and raw evidence.

The repaired baseline passes all seven metrics. The existing boundary cases retain their outcomes: chord spread 29 ms accepts and 30/31 ms reject; staccato and tenuto at the inclusive 375 ms boundary accept, while tenuto at 374 ms rejects. The mf target is 71.5 with an inclusive ±8 band: integer velocity 64 accepts and 80 rejects. Wrong pitch, out-of-range pitch, wrong velocity and applicable duration violations still reject as predicted.

## Remaining assessment limitations

The missing-note and duplicate-note cases still pass all seven metrics. The trace has no independent event for each unfulfilled score obligation, and pitch matching is not a one-to-one score/performance assignment. The repair therefore supplies no general completeness guarantee. Of {b['teacher_error_case_count']} rubric-labelled error cases, {b['teacher_error_cases_accepted_by_all']} pass all metrics ({', '.join(b['teacher_error_cases_accepted_by_all_names'])}). {len(false_rejections)} cases labelled without a teacher error fail to obtain every acceptance ({', '.join(false_rejections)}), owing to the tighter composed pedal association. The archived final-note error is no longer among them.

Pedal-toggle still accepts a press or late release at +25 ms and rejects +26 ms for this 120 BPM fixture. Enrichment associates/snaps endpoints within 0.05 beat, tighter than the RML's nominal 0.25-beat (125 ms) assessment tolerance; presses at 124/125 ms therefore reject despite lying within the declared teacher tolerance. Floating-point comparisons, tempo and score-map clamping affect the effective boundary. These cases do not establish a universal 25 ms threshold.

Syncopated-pedal still checks order without a numerical deadline: a 300 ms delayed press passes that metric but fails pedal-toggle; a pre-attack press fails syncopated-pedal. Missing release fails pedal-toggle but passes syncopated-pedal. With every pedal event absent, pedal-toggle accepts vacuously while syncopated-pedal rejects. These policies are unchanged.

## New local execution costs

{timing}

Each workload received three warm-ups followed by 30 measured calls. All {measured_count} measured samples contribute to the statistics; quartiles use linear interpolation and no outlier is discarded. Across these calls there were {failures} service failures, {timeouts} timeouts and {monitor_errors} calls with monitor exit 2. [timings.jsonl](results/timings.jsonl) retains all {len(timings)} calls, including warnings, complete verdicts and subprocess output; [timings.csv](results/timings.csv) retains the tabular samples. [summary.json](results/summary.json) and all displayed statistics are generated from this new raw data.

{outcomes}

The {small['note_count']:,}-note score produces {small['event_count']:,} decoded/enriched events ({small['control_change_count']} controls), and the {large['note_count']:,}-note score produces {large['event_count']:,} events ({large['control_change_count']} controls). The larger XML contains {large['xml_counts']['pitched_notes']:,} pitched noteheads and {large['xml_counts']['tie_starts']} tie starts/stops; actual parsing yields {large['note_count']:,} sounding notes. Input SHA-256 hashes and event counts match the archived workloads; [workloads.json](results/workloads.json) records full filenames, hashes and parser counts.

The other six metrics accept on every measured workload call; syncopated-pedal rejects on both. Separate [standalone-monitor diagnostics](diagnostics/early-rejection.json), excluded from timing, locate rejection at event **{rejections[small['name']]['unmatched_event_index']}/{small['event_count']}** and **{rejections[large['name']]['unmatched_event_index']}/{large['event_count']}**. At adjacent pedal spans, a boundary attack is consumed by the preceding region before its release; the following press lacks a fresh preceding marked attack. Rejecting monitors can stop early. The costs therefore do not represent seven fully accepting checks or worst-case trace consumption.

Warning occurrences numbered {small['generation_warnings_count']} during small-score generation and {large['generation_warnings_count']} during large-score generation, with {small['warnings_count']} and {large['warnings_count']} occurrences across their measured calls. Ignored metronome/unsupported text directions, the larger score's unmatched pedal stop and Prolog's pedal-toggle singleton-variable warning remain visible. Exact warnings and component statistics are in [RESULTS.md](RESULTS.md). No warnings were silently suppressed or repaired.

## Boundary, environment and reproduction

`time.perf_counter_ns()` measures the total immediately around the actual local `server.analyse(body)` call. This includes validation, temporary MusicXML creation, parsing, matching/enrichment, JSONL serialisation and writing, fresh Prolog startup, specification loading, seven sequential checks, verdict decoding and cleanup. It excludes Python import/startup, input JSON loading, MIDI encoding/decoding, browser capture/conversion, HTTP transport, rendering and ahead-of-time compilation. Delegating component timers and warning capture retain their overhead; serialisation excludes file writing, which remains in the total. Component medians are not summed to estimate a total.

Calls ran sequentially in fixed order ({large['note_count']:,} then {small['note_count']:,} notes) in one Python process. Every call reparsed its score and started one fresh Prolog process; imports, allocator state and OS caches could remain warm. Numerical-library thread limits were one. The first warm-up was uninstrumented; the second checked that delegation preserved success, verdicts and every enriched event. CPU affinity/frequency and background activity were not controlled, and the machine was not reserved exclusively.

The new calls ran on {start_local.strftime('%d %B %Y')}, {start_local.strftime('%H:%M:%S %Z')}–{end_local.strftime('%H:%M:%S %Z')}, using {cpu}, {ram:.2f} GiB reported RAM and Linux {env['uname'][2]}. The recorded environment used Python {env['python'].split()[0]}, {package_text}; runtime records report {runtime_text}. Full versions, CPU/resource information and thread settings are in [environment.json](metadata/environment.json); exact compilation and execution commands accompany the reproduction scripts. The local Python version differs from the Docker image's Python 3.12.

All service-path performances use deterministic synthetic MIDI at 0.5 ms resolution, with every original input and intermediate trace retained. They pass through the actual browser `toPerformance` export and unchanged service functions; direct monitor fixtures instead supply enriched JSONL events. Workload onsets depend on Cadenza's own timing map, so this does not independently validate alignment. Synthetic timestamps already use the intended score-time origin; browser capture/React lifecycle and the live capture/playback timestamp-origin relationship remain unvalidated. There are no pianist recordings or user-study participants.

[README.md](README.md) gives exact reproduction commands and [IMPLEMENTATION.md](IMPLEMENTATION.md) documents the observed semantics. The new concise British English section is [evaluation.tex](evaluation.tex). The preserved archive also contains the previous harness-only failures, installation diagnostics and determinism evidence; they are not new repaired-version observations. Hash and verdict checks retain the distinction between the intended source change and unrelated files.

The evidence supports elimination of the reproduced null-gap exception, preserved numeric articulation boundaries, unchanged other suite verdicts, and local costs for these two workloads. It does not establish general musical completeness, independent live alignment accuracy, scalability, real-time guarantees or end-to-end user latency. {readiness}
'''
    tex = rf'''% Generated from repaired-version retained raw data by scripts/paper.py.
\section{{Experimental evaluation}}
\label{{sec:evaluation}}
We evaluated the repaired articulation monitor, its preserved assessment
boundaries and local execution costs. Service-path performances used
deterministic synthetic MIDI; direct checks used synthetic enriched traces.
No pianist recordings or user study were involved.
The previous evaluation, expectations and diagnostics were archived before
repair. Content hashes identify both source versions because usable project
Git history was unavailable; no parent repository commit is attributed to Cadenza.

\paragraph{{Repair and behavioural evidence.}}
Replaying the original final-marked-note input reproduced
\texttt{{type\_error(clpr\_expression,null)}}. The final attack has no next
distinct performed onset, so enrichment intentionally supplies a null gap.
The RML tried a numeric duration alternative before the existing no-gap
alternative, exposing null to generated CLP(R) arithmetic. We moved the
no-gap alternative first and regenerated Prolog with the vendored compiler.
Staccato still requires $d\leq0.75g$, and tenuto/legato require
$d\geq0.75g$ whenever the gap applies. No successor interval was invented.
Acceptance without a gap means that this requirement is inapplicable,
not that the final duration was verified.

The unchanged {b['case_count']}-case suite uses an original eight-note MusicXML
exercise with a chord, dynamics, staccato, tenuto and a pedal span. A separately
versioned manual ledger was frozen before repaired execution; it changes only
the expected final-note articulation error to no-gap acceptance.
All {comparison['metric_verdicts_compared']} metric outcomes were compared with the archive:
only this articulation verdict changed (exit 2 to 0); the other
{comparison['unchanged_outcome_count']} were unchanged. All repaired predictions matched,
with {b['service_failures']} service failures and {b['monitor_error_cases']} monitor errors.
A further {regression_count} focused checks also matched expectations:
{direct_n} direct compiled-monitor fixtures and {service_n} complete
conversion/service fixtures. They cover marked/unmarked null-gap finals,
durations below/at/above the 0.75 boundary, and earlier violations followed
by no-gap events; earlier violations still reject. The importer produces
staccato and tenuto; literal legato is tested directly at the monitor boundary.
Two malformed numeric fixtures retain their expected monitor errors;
the repair does not convert arbitrary arithmetic failures into acceptance.

\paragraph{{Remaining assessment limits.}}
Missing and duplicate-note cases still pass all seven metrics, showing the
absence of general score-coverage and one-to-one matching obligations.
Pedal endpoint association remains narrower than the nominal RML assessment
tolerance: this 120 BPM fixture accepts +25\,ms and rejects +26\,ms,
despite a nominal 0.25-beat (125\,ms) allowance. The effective boundary depends
on enrichment, tempo and floating-point snapping. Syncopated-pedal checks
event order without a numerical deadline: a 300\,ms delayed press passes
that metric, although pedal-toggle rejects it. These policies were unchanged.

\paragraph{{Local execution costs.}}
The same repository-score inputs yielded {small['note_count']:,} and
{large['note_count']:,} parsed notes and {small['event_count']:,} and
{large['event_count']:,} enriched events; hashes and counts match the archive.
The larger score's {large['xml_counts']['pitched_notes']:,} pitched XML
noteheads include {large['xml_counts']['tie_starts']} tied continuations.
Onsets depend on the implementation's own timing map; this does not
independently validate alignment. Synthetic timestamps already have the
intended score-time origin, leaving live capture/playback clock alignment untested.

Each workload received three warm-ups and 30 measured calls, sequentially
in one Python process, with a new Prolog process per request and all seven
checks. A monotonic clock surrounded the actual \texttt{{analyse}} call,
including validation, temporary score creation, MusicXML parsing, enrichment,
JSONL serialisation/writing, Prolog startup/specification loading, monitoring,
verdict decoding and cleanup. Browser capture/conversion, MIDI decoding,
HTTP transport, rendering, Python startup/import and ahead-of-time compilation
were excluded. Stage-timer and warning-capture overhead remained included;
totals were measured directly, rather than summing component medians.

\begin{{table}}[t]
\centering
\resizebox{{\linewidth}}{{!}}{{\input{{tables/timing.tex}}}}
\caption{{New local analysis times in seconds. Quartiles use linear
interpolation; all measured samples are retained and warm-ups excluded.}}
\label{{tab:local-cost}}
\end{{table}}

Median totals were {small['median']:.6f}\,s and {large['median']:.6f}\,s
(Table~\ref{{tab:local-cost}}). Across {measured_count} measured calls,
there were {failures} service failures, {timeouts} timeouts and
{monitor_errors} calls with monitor errors. The other six metrics accepted
on every call, but syncopated-pedal rejected on both workloads.
Separate standalone-monitor diagnostics locate rejection at events
{rejections[small['name']]['unmatched_event_index']}/{small['event_count']} and
{rejections[large['name']]['unmatched_event_index']}/{large['event_count']},
respectively: at adjacent pedal spans the preceding region consumes a
boundary attack, leaving the next press without a fresh preceding attack.
These diagnostics were excluded from timing. Rejecting monitors can stop
early, so these costs do not represent seven fully accepting checks or
worst-case trace consumption. Parsing warnings and Prolog diagnostics were
retained with every sample; earlier timings were not reused as samples or targets.

Measurements ran on {start_local.strftime('%d %B %Y')} using
{latex(cpu)}, {ram:.2f}\,GiB reported RAM, Linux {latex(env['uname'][2])},
Python {latex(env['python'].split()[0])}, {latex(package_text)} and
{latex(command_version(env, 'swipl'))}. Numerical-library thread limits were
one; Python libraries and OS caches could remain warm. CPU frequency and
background load were uncontrolled. Exact versions, commands, hashes, raw
inputs/traces, manual expectations, all verdicts and timing samples accompany
the report. The evidence supports the repaired no-gap policy and these local
costs; it establishes neither complete musical assessment, independent live
alignment accuracy, scalability, real-time bounds nor user-facing latency.
'''
    (folder / 'REPORT.md').write_text(report)
    (folder / 'evaluation.tex').write_text(tex)
    hashes = {name: digest(folder / name) for name in inputs}
    (folder / 'results/report-inputs.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print('Generated repaired REPORT.md and evaluation.tex from fresh retained evidence.')


if __name__ == '__main__':
    main()
