#!/usr/bin/env python3
"""Cross-check summaries, every saved verdict, timing sample and source hash."""
import json
import csv
from collections import Counter
from pathlib import Path
import numpy as np
from common import EVAL, ROOT, save, sha


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
    assert sha(EVAL / 'results/expected-verdicts.json') == manifest['expectation_ledger_sha256']
    ledger = json.loads((EVAL / 'results/expected-verdicts.json').read_text())
    results = json.loads((EVAL / 'results/behaviour.json').read_text())
    from summarise import tables, report
    timing_tex, behaviour_tex = tables(summary, results)
    assert (EVAL / 'tables/timing.tex').read_text() == timing_tex
    assert (EVAL / 'tables/behaviour.tex').read_text() == behaviour_tex
    assert (EVAL / 'RESULTS.md').read_text() == report(summary, results)
    for row in results['cases']:
        case = next(c for c in manifest['cases'] if c['name'] == row['name'])
        expected = next(c for c in ledger['cases'] if c['name'] == row['name'])
        assert expected['expected'] == case['expected'] == row['expected']
        path = EVAL / case['input']
        assert sha(path) == case['input_sha256']
        actual = json.loads((path.parent / 'actual.json').read_text())
        assert actual['started_utc'] > ledger['frozen_utc']
        assert row['actual'] == {m: v['exit'] for m, v in actual['verdicts'].items()}
        trace = (path.parent / 'enriched-trace.jsonl').read_text().splitlines()
        assert len(trace) == actual['enriched_event_count']
    before = json.loads((EVAL / 'metadata/provenance-before.json').read_text())
    changed = [p for p, digest in before['initial_source_sha256'].items() if sha(ROOT / p) != digest]
    source_changes = [p for p in changed if '__pycache__' not in Path(p).parts]
    assert not source_changes, source_changes
    generated_cache_changes = [{'path': p, 'before_sha256': before['initial_source_sha256'][p],
                                'after_sha256': sha(ROOT / p),
                                'reason': 'Existing generated Python bytecode cache regenerated while parsing the fixture; application source is unchanged.'}
                               for p in changed]
    deterministic = json.loads((EVAL / 'results/determinism.json').read_text()) if (EVAL / 'results/determinism.json').exists() else None
    if deterministic:
        assert deterministic['ok'] and not deterministic['changed']
        generated_before = json.loads((EVAL / 'metadata/generation-hashes-before-check.json').read_text())
        assert all(sha(EVAL / p) == digest for p, digest in generated_before.items())
    rejection = json.loads((EVAL / 'diagnostics/early-rejection.json').read_text())
    for row in rejection['workloads']:
        assert sha(EVAL / row['trace']) == row['trace_sha256']
        assert sha(EVAL / row['specification']) == row['specification_sha256']
        assert row['returncode'] == 1 and row['rejected_before_end']
        assert row['unmatched_event_index'] < row['trace_event_count']
    checks = {'ok': True, 'initial_files_hashed': len(before['initial_source_sha256']),
              'source_and_input_files_unchanged': sum('__pycache__' not in Path(p).parts for p in before['initial_source_sha256']),
              'generated_cache_changes': generated_cache_changes,
              'behaviour_cases_checked': len(results['cases']), 'timing_samples_checked': len(samples),
              'csv_samples_checked': len(csv_rows),
              'deterministic_generation_artefacts_checked': deterministic['artefacts_checked'] if deterministic else None,
              'tables': 'Generated by summarise.py directly from raw data; summary statistics independently recomputed here.',
              'expected_actual_discrepancy_cases_preserved': results['discrepancy_case_count']}
    save(EVAL / 'results/checks.json', checks)
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()
