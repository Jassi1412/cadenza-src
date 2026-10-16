#!/usr/bin/env python3
"""Derive every displayed result from the retained manifests and raw samples."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import numpy as np


METRICS = ('articulation', 'chord-jitter', 'dynamics-adherence', 'pedal-toggle',
           'pitch-agreement', 'pitch-range', 'syncopated-pedal')
SHORT = dict(zip(METRICS, ('A', 'C', 'D', 'T', 'P', 'R', 'S')))
DEFAULT_EVAL = Path(__file__).resolve().parents[1]


def statistics(values):
    values = [float(x) for x in values]
    if any(not math.isfinite(x) or x < 0 for x in values):
        raise ValueError('Timing samples must be finite, non-negative seconds')
    if not values:
        return dict(sample_count=0, median=None, q1=None, q3=None, min=None, max=None)
    q1, median, q3 = np.percentile(values, [25, 50, 75], method='linear')
    return dict(sample_count=len(values), median=float(median), q1=float(q1),
                q3=float(q3), min=min(values), max=max(values))


def outcome_counts(rows, key='verdicts'):
    result = {}
    for metric in METRICS:
        counts = Counter({'0': 0, '1': 0, '2': 0, 'missing': 0})
        for row in rows:
            verdict = row.get(key, {}).get(metric)
            code = verdict.get('exit') if isinstance(verdict, dict) else verdict
            counts['missing' if code is None else str(code)] += 1
        result[metric] = dict(counts)
    return result


def diagnostics(rows):
    warnings = Counter((w.get('category', ''), w.get('message', ''))
                       for row in rows for w in row.get('warnings', []))
    return {
        'service_failures': sum(not row.get('success', False) for row in rows),
        'timeouts': sum(row.get('exception') == 'TimeoutExpired' for row in rows),
        'monitor_error_runs': sum(any(v.get('exit') == 2 for v in row.get('verdicts', {}).values())
                                  for row in rows),
        'warnings_count': sum(warnings.values()),
        'warning_runs': sum(bool(row.get('warnings')) for row in rows),
        'warning_messages': [dict(category=category, message=message, count=count)
                             for (category, message), count in sorted(warnings.items())],
        'prolog_stderr_runs': sum(bool(row.get('process', {}).get('stderr', '').strip()) for row in rows),
        'python_stderr_runs': sum(bool(row.get('python_stderr', '').strip()) for row in rows),
    }


def workload_summary(workload, samples):
    rows = [r for r in samples if r['workload'] == workload['name']]
    measured = [r for r in rows if r['phase'] == 'measured']
    warmup = [r for r in rows if r['phase'] == 'warmup']
    if len(measured) + len(warmup) != len(rows):
        raise ValueError('Unrecognised sample phase for ' + workload['name'])
    stages = sorted({stage for r in measured for stage in r.get('stages_seconds', {})})
    enriched = sorted({r['enriched_event_count'] for r in measured if 'enriched_event_count' in r})
    row = {
        'name': workload['name'], 'score_file': workload['score_file'],
        'score_sha256': workload['score_sha256'],
        'note_count': workload['parsed_note_count'],
        'generated_note_count': workload['note_count'],
        'event_count': workload['midi_event_count'],
        'control_change_count': workload['control_change_count'],
        'enriched_event_count': enriched[0] if len(enriched) == 1 else None,
        'enriched_event_counts': enriched,
        'xml_counts': workload.get('xml_counts', {}),
        'warmup_count': len(warmup), 'measured_count': len(measured),
        'protocol_complete': len(warmup) == 3 and len(measured) == 30,
        **statistics(r['total_seconds'] for r in measured),
        **diagnostics(measured),
        'outcomes': outcome_counts(measured),
        'stages': {stage: statistics(r['stages_seconds'][stage] for r in measured
                                      if stage in r.get('stages_seconds', {})) for stage in stages},
        'generation_warnings': workload.get('generation_warnings', []),
        'generation_warnings_count': len(workload.get('generation_warnings', [])),
        'warmup_diagnostics': diagnostics(warmup),
        'warmup_outcomes': outcome_counts(warmup),
    }
    return row


def behaviour_summary(data):
    cases = data['cases']
    discrepancies = []
    for case in cases:
        actual = case.get('actual', {})
        changed = {m: {'expected': code, 'actual': actual.get(m)}
                   for m, code in case['expected'].items() if actual.get(m) != code}
        if changed:
            discrepancies.append({'name': case['name'], 'metrics': changed})
    accepted = [case['name'] for case in cases if case['teacher_error']
                and case.get('success') and all(case.get('actual', {}).get(m) == 0 for m in METRICS)]
    return {
        'case_count': len(cases), 'discrepancy_case_count': len(discrepancies),
        'discrepancies': discrepancies,
        'teacher_error_case_count': sum(bool(c['teacher_error']) for c in cases),
        'teacher_error_cases_accepted_by_all': len(accepted),
        'teacher_error_cases_accepted_by_all_names': accepted,
        'all_metrics_accepted_case_names': [c['name'] for c in cases if c.get('success')
                                           and all(c.get('actual', {}).get(m) == 0 for m in METRICS)],
        'service_failures': sum(not c.get('success', False) for c in cases),
        'monitor_error_cases': sum(any(code == 2 for code in c.get('actual', {}).values()) for c in cases),
        'warnings_count': sum(len(c.get('warnings', [])) for c in cases),
        'outcomes': outcome_counts(cases, 'actual'),
    }


def number(value):
    return '--' if value is None else f'{value:.6f}'


def latex(value):
    escapes = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
               '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
               '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(escapes.get(c, c) for c in str(value))


def markdown(value):
    return str(value).replace('|', r'\|').replace('\n', ' ')


def tables(summary, behaviour):
    timing = [r'% Generated by scripts/summarise.py; all durations are seconds.',
              r'\begin{tabular}{lrrrrrrrrr}', r'\hline',
              r'Workload & Notes & Events & Warm & Runs & Median & Q1 & Q3 & Min & Max \\', r'\hline']
    for row in summary['workloads']:
        values = [latex(row['name']), str(row['note_count']), str(row['event_count']),
                  str(row['warmup_count']), str(row['measured_count'])]
        values += [number(row[key]) for key in ('median', 'q1', 'q3', 'min', 'max')]
        timing.append(' & '.join(values) + r' \\')
    timing += [r'\hline', r'\end{tabular}', '']
    behavioural = [r'% Generated by scripts/summarise.py. Cells are expected/actual exit codes.',
                  r'% A articulation; C chord jitter; D dynamics; T pedal toggle;',
                  r'% P pitch agreement; R pitch range; S syncopated pedal.',
                  r'\begin{tabular}{llrrrrrrrl}', r'\hline',
                  r'Case & Teacher error & A & C & D & T & P & R & S & Diff. \\', r'\hline']
    for case in behaviour['cases']:
        cells = [latex(case['name']), 'yes' if case['teacher_error'] else 'no']
        cells += [f"{case['expected'].get(m, '--')}/{case.get('actual', {}).get(m, '--')}" for m in METRICS]
        different = any(case.get('actual', {}).get(m) != code for m, code in case['expected'].items())
        behavioural.append(' & '.join(cells + ['yes' if different else 'no']) + r' \\')
    behavioural += [r'\hline', r'\end{tabular}', '']
    return '\n'.join(timing), '\n'.join(behavioural)


def report(summary, behaviour):
    lines = ['# Results generated from local raw data', '',
             'All performances are deterministic synthetic MIDI. Raw inputs are '
             '`results/workloads.json`, `results/behaviour.json` and `results/timings.jsonl`.', '',
             'Durations are seconds. Quartiles use NumPy percentile with `method="linear"`. '
             'Warm-ups are excluded from timing statistics. Every measured run contributes '
             'its total duration, including service failures and timeouts; no outliers are discarded. '
             'Timeouts are a subset of service failures. Monitor errors (exit 2) are counted separately.', '',
             'Generated events count decoded MIDI noteon, noteoff and control-change messages; '
             'the enriched trace count is reported separately.', '',
             '| Workload | Parsed notes | MIDI events | Enriched events | Warm-ups | Measured | Median | Q1 | Q3 | Min | Max |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for row in summary['workloads']:
        fields = [row['name'], row['note_count'], row['event_count'], row['enriched_event_count'],
                  row['warmup_count'], row['measured_count']]
        fields += [number(row[key]) for key in ('median', 'q1', 'q3', 'min', 'max')]
        lines.append('| ' + ' | '.join(markdown(v) if v is not None else '--' for v in fields) + ' |')
    lines += ['', '## Failures, errors and warnings', '',
              '| Workload | Service failures | Timeouts | Runs with monitor error | Warning occurrences | Runs with Prolog stderr | Generation warnings |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for row in summary['workloads']:
        keys = ('service_failures', 'timeouts', 'monitor_error_runs', 'warnings_count',
                'prolog_stderr_runs', 'generation_warnings_count')
        lines.append('| ' + markdown(row['name']) + ' | ' + ' | '.join(str(row[k]) for k in keys) + ' |')
    for row in summary['workloads']:
        lines += ['', f"- `{row['name']}`: score `{row['score_file']}`; SHA-256 `{row['score_sha256']}`."]
        if not row['protocol_complete']:
            lines.append('  Recorded counts differ from the requested 3 warm-ups and 30 measured runs.')
        warm = row['warmup_diagnostics']
        lines.append(f"  Warm-ups: {warm['service_failures']} service failures, {warm['timeouts']} timeouts, "
                     f"{warm['monitor_error_runs']} runs with monitor errors, {warm['warnings_count']} warning occurrences.")
        for warning in row['warning_messages']:
            lines.append(f"  Measured warning ({warning['count']} occurrences): "
                         f"{markdown(warning['category'])}: {markdown(warning['message'])}")
        for warning in row['generation_warnings']:
            lines.append(f"  Generation warning: {markdown(warning.get('category', ''))}: "
                         f"{markdown(warning.get('message', ''))}")
    lines += ['', '## Measured monitor outcomes', '',
              'These are finite-trace exit codes: 0 acceptance, 1 rejection, 2 error. '
              'A metric may reject before reading the complete trace. Missing means no metric result was returned.', '',
              '| Workload | Metric | Exit 0 | Exit 1 | Exit 2 | Missing |',
              '|---|---|---:|---:|---:|---:|']
    for row in summary['workloads']:
        for metric, counts in row['outcomes'].items():
            lines.append('| ' + ' | '.join([row['name'], metric] + [str(counts[k]) for k in ('0', '1', '2', 'missing')]) + ' |')
    lines += ['', '## Component timings', '',
              'Each component is measured around the unchanged function or subprocess call. '
              'Component statistics include available samples, with their counts shown; they do not '
              'sum to the independently measured request time. `trace_serialise` excludes writing the file. '
              '`prolog_process` includes subprocess startup, the seven checks and output capture.', '',
              '| Workload | Stage | Samples | Median | Q1 | Q3 | Min | Max |',
              '|---|---|---:|---:|---:|---:|---:|---:|']
    for row in summary['workloads']:
        for stage, stats in row['stages'].items():
            fields = [row['name'], stage, str(stats['sample_count'])]
            fields += [number(stats[k]) for k in ('median', 'q1', 'q3', 'min', 'max')]
            lines.append('| ' + ' | '.join(fields) + ' |')
    b = summary['behaviour']
    lines += ['', '## Behavioural validation', '',
              f"Executed {b['case_count']} cases: {b['discrepancy_case_count']} differ from the frozen manual expectations; "
              f"{b['service_failures']} service failures; {b['monitor_error_cases']} cases with a monitor error; "
              f"{b['warnings_count']} warning occurrences.", '',
              f"Of {b['teacher_error_case_count']} cases labelled as teacher errors, "
              f"{b['teacher_error_cases_accepted_by_all']} were accepted by all seven metrics.", '']
    if b['teacher_error_cases_accepted_by_all_names']:
        lines += ['Cases accepted despite a teacher error: ' + ', '.join(
            '`' + n + '`' for n in b['teacher_error_cases_accepted_by_all_names']) + '.', '']
    lines += ['Cells below are **expected/actual** exit codes. A=articulation, C=chord-jitter, '
              'D=dynamics-adherence, T=pedal-toggle, P=pitch-agreement, R=pitch-range, S=syncopated-pedal.', '',
              '| Case | Teacher error | A | C | D | T | P | R | S | Discrepancy |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for case in behaviour['cases']:
        cells = [case['name'], 'yes' if case['teacher_error'] else 'no']
        cells += [f"{case['expected'].get(m, '--')}/{case.get('actual', {}).get(m, '--')}" for m in METRICS]
        changed = any(case.get('actual', {}).get(m) != code for m, code in case['expected'].items())
        lines.append('| ' + ' | '.join(cells + ['yes' if changed else 'no']) + ' |')
    if b['discrepancies']:
        lines += ['', 'Discrepancies remain visible:', '']
        for case in b['discrepancies']:
            lines.append('- `' + case['name'] + '`: ' + '; '.join(
                f"{m}: expected {v['expected']}, actual {v['actual']}" for m, v in case['metrics'].items()) + '.')
    lines += ['', 'These observations concern the original specifications and synthetic inputs on this '
              'machine. They establish neither worst-case costs nor real-time guarantees, general '
              'scalability, independent alignment accuracy, pianist performance or user-facing latency.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evaluation-dir', type=Path, default=DEFAULT_EVAL)
    args = parser.parse_args()
    folder = args.evaluation_dir
    files = {name: folder / 'results' / name for name in
             ('workloads.json', 'behaviour.json', 'timings.jsonl')}
    for path in files.values():
        if not path.is_file():
            raise SystemExit(f'Missing raw input {path}; run generation, validation and benchmarking first.')
    workloads = json.loads(files['workloads.json'].read_text())['workloads']
    behaviour = json.loads(files['behaviour.json'].read_text())
    samples = [json.loads(line) for line in files['timings.jsonl'].read_text().splitlines() if line.strip()]
    known = {w['name'] for w in workloads}
    if any(row['workload'] not in known for row in samples):
        raise ValueError('Raw timings contain a workload absent from workloads.json')
    summary = {
        'duration_unit': 'seconds', 'quartiles': 'numpy.percentile(method="linear")',
        'numpy_version': np.__version__,
        'sample_policy': 'All measured total durations retained, including failures; warm-ups excluded.',
        'event_count_definition': 'Decoded generated MIDI noteon, noteoff and control-change events.',
        'raw_inputs': {name: {'path': str(path.relative_to(folder)),
                              'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                       for name, path in files.items()},
        'workloads': [workload_summary(w, samples) for w in workloads],
        'behaviour': behaviour_summary(behaviour),
    }
    timing_tex, behaviour_tex = tables(summary, behaviour)
    (folder / 'tables').mkdir(exist_ok=True)
    (folder / 'results/summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    (folder / 'RESULTS.md').write_text(report(summary, behaviour))
    (folder / 'tables/timing.tex').write_text(timing_tex)
    (folder / 'tables/behaviour.tex').write_text(behaviour_tex)
    print(f"Summarised {len(workloads)} workloads, {len(samples)} raw timing samples and "
          f"{summary['behaviour']['case_count']} behavioural cases.")


if __name__ == '__main__':
    main()
