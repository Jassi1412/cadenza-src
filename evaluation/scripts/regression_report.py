#!/usr/bin/env python3
"""Render the focused regression matrix directly from retained raw results."""
import hashlib
import json
from pathlib import Path


EVAL = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cell(row, version):
    return f"{row['expected_' + version]['articulation']}/{row['actual_' + version].get('articulation', 'missing')}"


def tex_escape(value):
    return value.replace('\\', r'\textbackslash{}').replace('_', r'\_').replace('%', r'\%').replace('&', r'\&')


def render(raw, ledger):
    cases = raw['cases']
    direct = [r for r in cases if r['kind'] == 'direct_monitor']
    complete = [r for r in cases if r['kind'] == 'converter_and_service']
    assert len(direct) == raw['direct_monitor_count']
    assert len(complete) == raw['converter_and_service_count']
    assert len(direct) + len(complete) == len(cases)
    assert raw['expectation_ledger_sha256'] == digest(EVAL / raw['expectation_ledger'])
    assert ledger['frozen_utc'] < raw['started_utc'] <= raw['completed_utc']
    expected_cases = {r['name']: r for r in ledger['cases']}
    assert len(expected_cases) == len(cases)
    other_checks = []
    for row in cases:
        expected = expected_cases[row['name']]
        for version in ('original', 'repaired'):
            assert row['expected_' + version] == expected['expected_' + version]
            path = EVAL / 'artifacts/regressions' / row['name'] / (version + '-actual.json')
            retained = json.loads(path.read_text())
            assert retained['actual'] == row['actual_' + version]
            assert retained['started_utc'] > ledger['frozen_utc']
            if row['kind'] == 'converter_and_service':
                other_checks.append(all(
                    code == 0 and row['actual_' + version].get(metric) == 0
                    for metric, code in expected['expected_' + version].items()
                    if metric != 'articulation'))
        if row['kind'] == 'direct_monitor':
            assert set(row['actual_original']) == set(row['actual_repaired']) == {'articulation'}
    others_ok = all(other_checks)
    changed = [r for r in cases if r['actual_changes']]
    successes = sum(bool(r['ok']) for r in cases)
    failed = len(cases) - successes
    assert failed == raw['discrepancy_case_count']
    all_match = successes == len(cases)
    service_statement = (
        f'All six other checks accepted in both versions for all {len(complete)} complete service cases '
        f'({len(other_checks)} checked version/case vectors).'
        if others_ok else
        'At least one complete service case has an unexpected outcome in the other six checks; inspect the raw vectors.')
    md = [
        '# Focused articulation regression results', '',
        f'{successes}/{len(cases)} additional regression cases matched their frozen original and repaired '
        f'outcome vectors; {failed} discrepancies. These cases remain separate from the original 28-case suite.', '',
        'Exit codes: **0** acceptance, **1** rejection, **2** monitor error. Each matrix cell is '
        '**expected/actual articulation exit code**. Original means the archived compiled RML; '
        'repaired means the current compiler-generated RML monitor.', '',
        '## Scope and interpretation', '',
        f'The {len(direct)} direct fixtures invoke only the actual compiled articulation monitor through '
        f'the project batch runner. The {len(complete)} complete cases encode and decode synthetic MIDI, '
        'call the actual browser `toPerformance` conversion and local `analyse` service, '
        'and execute all seven checks in a fresh Prolog process per request. '
        'Complete cases do not exercise live MIDI capture, HTTP transport or independent alignment.', '',
        service_statement + ' The saved original and repaired enriched service traces are byte-identical '
        'for each case.' if all(r['enrichment_identical'] for r in complete) else
        service_statement + ' An enriched trace differs between versions; inspect the raw traces.', '',
        'Final null-gap fixtures use a deliberately long **25,000 ms** duration for each supported '
        'monitor articulation (staccato, tenuto and legato) and for an unmarked event. '
        'Acceptance means that the next-attack duration requirement is **inapplicable**; '
        'the final duration has not been verified. The complete MusicXML/service path covers '
        'staccato, tenuto and unmarked final events.', '',
        'Numeric fixtures exercise 374, 375 and 376 ms at a 500 ms gap: '
        'staccato retains `duration <= 0.75 * gap`; tenuto and legato retain '
        '`duration >= 0.75 * gap`. Earlier violations still reject when followed by a marked '
        'null-gap event. Two malformed non-null operand controls retain exit 2 in both versions; '
        'arbitrary monitor errors have not been converted into acceptance.', '',
        raw['legato_service_limitation'], '',
        '## Frozen expectations and provenance', '',
        f'- [Separate expectation ledger]({raw["expectation_ledger"]}), manually frozen at '
        f'`{ledger["frozen_utc"]}` before regression monitor execution.',
        f'- Ledger SHA-256: `{raw["expectation_ledger_sha256"]}`.',
        f'- Execution: `{raw["started_utc"]}` to `{raw["completed_utc"]}`.',
        f'- Original compiled articulation SHA-256: `{raw["original_compiled_articulation_sha256"]}`.',
        f'- Repaired compiled articulation SHA-256: `{raw["repaired_compiled_articulation_sha256"]}`.',
        '- [Raw expected/actual vectors and comparison](results/regressions.json); '
        '[fixture notes](fixtures/regressions/README.md).', '',
        f'{len(changed)} additional cases change articulation from monitor error (2) to acceptance (0): '
        'the three marked direct null-gap cases and the staccato/tenuto complete final-null cases. '
        'These are the changes declared in advance in the separate regression ledger.', '',
    ]
    tex = ['% Generated by scripts/regression_report.py directly from results/regressions.json.',
           '% Cells are expected/actual articulation exit codes: 0 accept, 1 reject, 2 monitor error.',
           '% Direct cases run only articulation; service cases run all seven checks.',
           r'\begin{tabular}{lccc}', r'\hline',
           r'Case & Original E/A & Repaired E/A & Status \\', r'\hline']
    for title, rows in ((f'Direct compiled articulation monitor ({len(direct)} cases)', direct),
                        (f'Complete converter and service path ({len(complete)} cases)', complete)):
        md.extend(['## ' + title, '',
                   '| Case | Original E/A | Repaired E/A | Status | Retained evidence |',
                   '|---|---:|---:|---|---|'])
        tex.append(r'\multicolumn{4}{l}{' + tex_escape(title) + r'} \\')
        tex.append(r'\hline')
        for row in rows:
            name = row['name']
            folder = 'artifacts/regressions/' + name
            status = 'pass' if row['ok'] else 'DISCREPANCY'
            links = (f'[input]({row["input"]}); [artefacts]({folder}/); '
                     f'[original]({folder}/original-actual.json); [repaired]({folder}/repaired-actual.json)')
            md.append(f'| `{name}` | {cell(row, "original")} | {cell(row, "repaired")} | {status} | {links} |')
            short_name = name.removeprefix('direct_').removeprefix('service_')
            tex.append(tex_escape(short_name) + f' & {cell(row, "original")} & '
                       + cell(row, 'repaired') + ' & ' + status + r' \\')
        md.append('')
        tex.append(r'\hline')
    md.extend(['## Reproduce', '',
               'Run from the repository root, after compiling the repaired RML and preserving the archived original:', '',
               '```bash',
               'PYTHONDONTWRITEBYTECODE=1 evaluation/.venv/bin/python evaluation/scripts/regressions.py --generate-only',
               'PYTHONDONTWRITEBYTECODE=1 evaluation/.venv/bin/python evaluation/scripts/regressions.py --run',
               'PYTHONDONTWRITEBYTECODE=1 evaluation/.venv/bin/python evaluation/scripts/regression_report.py',
               '```', '',
               'Generation refuses to revise an existing frozen ledger. Raw results retain every '
               'original/repaired stdout, stderr, warning and verdict; the runner exits non-zero '
               'for an unexpected outcome or change. This document and the LaTeX matrix are derived '
               'from those saved results, without running monitors.', ''])
    tex.extend([r'\end{tabular}',
                '% All six other checks accept for every original/repaired service case.'
                if others_ok else '% WARNING: a service outcome in another check needs inspection.',
                '% Null-gap acceptance exempts this requirement; it does not verify final duration.',
                '% Literal legato has direct-monitor coverage only.', ''])
    return '\n'.join(md), '\n'.join(tex), all_match and others_ok


def main():
    raw = json.loads((EVAL / 'results/regressions.json').read_text())
    ledger = json.loads((EVAL / raw['expectation_ledger']).read_text())
    md, tex, ok = render(raw, ledger)
    (EVAL / 'REGRESSIONS.md').write_text(md)
    (EVAL / 'tables/regressions.tex').write_text(tex)
    print(f'Rendered {len(raw["cases"])} regression rows to REGRESSIONS.md and tables/regressions.tex.')
    if not ok:
        raise SystemExit('Regression discrepancies retained in rendered results.')


if __name__ == '__main__':
    main()
