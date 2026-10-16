"""Narrow publication exclusions; frozen scientific evidence remains required."""
import hashlib
import json
from pathlib import PurePosixPath


def project_file_required(path):
    """Exclude only publication Git settings, the source ZIP and Python caches."""
    relative = PurePosixPath(path)
    return not (path in ('.gitignore', '.gitattributes', 'archive.zip') or
                ('__pycache__' in relative.parts and relative.suffix == '.pyc'))


def _expendable_archive_file(path):
    relative = PurePosixPath(path)
    if path == 'project/archive.zip':
        return True
    if '__pycache__' in relative.parts and relative.suffix == '.pyc':
        return True
    if relative.parts[:1] == ('evaluation',) and relative.suffix == '.log':
        return True
    return (relative.parts[:3] == ('evaluation', 'artifacts', 'paper') and
            relative.suffix in ('.aux', '.log', '.pdf', '.png', '.txt'))


def _sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_archive_manifest(archive, manifest):
    """Hash all present files; allow only declared expendable files to be absent.

    The original manifest is never rewritten. Sharing declarations must identify
    an original manifest entry and repeat its exact digest and omission reason.
    The returned count includes only files whose bytes were actually verified.
    """
    declaration = archive / 'SHARING-EXCLUSIONS.json'
    excluded = {}
    if declaration.exists():
        payload = json.loads(declaration.read_text())
        excluded = payload['files']
        assert isinstance(excluded, dict), 'Sharing exclusions must be a path map'
        for path, details in excluded.items():
            assert path in manifest and _expendable_archive_file(path), path
            assert isinstance(details, dict), path
            assert details.get('sha256') == manifest[path], path
            assert isinstance(details.get('reason'), str) and details['reason'].strip(), path
    verified = 0
    for path, digest in manifest.items():
        archived_file = archive / path
        if not archived_file.exists():
            assert path in excluded, 'Required archived evidence missing: ' + path
            continue
        assert _sha(archived_file) == digest, 'Archived evidence changed: ' + path
        verified += 1
    return verified
