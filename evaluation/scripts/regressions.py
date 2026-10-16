#!/usr/bin/env python3
"""Freeze focused articulation expectations, then execute actual old/new monitors.

Generation calls the real MIDI/browser converter and MusicXML parser, but never
a monitor. Execution is an explicit separate operation after the ledger exists.
These cases remain separate from the original 28-case behavioural suite.
"""
import argparse
import copy
import datetime
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import time
import warnings

sys.dont_write_bytecode = True

from lxml import etree
from common import EVAL, ROOT, ScoreModel, analyse, midi_replay, save, service, sha, to_jsonl


ARCHIVE = EVAL / 'archive/v1-original'
FIXTURES = EVAL / 'fixtures/regressions'
ARTIFACTS = EVAL / 'artifacts/regressions'
LEDGER = EVAL / 'results/regression-expected-v2.json'
METRICS = tuple(service.METRICS)
MARKS = ('staccato', 'tenuto', 'legato')


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def acceptance(articulation=0):
    return {m: articulation if m == 'articulation' else 0 for m in METRICS}


def note(mark, duration=25000, gap=None, timestamp=0, pitch=60):
    return {'type': 'noteon', 'note': {'number': pitch, 'rawAttack': 80},
            'timestamp': timestamp, 'durMs': duration, 'gapMs': gap,
            'expected': {'art': mark}}


def add_direct(rows, name, events, original, repaired, rationale):
    path = FIXTURES / 'direct' / (name + '.jsonl')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_jsonl(events) + '\n')
    rows.append({'name': name, 'kind': 'direct_monitor',
                 'input': str(path.relative_to(EVAL)), 'input_sha256': sha(path),
                 'event_count': len(events),
                 'expected_original': {'articulation': original},
                 'expected_repaired': {'articulation': repaired},
                 'rationale': rationale})


def score_variant(mark):
    tree = etree.parse(str(ARCHIVE / 'evaluation/fixtures/exercise.musicxml'))
    last = tree.findall('.//note[pitch]')[-1]
    notations = last.find('notations')
    if notations is not None:
        for old in list(notations.findall('articulations')):
            notations.remove(old)
    if mark is not None:
        if notations is None:
            notations = etree.SubElement(last, 'notations')
        arts = etree.SubElement(notations, 'articulations')
        etree.SubElement(arts, mark)
    path = FIXTURES / ('exercise-final-' + (mark or 'unmarked') + '.musicxml')
    tree.write(str(path), encoding='UTF-8', xml_declaration=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        model = ScoreModel.from_musicxml(str(path))
    assert len(model.notes) == 8
    assert model.notes[-1]['articulation'] == mark
    return path, [{'category': w.category.__name__, 'message': str(w.message)} for w in caught]


def add_service(rows, name, score, parse_warnings, notes, controls,
                original, repaired, rationale, probe_index, probe_mark, final_mark):
    folder = ARTIFACTS / name
    payload, midi_event_count = midi_replay(folder, notes, controls)
    # Every fixture is exactly on the converter's 0.5 ms time grid. Confirm that
    # the complete converter path retained the intended duration and onsets.
    assert payload['notes'] == notes, (name, payload['notes'], notes)
    assert payload['control_changes'] == controls
    payload['score'] = score.read_text()
    path = folder / 'service-input.json'
    save(path, payload)
    rows.append({'name': name, 'kind': 'converter_and_service',
                 'input': str(path.relative_to(EVAL)), 'input_sha256': sha(path),
                 'score': str(score.relative_to(EVAL)), 'score_sha256': sha(score),
                 'midi_sha256': sha(folder / 'performance.mid'),
                 'midi_event_count': midi_event_count, 'note_count': len(notes),
                 'generation_warnings': parse_warnings,
                 'probe': {'time_ms': notes[probe_index]['time_ms'],
                           'pitch': notes[probe_index]['pitch'],
                           'durMs': notes[probe_index]['dur_ms']},
                 'expected_enrichment': {
                     'note_count': len(notes), 'final_gap_null': True,
                     'final_articulation': final_mark,
                     'final_duration_ms': notes[-1]['dur_ms'],
                     'probe_articulation': probe_mark,
                     'probe_gap_ms': None if probe_index == -1 else 500.0,
                     'probe_duration_ms': notes[probe_index]['dur_ms'],
                     'probe_duration_retained': True},
                 'expected_original': acceptance(original),
                 'expected_repaired': acceptance(repaired),
                 'rationale': rationale})


def generate():
    FIXTURES.mkdir(parents=True, exist_ok=True)
    rows = []
    for mark in MARKS:
        add_direct(rows, 'direct_final_null_' + mark, [note(mark)], 2, 0,
                   f'Final {mark} attack has gapMs:null and duration 25,000 ms. '
                   'Original marked arithmetic raises before noGap; repaired '
                   'noGap exempts this requirement without verifying duration.')
    add_direct(rows, 'direct_final_null_unmarked', [note(None)], 0, 0,
               'An unmarked final attack is accepted by the existing noMark '
               'alternative and by the reordered noGap alternative.')
    for mark in MARKS:
        for duration in (374, 375, 376):
            code = int(duration > 375 if mark == 'staccato' else duration < 375)
            add_direct(rows, f'direct_{mark}_{duration}ms',
                       [note(mark, duration, 500)], code, code,
                       f'Numeric gap 500 ms sets the boundary at 375 ms. '
                       f'{mark} requires duration ' + ('<=375 ms.' if mark == 'staccato' else '>=375 ms.'))
        bad = 376 if mark == 'staccato' else 374
        add_direct(rows, 'direct_earlier_bad_then_null_' + mark,
                   [note(mark, bad, 500), note(mark, 25000, None, 500, 62)], 1, 1,
                   f'The first {mark} event violates the numeric 375 ms boundary; '
                   'the final marked null-gap exemption cannot erase that rejection.')
    add_direct(rows, 'direct_malformed_nonnull_gap', [note('staccato', 250, 'bad-gap')], 2, 2,
               'A non-null, non-numeric gap still reaches CLP(R) and raises; '
               'the repair must not convert arbitrary monitor errors into acceptance.')
    add_direct(rows, 'direct_malformed_duration', [note('tenuto', 'bad-duration', 500)], 2, 2,
               'A non-numeric duration with a numeric gap still raises in CLP(R).')

    baseline = json.loads((ARCHIVE / 'evaluation/artifacts/behaviour/baseline/service-input.json').read_text())
    variants = {mark: score_variant(mark) for mark in ('staccato', 'tenuto', None)}
    for mark, (score, ws) in variants.items():
        notes = copy.deepcopy(baseline['notes'])
        notes[-1]['dur_ms'] = 25000.0
        add_service(rows, 'service_final_null_' + (mark or 'unmarked'), score, ws,
                    notes, baseline['control_changes'], 2 if mark else 0, 0,
                    'Actual MIDI decoding, browser conversion, MusicXML parsing, '
                    'enrichment and all seven checks. The final '
                    f'{mark or "unmarked"} attack has duration 25,000 ms and no next attack; '
                    'acceptance exempts the duration requirement rather than verifying it.', -1, mark, mark)
    for mark, index, bad in (('staccato', 0, 376), ('tenuto', 1, 374)):
        score, ws = variants[mark]
        notes = copy.deepcopy(baseline['notes'])
        notes[index]['dur_ms'] = float(bad)
        notes[-1]['dur_ms'] = 25000.0
        add_service(rows, 'service_earlier_bad_then_null_' + mark, score, ws,
                    notes, baseline['control_changes'], 1, 1,
                    f'Earlier {mark} duration {bad} ms violates its numeric 375 ms '
                    'boundary; a later marked null-gap event cannot erase rejection.', index, mark, mark)
        for duration in (374, 375, 376):
            notes = copy.deepcopy(baseline['notes'])
            notes[index]['dur_ms'] = float(duration)
            code = int(duration > 375 if mark == 'staccato' else duration < 375)
            unmarked_score, unmarked_ws = variants[None]
            add_service(rows, f'service_{mark}_{duration}ms', unmarked_score, unmarked_ws,
                        notes, baseline['control_changes'], code, code,
                        f'Complete converter/service boundary test: {mark}, duration '
                        f'{duration} ms, next attack gap 500 ms, threshold 375 ms. '
                        'The final event is unmarked with a null gap.', index, mark, None)
    ledger = {'version': 2,
              'method': 'Manual outcomes fixed from original/repaired source semantics before any regression monitor call.',
              'scope': 'Additional focused regressions, separate from the original 28 cases.',
              'no_gap_interpretation': 'Duration requirement inapplicable when there is no next-attack gap; final duration is not verified.',
              'legato_service_limitation': 'Installed Partitura ' + importlib.metadata.version('partitura') + ' MusicXML get_articulations recognises staccato and tenuto, but not literal legato. Detached-legato is a different unchanged token. Literal legato is tested only by direct compiled-monitor fixtures.',
              'original_compiled_articulation_sha256': sha(ARCHIVE / 'evaluation/compiled/articulation.pl'),
              'cases': rows}
    if LEDGER.exists():
        existing = json.loads(LEDGER.read_text())
        assert {k: v for k, v in existing.items() if k != 'frozen_utc'} == ledger, 'Refusing to revise the frozen regression ledger.'
    else:
        save(LEDGER, dict(ledger, frozen_utc=utc()))
    (FIXTURES / 'README.md').write_text(
        '# Focused articulation regressions\n\n'
        'These additional cases are separate from the original 28-case suite. '
        'Generate and freeze manual original/repaired expectations before executing monitors:\n\n'
        '```bash\n'
        'PYTHONDONTWRITEBYTECODE=1 evaluation/.venv/bin/python evaluation/scripts/regressions.py --generate-only\n'
        'PYTHONDONTWRITEBYTECODE=1 evaluation/.venv/bin/python evaluation/scripts/regressions.py --run\n'
        '```\n\n'
        '`results/regression-expected-v2.json` is immutable once generated. '
        'Direct JSONL fixtures invoke the actual batch monitor with archived original '
        'and current compiled RML. Converter/service cases encode and decode MIDI, '
        'call the actual browser `toPerformance`, then call the actual local '
        '`analyse` service with all seven checks and a fresh Prolog process. '
        'The two paths are labelled in every result.\n\n'
        'A 25,000 ms final duration deliberately demonstrates that null-gap '
        'acceptance means the duration requirement is inapplicable; it does not '
        'verify that duration. Numeric boundaries are 374/375/376 ms for a 500 ms '
        'gap. Earlier violations must reject even when the trace ends with a '
        'marked null-gap attack. Malformed non-null numeric operands must retain '
        'their monitor errors.\n\n'
        'Partitura\'s MusicXML articulation importer exposes staccato and tenuto, '
        'but not the literal `legato` used by this monitor. `detached-legato` '
        'is a different unchanged token. Legato therefore has direct monitor '
        'coverage only; no unsupported MusicXML legato service coverage is claimed.\n')
    print(f'Frozen {len(rows)} manual regression expectations; no monitor executed.')


def direct_run(case, spec, version):
    trace = EVAL / case['input']
    argv = ['swipl', '-O', '-p', 'monitor=' + str(ROOT / 'rml/monitor'),
            str(ROOT / 'server/batch.pl'), '--', str(trace), 'articulation', str(spec)]
    started = utc()
    start = time.perf_counter_ns()
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    elapsed = (time.perf_counter_ns() - start) / 1e9
    verdict = {}
    for line in proc.stdout.splitlines():
        pieces = line.split()
        if len(pieces) == 2 and pieces[0] == 'articulation':
            verdict['articulation'] = int(pieces[1])
    result = {'version': version, 'started_utc': started,
              'command': argv, 'specification_sha256': sha(spec),
              'total_seconds': elapsed, 'process': {'returncode': proc.returncode,
                  'stdout': proc.stdout, 'stderr': proc.stderr},
              'actual': verdict, 'trace_sha256': sha(trace)}
    save(ARTIFACTS / case['name'] / (version + '-actual.json'), result)
    return result


def service_run(case, specs, version):
    body = json.loads((EVAL / case['input']).read_text())
    previous = service.SPECS
    try:
        service.SPECS = str(specs)
        started = utc()
        result, events = analyse(body)
    finally:
        service.SPECS = previous
    result.update(version=version, started_utc=started,
                  specification_sha256=sha(specs / 'articulation.pl'),
                  specifications_directory=str(specs))
    actual = {m: v['exit'] for m, v in result.get('verdicts', {}).items()}
    result['actual'] = actual
    if events is not None:
        folder = ARTIFACTS / case['name']
        (folder / (version + '-enriched-trace.jsonl')).write_text(to_jsonl(events) + '\n')
        onsets = [e for e in events if e['type'] == 'noteon']
        final = max(onsets, key=lambda e: e['timestamp'])
        probe = next(e for e in onsets if e['timestamp'] == case['probe']['time_ms']
                     and e['note']['number'] == case['probe']['pitch'])
        result['enrichment_checks'] = {
            'note_count': len(onsets), 'final_gap_null': final['gapMs'] is None,
            'final_articulation': final['expected']['art'],
            'final_duration_ms': final['durMs'],
            'probe_articulation': probe['expected']['art'],
            'probe_gap_ms': probe['gapMs'], 'probe_duration_ms': probe['durMs'],
            'probe_duration_retained': probe['durMs'] == case['probe']['durMs']}
    save(ARTIFACTS / case['name'] / (version + '-actual.json'), result)
    return result


def run():
    if not LEDGER.exists():
        raise SystemExit('Run --generate-only first to freeze the manual regression ledger.')
    ledger_sha = sha(LEDGER)
    ledger = json.loads(LEDGER.read_text())
    original = ARCHIVE / 'evaluation/compiled'
    repaired = EVAL / 'compiled'
    assert sha(original / 'articulation.pl') == ledger['original_compiled_articulation_sha256']
    # All application components used by both variants must remain byte-identical.
    for path in ('server/alignment/server.py', 'server/alignment/join.py', 'server/batch.pl',
                 'rml/monitor/trace_expressions_semantics.pl', 'rml/monitor/deep_subdict.pl'):
        assert sha(ROOT / path) == sha(ARCHIVE / 'project' / path), path
    started = utc()
    assert started > ledger['frozen_utc']
    rows = []
    for case in ledger['cases']:
        assert sha(EVAL / case['input']) == case['input_sha256']
        if case['kind'] == 'converter_and_service':
            assert sha(EVAL / case['score']) == case['score_sha256']
            folder = (EVAL / case['input']).parent
            assert sha(folder / 'performance.mid') == case['midi_sha256']
            before = service_run(case, original, 'original')
            after = service_run(case, repaired, 'repaired')
            before_trace = (folder / 'original-enriched-trace.jsonl').read_bytes()
            after_trace = (folder / 'repaired-enriched-trace.jsonl').read_bytes()
            enrichment_identical = before_trace == after_trace
        else:
            before = direct_run(case, original / 'articulation.pl', 'original')
            after = direct_run(case, repaired / 'articulation.pl', 'repaired')
            enrichment_identical = None
        discrepancy = {version: {'expected': case['expected_' + version], 'actual': result['actual']}
                       for version, result in (('original', before), ('repaired', after))
                       if result['actual'] != case['expected_' + version]}
        expected_changes = {m: {'before': code, 'after': case['expected_repaired'][m]}
                            for m, code in case['expected_original'].items()
                            if code != case['expected_repaired'][m]}
        actual_changes = {m: {'before': before['actual'].get(m), 'after': after['actual'].get(m)}
                          for m in case['expected_original']
                          if before['actual'].get(m) != after['actual'].get(m)}
        checks_ok = all(r.get('process', {}).get('returncode') == 0 for r in (before, after))
        if case['kind'] == 'converter_and_service':
            checks_ok = checks_ok and enrichment_identical and all(
                r.get('success') and r.get('enrichment_checks') == case['expected_enrichment']
                for r in (before, after))
        row = dict(case, actual_original=before['actual'], actual_repaired=after['actual'],
                   expected_changes=expected_changes, actual_changes=actual_changes,
                   discrepancies=discrepancy, enrichment_identical=enrichment_identical,
                   ok=not discrepancy and actual_changes == expected_changes and bool(checks_ok))
        rows.append(row)
        print(case['name'], before['actual'], '->', after['actual'],
              'as expected' if row['ok'] else 'DISCREPANCY', flush=True)
    assert sha(LEDGER) == ledger_sha
    output = {'started_utc': started, 'completed_utc': utc(),
              'expectation_ledger': str(LEDGER.relative_to(EVAL)),
              'expectation_ledger_sha256': ledger_sha,
              'original_compiled_articulation_sha256': sha(original / 'articulation.pl'),
              'repaired_compiled_articulation_sha256': sha(repaired / 'articulation.pl'),
              'direct_monitor_count': sum(r['kind'] == 'direct_monitor' for r in rows),
              'converter_and_service_count': sum(r['kind'] == 'converter_and_service' for r in rows),
              'discrepancy_case_count': sum(not r['ok'] for r in rows),
              'no_gap_interpretation': ledger['no_gap_interpretation'],
              'legato_service_limitation': ledger['legato_service_limitation'],
              'cases': rows, 'ok': all(r['ok'] for r in rows)}
    save(EVAL / 'results/regressions.json', output)
    if not output['ok']:
        raise SystemExit('Regression discrepancy; retained all original/repaired results and diagnostics.')
    print(f'All {len(rows)} focused regression cases match both frozen outcome vectors.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--generate-only', action='store_true')
    mode.add_argument('--run', action='store_true')
    args = parser.parse_args()
    generate() if args.generate_only else run()
