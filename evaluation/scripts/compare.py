#!/usr/bin/env python3
"""Check archived evidence, minimal source change and all before/after outcomes."""
import datetime
import json
import subprocess
from common import EVAL, ROOT, ScoreModel, save, sha
from sharing import project_file_required, verify_archive_manifest

ARCHIVE = EVAL / 'archive/v1-original'


def read(path):
    return json.loads(path.read_text())


def verify_archive():
    manifest = read(ARCHIVE / 'MANIFEST.json')
    return verify_archive_manifest(ARCHIVE, manifest)


def provenance():
    count = verify_archive()
    archived = read(ARCHIVE / 'provenance.json')
    original = archived['original_project_sha256']
    current = {path: sha(ROOT / path) for path in original if project_file_required(path)}
    changes = [{'path': p, 'before_sha256': original[p], 'after_sha256': current[p]}
               for p in current if current[p] != original[p]]
    assert [c['path'] for c in changes] == ['rml/metrics/articulation.rml'], changes
    old_rml = (ARCHIVE / 'project/rml/metrics/articulation.rml').read_text()
    new_rml = (ROOT / 'rml/metrics/articulation.rml').read_text()
    # Numeric predicate declarations are byte-for-byte unchanged.
    assert old_rml.split('Main =')[0] == new_rml.split('// Without a successor')[0]
    compiled_changes = []
    diffs = []
    for path in ('rml/metrics/articulation.rml',):
        process = subprocess.run(['diff', '-u', '--label', 'before/' + path, '--label', 'after/' + path,
                                  str(ARCHIVE / 'project' / path), str(ROOT / path)], capture_output=True, text=True)
        assert process.returncode == 1
        diffs.append(process.stdout)
    for old in sorted((ARCHIVE / 'evaluation/compiled').glob('*.pl')):
        new = EVAL / 'compiled' / old.name
        if sha(old) != sha(new):
            compiled_changes.append({'metric': old.stem, 'before_sha256': sha(old), 'after_sha256': sha(new)})
            process = subprocess.run(['diff', '-u', '--label', 'before/compiled/' + old.name,
                                      '--label', 'after/compiled/' + old.name, str(old), str(new)], capture_output=True, text=True)
            diffs.append(process.stdout)
    assert [c['metric'] for c in compiled_changes] == ['articulation']
    (EVAL / 'metadata/repair.diff').write_text('\n'.join(diffs))
    save(EVAL / 'metadata/repair-provenance.json', {
        'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'archive': 'archive/v1-original', 'archive_verified_file_count': count,
        'original_project_sha256': original, 'repaired_project_sha256': current,
        'source_changes': changes, 'compiled_changes': compiled_changes,
        'source_diff': 'metadata/repair.diff', 'git_state': archived['git_commands'],
        'project_commit': None, 'git_limitation': archived['git_limitation'],
        'policy': 'The existing no-gap exemption precedes numeric articulation alternatives. Numeric predicates, service code, other six specifications and assessment policies are unchanged.'})


def verify_inputs(parse_counts=True):
    """Identity is checked against archived original inputs, never by retuning them."""
    old_manifest = read(ARCHIVE / 'evaluation/results/behaviour-manifest.json')
    new_manifest = read(EVAL / 'results/behaviour-manifest.json')
    assert [c['name'] for c in old_manifest['cases']] == [c['name'] for c in new_manifest['cases']]
    identities = []
    for case in old_manifest['cases']:
        for name in ('performance.mid', 'midi-events.json', 'browser-payload.json', 'service-input.json'):
            relative = str((EVAL / case['input']).parent.relative_to(EVAL) / name)
            assert sha(EVAL / relative) == sha(ARCHIVE / 'evaluation' / relative), relative
            identities.append(relative)
    old_workloads = read(ARCHIVE / 'evaluation/results/workloads.json')['workloads']
    new_workloads = read(EVAL / 'results/workloads.json')['workloads']
    assert new_workloads == old_workloads, 'Workload manifest changed'
    details = []
    for row in new_workloads:
        for name in ('performance.mid', 'midi-events.json', 'browser-payload.json', 'service-input.json', 'score-model.json'):
            relative = str((EVAL / row['input']).parent.relative_to(EVAL) / name)
            assert sha(EVAL / relative) == sha(ARCHIVE / 'evaluation' / relative), relative
            identities.append(relative)
        assert sha(EVAL / row['input']) == row['input_sha256']
        assert sha(ROOT / row['score_file']) == row['score_sha256']
        body = read(EVAL / row['input'])
        assert len(body['notes']) == row['parsed_note_count']
        assert 2 * len(body['notes']) + len(body['control_changes']) == row['midi_event_count']
        actual_count = len(ScoreModel.from_musicxml(str(ROOT / row['score_file'])).notes) if parse_counts else row['parsed_note_count']
        assert actual_count == row['parsed_note_count']
        details.append({'workload': row['name'], 'parsed_note_count': actual_count,
                        'input_sha256': sha(EVAL / row['input']), 'midi_event_count': row['midi_event_count'],
                        'score_sha256': row['score_sha256'], 'identical_to_original': True})
    assert sorted(r['parsed_note_count'] for r in details) == [216, 2324]
    if parse_counts:
        save(EVAL / 'results/input-identity-v2.json', {'ok': True, 'inputs_identical': True,
             'note_counts_verified_by_fresh_source_parse': True,
             'original_cases_checked': len(old_manifest['cases']), 'generated_artefacts_checked': len(identities),
             'paths_compared': identities, 'workloads': details})
    else:
        prepared = read(EVAL / 'results/input-identity-v2.json')
        assert prepared['ok'] and prepared['inputs_identical'] and prepared['workloads'] == details
    return len(identities)


def compare():
    count = verify_archive()
    verify_inputs(parse_counts=False)
    before = {c['name']: c for c in read(ARCHIVE / 'evaluation/results/behaviour.json')['cases']}
    after = {c['name']: c for c in read(EVAL / 'results/behaviour.json')['cases']}
    assert set(before) == set(after) and len(after) == 28
    changed, rows = [], []
    for name, old in before.items():
        new = after[name]
        assert set(old['actual']) == set(new['actual'])
        for metric, code in old['actual'].items():
            row = {'case': name, 'metric': metric, 'before': code, 'after': new['actual'][metric]}
            rows.append(row)
            if row['before'] != row['after']:
                changed.append(row)
    allowed = [{'case': 'final_marked_note', 'metric': 'articulation', 'before': 2, 'after': 0}]
    unexpected = [row for row in changed if row not in allowed]
    payload = {'suite_case_count': 28, 'metric_verdicts_compared': len(rows), 'changed_outcomes': changed,
               'unchanged_outcome_count': len(rows) - len(changed), 'unexpected_changes': unexpected,
               'inputs_identical': True, 'archive_verified': True, 'archive_verified_file_count': count,
               'all_outcomes': rows, 'expected_repair_observed': changed == allowed}
    save(EVAL / 'results/behaviour-comparison.json', payload)
    assert changed == allowed, changed
    print('Compared 196 outcomes: final_marked_note articulation 2->0; other 195 unchanged.')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    if args.prepare:
        provenance()
        n = verify_inputs()
        print(f'Original archive verified; only articulation RML/generated Main changed; {n} input artefacts identical.')
    else:
        compare()
