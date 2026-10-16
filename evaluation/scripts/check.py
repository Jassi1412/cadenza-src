#!/usr/bin/env python3
"""Cross-check summaries, every saved verdict, timing sample and source hash."""
import json
import csv
from collections import Counter
from pathlib import Path
import numpy as np
from common import EVAL, ROOT, save, sha
from sharing import project_file_required


def main():
    summary = json.loads((EVAL / 'results/summary.json').read_text())
    samples = [json.loads(line) for line in (EVAL / 'results/timings.jsonl').read_text().splitlines()]
    with (EVAL / 'results/timings.csv').open() as f:
        csv_rows = list(csv.DictReader(f))
    assert len(csv_rows) == len(samples)
    for raw, row in zip(samples, csv_rows):
        assert row['workload'] == raw['workload'] and row['phase'] == raw['phase']
        assert int(row['index']) == raw['index'] and float(row['total_seconds']) == raw['total_seconds']
        assert row['success'] == str(raw['success'])
        for metric, verdict in raw.get('verdicts', {}).items():
            assert int(row[metric + '_exit']) == verdict['exit']
    workloads = json.loads((EVAL / 'results/workloads.json').read_text())['workloads']
    for workload in workloads:
        selected = [s for s in samples if s['workload'] == workload['name']]
        assert Counter(s['phase'] for s in selected) == {'warmup': 3, 'measured': 30}
        for phase in ('warmup', 'measured'):
            assert len({s['index'] for s in selected if s['phase'] == phase}) == (3 if phase == 'warmup' else 30)
        measured = [s for s in selected if s['phase'] == 'measured']
        values = np.array([s['total_seconds'] for s in measured])
        item = next(w for w in summary['workloads'] if w['name'] == workload['name'])
        expected_stats = dict(zip(('min', 'q1', 'median', 'q3', 'max'), np.percentile(values, [0, 25, 50, 75, 100], method='linear')))
        for key, val in expected_stats.items():
            assert np.isclose(item[key], val, rtol=0, atol=1e-12), (key, item[key], val)
        assert item['measured_count'] == 30 and item['warmup_count'] == 3
        for metric, counts in item['outcomes'].items():
            observed = Counter(str(s.get('verdicts', {}).get(metric, {}).get('exit', 'missing')) for s in measured)
            assert all(observed[code] == count for code, count in counts.items())
        assert sha(EVAL / workload['input']) == workload['input_sha256']
        assert sha(ROOT / workload['score_file']) == workload['score_sha256']
        for sample in selected:
            assert sample['total_seconds'] > 0
            assert sum(sample['stages_seconds'].values()) <= sample['total_seconds']
    manifest = json.loads((EVAL / 'results/behaviour-manifest.json').read_text())
    ledger_path = EVAL / manifest['expectation_ledger']
    assert sha(ledger_path) == manifest['expectation_ledger_sha256']
    ledger = json.loads(ledger_path.read_text())
    archive = EVAL / 'archive/v1-original'
    assert sha(EVAL / 'results/expected-verdicts.json') == sha(archive / 'evaluation/results/expected-verdicts.json')
    assert ledger['original_ledger_sha256'] == sha(EVAL / 'results/expected-verdicts.json')
    results = json.loads((EVAL / 'results/behaviour.json').read_text())
    assert results['discrepancy_case_count'] == 0
    from summarise import tables, report
    timing_tex, behaviour_tex = tables(summary, results)
    assert (EVAL / 'tables/timing.tex').read_text() == timing_tex
    assert (EVAL / 'tables/behaviour.tex').read_text() == behaviour_tex
    assert (EVAL / 'RESULTS.md').read_text() == report(summary, results)
    for row in results['cases']:
        case = next(c for c in manifest['cases'] if c['name'] == row['name'])
        expected = next(c for c in ledger['cases'] if c['name'] == row['name'])
        assert expected['expected'] == case['expected'] == row['expected']
        assert row['success'] and row['actual'] == row['expected'] and not row['discrepancies']
        path = EVAL / case['input']
        assert sha(path) == case['input_sha256']
        actual = json.loads((path.parent / 'actual.json').read_text())
        assert actual['started_utc'] > ledger['frozen_utc']
        assert row['actual'] == {m: v['exit'] for m, v in actual['verdicts'].items()}
        trace = (path.parent / 'enriched-trace.jsonl').read_text().splitlines()
        assert len(trace) == actual['enriched_event_count']
    provenance = json.loads((EVAL / 'metadata/repair-provenance.json').read_text())
    unchanged_harness = ('common.py', 'benchmark.py', 'replay.mjs', 'behaviour_cases.py')
    for script in unchanged_harness:
        assert sha(EVAL / 'scripts' / script) == sha(archive / 'evaluation/scripts' / script), script
    project_hashes = {p: digest for p, digest in provenance['repaired_project_sha256'].items()
                      if project_file_required(p)}
    assert all(sha(ROOT / p) == digest for p, digest in project_hashes.items())
    assert [c['path'] for c in provenance['source_changes']] == ['rml/metrics/articulation.rml']
    assert [c['metric'] for c in provenance['compiled_changes']] == ['articulation']
    from compare import verify_archive, verify_inputs
    archived_files = verify_archive()
    original_input_artefacts = verify_inputs(parse_counts=False)
    comparison = json.loads((EVAL / 'results/behaviour-comparison.json').read_text())
    expected_change = [{'case': 'final_marked_note', 'metric': 'articulation', 'before': 2, 'after': 0}]
    assert comparison['changed_outcomes'] == expected_change and not comparison['unexpected_changes']
    assert comparison['metric_verdicts_compared'] == 196 and comparison['unchanged_outcome_count'] == 195
    old_expected = {c['name']: c['expected'] for c in json.loads((EVAL / 'results/expected-verdicts.json').read_text())['cases']}
    changed_predictions = [{'case': c['name'], 'metric': m, 'before': old_expected[c['name']][m], 'after': v}
                           for c in ledger['cases'] for m, v in c['expected'].items() if v != old_expected[c['name']][m]]
    assert changed_predictions == expected_change
    regressions = json.loads((EVAL / 'results/regressions.json').read_text())
    regression_ledger_path = EVAL / regressions['expectation_ledger']
    assert sha(regression_ledger_path) == regressions['expectation_ledger_sha256']
    regression_ledger = json.loads(regression_ledger_path.read_text())
    assert regressions['ok'] and regressions['direct_monitor_count'] == 18 and regressions['converter_and_service_count'] == 11
    assert regressions['discrepancy_case_count'] == 0
    for row in regressions['cases']:
        assert row['ok'] and row['actual_original'] == row['expected_original'] and row['actual_repaired'] == row['expected_repaired']
        assert sha(EVAL / row['input']) == row['input_sha256']
        for version in ('original', 'repaired'):
            actual = json.loads((EVAL / 'artifacts/regressions' / row['name'] / (version + '-actual.json')).read_text())
            assert actual['actual'] == row['actual_' + version]
            assert actual['started_utc'] > regression_ledger['frozen_utc']
        if row['kind'] == 'converter_and_service':
            assert row['enrichment_identical']
    from regression_report import render as render_regressions
    regression_md, regression_tex, regression_ok = render_regressions(regressions, regression_ledger)
    assert regression_ok
    assert (EVAL / 'REGRESSIONS.md').read_text() == regression_md
    assert (EVAL / 'tables/regressions.tex').read_text() == regression_tex
    assert all(sha(EVAL / path) == digest for path, digest in json.loads((EVAL / 'results/report-inputs.json').read_text()).items())
    rejection = json.loads((EVAL / 'diagnostics/early-rejection.json').read_text())
    for row in rejection['workloads']:
        assert sha(EVAL / row['trace']) == row['trace_sha256']
        assert sha(EVAL / row['specification']) == row['specification_sha256']
        assert row['returncode'] == 1 and row['rejected_before_end']
        assert row['unmatched_event_index'] < row['trace_event_count']
    for compilation in json.loads((EVAL / 'metadata/compilation.json').read_text()):
        assert compilation['returncode'] == 0
        assert sha(ROOT / compilation['source']) == compilation['source_sha256']
        assert sha(EVAL / 'compiled' / (Path(compilation['source']).stem + '.pl')) == compilation['compiled_sha256']
    assert min(s['started_utc'] for s in samples) > ledger['frozen_utc']
    checks = {'ok': True, 'archived_files_verified': archived_files,
              'project_files_checked': len(project_hashes),
              'authorised_source_changes': provenance['source_changes'],
              'original_input_artefacts_identical': original_input_artefacts,
              'behaviour_cases_checked': len(results['cases']), 'timing_samples_checked': len(samples),
              'csv_samples_checked': len(csv_rows),
              'regression_cases_checked': len(regressions['cases']),
              'timing_and_conversion_harness_unchanged': list(unchanged_harness),
              'changed_original_suite_outcomes': comparison['changed_outcomes'],
              'tables': 'Generated by summarise.py directly from raw data; summary statistics independently recomputed here.',
              'expected_actual_discrepancy_cases_preserved': results['discrepancy_case_count']}
    save(EVAL / 'results/checks.json', checks)
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()
