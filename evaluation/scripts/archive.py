#!/usr/bin/env python3
"""Preserve active evidence before a rerun; the immutable v1 archive is retained."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / 'evaluation'


def main():
    if not (EVAL / 'archive/v1-original/MANIFEST.json').is_file():
        raise SystemExit('The original version-1 archive must be present; refusing to overwrite evidence without it.')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination = EVAL / 'archive' / ('rerun-before-' + stamp)
    destination.mkdir()
    def ignore(folder, names):
        return [name for name in names if name in ('archive', '.venv', 'node_modules', '__pycache__')]
    for path in sorted(EVAL.iterdir()):
        if path.name in ('archive', '.venv'):
            continue
        target = destination / 'evaluation' / path.name
        if path.is_dir():
            shutil.copytree(path, target, ignore=ignore)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    for folder, pattern in (('rml/metrics', '*.rml'), ('server/alignment', '*.py'), ('server', '*.pl')):
        for source in sorted((ROOT / folder).glob(pattern)):
            target = destination / 'project' / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    manifest = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(destination.rglob('*')) if p.is_file()}
    (destination / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    assert all(hashlib.sha256((destination / path).read_bytes()).hexdigest() == digest for path, digest in manifest.items())
    print(f'Archived and verified {len(manifest)} files in {destination.relative_to(ROOT)}; original full project snapshot remains in archive/v1-original.')


if __name__ == '__main__':
    main()
