#!/usr/bin/env python3
"""Compile project RML, reproduce the Docker service layout, record environment."""
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / 'evaluation'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args):
    p = subprocess.run(args, text=True, capture_output=True)
    return {'argv': args, 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}


def main():
    for folder in ('metadata', 'compiled', 'runtime', 'results', 'artifacts'):
        (EVAL / folder).mkdir(exist_ok=True)
    compilation = []
    for source in sorted((ROOT / 'rml/metrics').glob('*.rml')):
        dest = EVAL / 'compiled' / (source.stem + '.pl')
        result = command(['java', '-cp', str(ROOT / 'vendor/rml-compiler/lib/*'),
                          'compiler.MainKt', '--input', str(source), '--output', str(dest)])
        result.update(source=str(source.relative_to(ROOT)), source_sha256=digest(source))
        if dest.exists():
            result['compiled_sha256'] = digest(dest)
        compilation.append(result)
    (EVAL / 'metadata/compilation.json').write_text(json.dumps(compilation, indent=2) + '\n')
    if len(compilation) != 7 or any(r['returncode'] != 0 for r in compilation):
        raise SystemExit('Compilation failed: see metadata/compilation.json')
    copies = {}
    for source in ('server/alignment/server.py', 'server/alignment/join.py', 'server/batch.pl'):
        src = ROOT / source
        dst = EVAL / 'runtime' / src.name
        shutil.copyfile(src, dst)
        assert digest(src) == digest(dst)
        copies[source] = digest(src)
    limits = {}
    for name in sorted(n for n in dir(resource) if n.startswith('RLIMIT_')):
        limits[name] = list(resource.getrlimit(getattr(resource, name)))
    optional = {}
    for path in ('/etc/os-release', '/proc/meminfo', '/proc/cpuinfo', '/proc/loadavg', '/proc/self/cgroup',
                 '/sys/fs/cgroup/cpu.max', '/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory.high'):
        if Path(path).exists():
            optional[path] = Path(path).read_text()
    sw = {p.metadata['Name']: p.version for p in importlib.metadata.distributions()}
    env = {
        'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'platform': platform.platform(), 'uname': list(platform.uname()),
        'python': sys.version, 'python_executable': sys.executable,
        'cpu_count': os.cpu_count(), 'cpu_affinity': sorted(os.sched_getaffinity(0)),
        'resource_limits': limits, 'proc_and_cgroup': optional,
        'clock': vars(__import__('time').get_clock_info('perf_counter')),
        'packages': dict(sorted(sw.items())), 'service_source_copies': copies,
        'runtime_commands': [command(x) for x in (['swipl', '--version'], ['java', '-version'],
                            ['node', '--version'], ['npm', '--version'], ['lscpu'])],
        'thread_environment': {key: os.environ.get(key) for key in
             ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS')},
        'runtime_layout': 'Byte-identical service/join/batch co-located as in server/Dockerfile; monitor and compiled spec paths passed through existing environment options.',
    }
    (EVAL / 'metadata/environment.json').write_text(json.dumps(env, indent=2) + '\n')
    freeze = command([sys.executable, '-m', 'pip', 'freeze'])
    (EVAL / 'metadata/python-freeze.txt').write_text(freeze['stdout'])
    print('Compiled 7 project specifications; staged byte-identical service and recorded environment.')


if __name__ == '__main__':
    main()
