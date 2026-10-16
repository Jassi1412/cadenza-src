#!/usr/bin/env python3
"""Sequential actual analyse calls, 3 warm-ups plus 30 measured runs per workload."""
import csv
import datetime
import json
import time
from common import EVAL, analyse, save, sha, to_jsonl


def main():
    workloads = json.loads((EVAL / 'results/workloads.json').read_text())['workloads']
    output = EVAL / 'results/timings.jsonl'
    output.write_text('')
    csvrows = []
    for workload in workloads:
        path = EVAL / workload['input']
        assert sha(path) == workload['input_sha256']
        body = json.loads(path.read_text())
        plain, plain_events = None, None
        for index in range(33):
            phase = 'warmup' if index < 3 else 'measured'
            started = datetime.datetime.now(datetime.timezone.utc).isoformat()
            # The first of exactly three warm-ups is uninstrumented; the second
            # checks that the delegating timers preserve success, verdicts and trace.
            result, events = analyse(body, instrument=index != 0)
            result.update(workload=workload['name'], phase=phase,
                          index=index if phase == 'warmup' else index - 3, started_utc=started,
                          instrumented=index != 0)
            if index == 0:
                plain, plain_events = result, events
                if events is not None:
                    (path.parent / 'enriched-trace.jsonl').write_text(to_jsonl(events) + '\n')
            if index == 1:
                assert plain['success'] == result['success'], 'Instrumentation changed success'
                if plain['success']:
                    assert plain['verdicts'] == result['verdicts'] and plain_events == events, 'Instrumentation changed result'
                else:
                    assert plain['exception'] == result['exception'], 'Instrumentation changed exception'
            with output.open('a') as f:
                f.write(json.dumps(result, allow_nan=False) + '\n')
            csvrows.append({'workload': workload['name'], 'phase': phase, 'index': result['index'],
                            'total_seconds': result['total_seconds'], 'success': result['success'],
                            **result['stages_seconds'],
                            **{m + '_exit': v['exit'] for m, v in result.get('verdicts', {}).items()}})
            print(workload['name'], phase, result['index'], f"{result['total_seconds']:.6f}s", flush=True)
    keys = list(dict.fromkeys(k for row in csvrows for k in row))
    with (EVAL / 'results/timings.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(csvrows)


if __name__ == '__main__':
    main()
