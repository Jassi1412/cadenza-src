#!/usr/bin/env python3
"""Reproduce the saved defect with the archived original compiled specifications."""
import datetime
import json
from common import EVAL, analyse, save, service, sha, to_jsonl


def main():
    archive = EVAL / 'archive/v1-original'
    path = archive / 'evaluation/artifacts/behaviour/final_marked_note/service-input.json'
    old_specs = service.SPECS
    service.SPECS = str(archive / 'evaluation/compiled')
    try:
        result, events = analyse(json.loads(path.read_text()))
    finally:
        service.SPECS = old_specs
    result.update(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  input=str(path.relative_to(EVAL)), input_sha256=sha(path),
                  original_rml_sha256=sha(archive / 'project/rml/metrics/articulation.rml'),
                  original_compiled_sha256=sha(archive / 'evaluation/compiled/articulation.pl'),
                  interpretation='Original numeric marked-note branch structurally matches gapMs:null; CLP(R) raises before the later noGap alternative. Compiler preserves RML ordering.')
    save(EVAL / 'diagnostics/null-gap-original-reproduction.json', result)
    if events is not None:
        (EVAL / 'diagnostics/null-gap-original-trace.jsonl').write_text(to_jsonl(events) + '\n')
    assert result['success']
    assert result['verdicts']['articulation']['exit'] == 2
    assert 'clpr_expression' in result['process']['stderr'] and 'null' in result['process']['stderr']
    assert all(v['exit'] == 0 for m, v in result['verdicts'].items() if m != 'articulation')
    print('Original input reproduced articulation exit2 and clpr_expression/null; other six metrics accept.')


if __name__ == '__main__':
    main()
