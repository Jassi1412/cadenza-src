#!/usr/bin/env python3
"""Retain standalone original-monitor diagnostics separately from timed calls."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / 'evaluation'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((EVAL / 'results/workloads.json').read_text())
    monitor = ROOT / 'rml/monitor/monitor.pl'
    spec = EVAL / 'compiled/syncopated-pedal.pl'
    rows = []
    for workload in manifest['workloads']:
        folder = (EVAL / workload['input']).parent
        trace = folder / 'enriched-trace.jsonl'
        command = ['swipl', '-O', '-p', f'monitor={ROOT / "rml/monitor"}',
                   str(monitor), '--', str(spec), str(trace)]
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        unmatched = re.search(r'^unmatched event #(\d+): (.*)$', result.stdout, re.MULTILINE)
        matched = re.findall(r'^matched event #(\d+): (.*)$', result.stdout, re.MULTILINE)
        count = sum(bool(line.strip()) for line in trace.read_text().splitlines())
        index = int(unmatched.group(1)) if unmatched else None
        rows.append({
            'workload': workload['name'], 'started_utc': started,
            'command': command, 'returncode': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr,
            'trace': str(trace.relative_to(EVAL)), 'trace_sha256': sha(trace),
            'trace_event_count': count, 'unmatched_event_index': index,
            'unmatched_event_printed': unmatched.group(2) if unmatched else None,
            'last_matched_event_index': int(matched[-1][0]) if matched else None,
            'last_matched_event_printed': matched[-1][1] if matched else None,
            'rejected_before_end': result.returncode == 1 and index is not None and index < count,
            'specification': str(spec.relative_to(EVAL)), 'specification_sha256': sha(spec),
        })
    payload = {
        'purpose': 'Locate original-monitor rejection events on the saved workload traces.',
        'separate_from_timing': True,
        'method': 'Unchanged standalone monitor.pl, using the same compiled specification and '
                  'trace_expressions_semantics.pl as the timed batch path. Event indices are '
                  'extracted only from the original monitor printed diagnostics; no replacement '
                  'matching or monitoring logic is used.',
        'monitor_source': str(monitor.relative_to(ROOT)), 'monitor_sha256': sha(monitor),
        'monitor_transition_call_line': 99, 'monitor_rejection_reporting_line': 101,
        'timed_batch_transition_call': {'source': 'server/batch.pl', 'line': 56},
        'workloads': rows,
    }
    output = EVAL / 'diagnostics/early-rejection.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n')
    for row in rows:
        print(f"{row['workload']}: exit {row['returncode']}, unmatched event "
              f"{row['unmatched_event_index']}/{row['trace_event_count']}; "
              f"early rejection={row['rejected_before_end']}")


if __name__ == '__main__':
    main()
