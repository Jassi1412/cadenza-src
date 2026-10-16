#!/usr/bin/env python3
"""Generate deterministic synthetic MIDI and freeze manual expectations before validation."""
import copy
import datetime
import json
from pathlib import Path
import shutil
import warnings
from lxml import etree

from common import EVAL, ROOT, ScoreModel, midi_replay, save, sha
from behaviour_cases import build_cases


def parse(path):
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter('always')
        model = ScoreModel.from_musicxml(str(path))
    return model, [{'category': w.category.__name__, 'message': str(w.message)} for w in ws]


def serialise_model(model):
    return {'notes': model.notes, 'dynamics': model.dynamics, 'pedals': model.pedals,
            'beat_grad': model.beat_grad, 'time_anchors': list(zip(model._anch_beats.tolist(), model._anch_ms.tolist()))}


def write_performance(folder, score, notes, cc):
    payload, event_count = midi_replay(folder, notes, cc)
    payload['score'] = Path(score).read_text()
    save(folder / 'service-input.json', payload)
    return {'input': str((folder / 'service-input.json').relative_to(EVAL)),
            'input_sha256': sha(folder / 'service-input.json'),
            'midi_sha256': sha(folder / 'performance.mid'),
            'note_count': len(payload['notes']), 'midi_event_count': event_count,
            'control_change_count': len(payload['control_changes'])}


def main():
    exercise = EVAL / 'fixtures/exercise.musicxml'
    model, ws = parse(exercise)
    save(EVAL / 'fixtures/exercise-model.json', serialise_model(model))
    cases = build_cases(model)
    # Freeze all expected outputs before the first monitor execution. They are
    # hand-authored in behaviour_cases.py; generation calls no monitor.
    ledger = [{k: v for k, v in c.items() if k not in ('notes', 'control_changes')} for c in cases]
    ledger.append({'name': 'final_marked_note', 'teacher_error': False,
                   'teacher_interpretation': 'Final staccato note shortened to half its written duration.',
                   'expected': {m: 0 for m in
                     ('articulation', 'chord-jitter', 'dynamics-adherence', 'pedal-toggle', 'pitch-agreement', 'pitch-range', 'syncopated-pedal')},
                   'rationale': 'Version 2: the existing noGap exemption is tried before numeric predicates. Last marked attack has gapMs:null, so the duration requirement is inapplicable and articulation accepts. Other six outcomes remain unchanged.'})
    original_ledger_path = EVAL / 'results/expected-verdicts.json'
    original = json.loads(original_ledger_path.read_text())
    original_archived = EVAL / 'archive/v1-original/evaluation/results/expected-verdicts.json'
    assert sha(original_ledger_path) == sha(original_archived), 'Original frozen ledger changed'
    old_expected = {c['name']: c['expected'] for c in original['cases']}
    changes = [{'case': c['name'], 'metric': m, 'before': old_expected[c['name']][m], 'after': v}
               for c in ledger for m, v in c['expected'].items() if v != old_expected[c['name']][m]]
    assert changes == [{'case': 'final_marked_note', 'metric': 'articulation', 'before': 2, 'after': 0}]
    ledger_path = EVAL / 'results/expected-verdicts-v2.json'
    if ledger_path.exists():
        existing = json.loads(ledger_path.read_text())
        if existing['cases'] != ledger:
            raise SystemExit('Refusing to change the frozen expectation ledger. Preserve this run and use a separate evaluation copy for revised expectations.')
    else:
        save(ledger_path, {'version': 2, 'method': 'Manual policy-preserving repair expectations before repaired evaluation',
             'derived_from': 'results/expected-verdicts.json', 'original_ledger_sha256': sha(original_ledger_path),
             'intended_changes': changes,
             'frozen_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'cases': ledger})
    rows = []
    for case in cases:
        row = dict(next(r for r in ledger if r['name'] == case['name']))
        row.update(write_performance(EVAL / 'artifacts/behaviour' / case['name'], exercise,
                                     case['notes'], case['control_changes']))
        rows.append(row)
    tree = etree.parse(str(exercise))
    last = tree.findall('.//note[pitch]')[-1]
    notations = last.find('notations')
    if notations is None:
        notations = etree.SubElement(last, 'notations')
    arts = notations.find('articulations')
    if arts is None:
        arts = etree.SubElement(notations, 'articulations')
    etree.SubElement(arts, 'staccato')
    final_score = EVAL / 'fixtures/exercise-final-marked.musicxml'
    tree.write(str(final_score), encoding='UTF-8', xml_declaration=True)
    baseline = next(c for c in cases if c['name'] == 'baseline')
    notes = copy.deepcopy(baseline['notes'])
    notes[-1]['dur_ms'] = 250.0
    row = dict(ledger[-1])
    row.update(write_performance(EVAL / 'artifacts/behaviour/final_marked_note', final_score,
                                 notes, baseline['control_changes']))
    rows.append(row)
    save(EVAL / 'results/behaviour-manifest.json', {'exercise_sha256': sha(exercise), 'generation_warnings': ws,
         'expectation_ledger': 'results/expected-verdicts-v2.json',
         'expectation_ledger_sha256': sha(ledger_path), 'cases': rows})

    workloads = []
    for path in sorted((ROOT / 'scores').glob('*.musicxml')):
        model, ws = parse(path)
        label = 'score-' + str(len(model.notes))
        folder = EVAL / 'artifacts/workloads' / label
        onsets = sorted({n['onset'] for n in model.notes})
        notes = []
        for n in model.notes:
            onset = model.ms_at(n['onset'])
            end = model.ms_at(n['onset'] + n['duration'])
            following = next((o for o in onsets if o > n['onset']), None)
            gap = model.ms_at(following) - onset if following is not None else end - onset
            duration = (0.5 * gap if n['articulation'] == 'staccato' else
                        0.9 * gap if n['articulation'] in ('tenuto', 'legato') else 0.8 * (end - onset))
            notes.append({'time_ms': round(onset * 2) / 2,
                          'dur_ms': max(0.5, round(duration * 2) / 2),
                          'pitch': n['pitch'],
                          'velocity': int(round(n['expected_dyn'])) if n['expected_dyn'] is not None else 80})
        cc = []
        for span in model.pedals:
            cc.extend([{'time_ms': round(model.ms_at(span['start']) * 2) / 2 + 10,
                        'controller': 64, 'value': 127},
                       {'time_ms': round(model.ms_at(span['end']) * 2) / 2,
                        'controller': 64, 'value': 0}])
        # No random jitter; no adjustments based on monitor verdicts.
        row = {'name': label, 'score_file': str(path.relative_to(ROOT)), 'score_sha256': sha(path),
               'parsed_note_count': len(model.notes), 'generation_warnings': ws}
        row.update(write_performance(folder, path, notes, cc))
        xml = etree.parse(str(path))
        row['xml_counts'] = {'pitched_notes': len(xml.findall('.//note[pitch]')), 'rests': len(xml.findall('.//note/rest')),
                             'tie_starts': len(xml.findall('.//note/tie[@type="start"]')),
                             'tie_stops': len(xml.findall('.//note/tie[@type="stop"]')),
                             'parts': len(xml.findall('.//part'))}
        save(folder / 'score-model.json', serialise_model(model))
        workloads.append(row)
    save(EVAL / 'results/workloads.json', {'seed': None, 'randomness': 'none', 'workloads': workloads})
    print(f'Generated {len(rows)} behaviour cases and {len(workloads)} workloads; expectations frozen.')


if __name__ == '__main__':
    main()
