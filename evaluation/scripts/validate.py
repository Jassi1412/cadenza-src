#!/usr/bin/env python3
"""Execute original service and compare against the previously frozen ledger."""
import json
import datetime
from common import EVAL, ROOT, analyse, save, sha, to_jsonl


def main():
    manifest = json.loads((EVAL / 'results/behaviour-manifest.json').read_text())
    ledger_path = EVAL / manifest['expectation_ledger']
    assert manifest['expectation_ledger_sha256'] == sha(ledger_path)
    ledger = {r['name']: r['expected'] for r in json.loads(ledger_path.read_text())['cases']}
    rows = []
    for case in manifest['cases']:
        assert case['expected'] == ledger[case['name']]
        path = EVAL / case['input']
        assert sha(path) == case['input_sha256']
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result, events = analyse(json.loads(path.read_text()))
        result['started_utc'] = started
        if events is not None:
            (path.parent / 'enriched-trace.jsonl').write_text(to_jsonl(events) + '\n')
        save(path.parent / 'actual.json', result)
        actual = {m: v['exit'] for m, v in result.get('verdicts', {}).items()}
        discrepancy = {m: {'expected': code, 'actual': actual.get(m)} for m, code in ledger[case['name']].items() if actual.get(m) != code}
        rows.append({'name': case['name'], 'teacher_error': case['teacher_error'],
                     'expected': case['expected'], 'actual': actual, 'discrepancies': discrepancy,
                     'success': result['success'], 'artifact_directory': str(path.parent.relative_to(EVAL)),
                     'warnings': result['warnings']})
        print(case['name'], actual, 'DISCREPANCY' if discrepancy else 'as expected', flush=True)
    save(EVAL / 'results/behaviour.json', {'cases': rows, 'discrepancy_case_count': sum(bool(r['discrepancies']) for r in rows)})
    if any(r['discrepancies'] or not r['success'] for r in rows):
        raise SystemExit('Behavioural discrepancies or service failures retained in results/behaviour.json.')


if __name__ == '__main__':
    main()
