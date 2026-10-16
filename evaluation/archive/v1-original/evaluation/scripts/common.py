"""Evaluation adapters: all parsing, enrichment and verdicts call project code."""
import contextlib
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import types
import warnings

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / 'evaluation'
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS'):
    os.environ[key] = '1'
os.environ['RML_MONITOR'] = str(ROOT / 'rml/monitor')
os.environ['RML_SPECS'] = str(EVAL / 'compiled')
sys.path.insert(0, str(EVAL / 'runtime'))
service = importlib.import_module('server')
from join import ScoreModel, join, to_jsonl


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def midi_replay(folder, notes, cc, tempo_factor=1.0):
    """Encode synthetic MIDI, decode it, then call actual browser toPerformance."""
    import mido
    folder.mkdir(parents=True, exist_ok=True)
    # 1000 ticks per beat at 500000 us/beat -> exactly two ticks per ms.
    # Absolute tick quantisation is round-to-nearest; all fixtures use 0.5ms grid.
    events = []
    for n in notes:
        events.append((n['time_ms'], mido.Message('note_on', note=n['pitch'], velocity=n['velocity'])))
        events.append((n['time_ms'] + n['dur_ms'], mido.Message('note_off', note=n['pitch'], velocity=0)))
    for c in cc:
        events.append((c['time_ms'], mido.Message('control_change', control=c['controller'], value=c['value'])))
    events.sort(key=lambda e: e[0])
    if events and events[0][0] < 0:
        raise ValueError('MIDI cannot encode a negative absolute onset')
    midi = mido.MidiFile(type=0, ticks_per_beat=1000)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))
    last = 0
    for t, message in events:
        tick = round(t * 2)
        track.append(message.copy(time=tick - last))
        last = tick
    midi.save(folder / 'performance.mid')
    decoded, t = [], 0.0
    for message in mido.MidiFile(folder / 'performance.mid'):
        t += message.time * 1000
        if message.type in ('note_on', 'note_off'):
            decoded.append({'type': 'noteon' if message.type == 'note_on' else 'noteoff',
                            'timestamp': round(t, 6), 'note': message.note,
                            'rawAttack': message.velocity, 'velocity': message.velocity / 127})
        elif message.type == 'control_change':
            decoded.append({'type': 'controlchange', 'timestamp': round(t, 6),
                            'controller': message.control, 'value': message.value})
    save(folder / 'midi-events.json', {'events': decoded, 'tempo_factor': tempo_factor})
    replay = subprocess.run(['node', str(EVAL / 'scripts/replay.mjs'),
                             str(folder / 'midi-events.json'), str(folder / 'browser-payload.json')],
                            capture_output=True, text=True, timeout=60)
    (folder / 'replay-stderr.txt').write_text(replay.stderr)
    replay.check_returncode()
    payload = json.loads((folder / 'browser-payload.json').read_text())
    return {k: payload[k] for k in ('notes', 'control_changes', 'tempo_factor')}, len(decoded)


def analyse(body, instrument=True):
    """Time the actual analyse call; wrappers delegate unchanged stages and retain diagnostics."""
    stages, process = {}, {}
    old_model, old_join, old_json, old_subprocess = service.ScoreModel, service.join, service.to_jsonl, service.subprocess

    def timed(key, fn):
        def call(*args, **kwargs):
            start = time.perf_counter_ns()
            try:
                result = fn(*args, **kwargs)
                if key == 'prolog_process':
                    process.update(returncode=result.returncode, stdout=result.stdout.decode(), stderr=result.stderr.decode())
                return result
            finally:
                stages[key] = (time.perf_counter_ns() - start) / 1e9
        return call

    if instrument:
        service.ScoreModel = types.SimpleNamespace(from_musicxml=timed('score_parse', old_model.from_musicxml))
        service.join = timed('join', old_join)
        service.to_jsonl = timed('trace_serialise', old_json)
        service.subprocess = types.SimpleNamespace(run=timed('prolog_process', old_subprocess.run), PIPE=old_subprocess.PIPE)
    result = {'success': False}
    errout, stdout = io.StringIO(), io.StringIO()
    with warnings.catch_warnings(record=True) as caught, contextlib.redirect_stderr(errout), contextlib.redirect_stdout(stdout):
        warnings.simplefilter('always')
        start = time.perf_counter_ns()
        try:
            verdicts, events = service.analyse(body)
            elapsed = time.perf_counter_ns() - start
            result.update(success=True, verdicts={k: {'ok': v[0], 'exit': v[1], 'diagnostic': v[2]} for k, v in verdicts.items()},
                          enriched_event_count=len(events))
        except Exception as exc:
            elapsed = time.perf_counter_ns() - start
            events = None
            result.update(exception=type(exc).__name__, exception_message=str(exc), traceback=traceback.format_exc())
        finally:
            service.ScoreModel, service.join, service.to_jsonl, service.subprocess = old_model, old_join, old_json, old_subprocess
    result.update(total_seconds=elapsed / 1e9, stages_seconds=stages, process=process,
                  warnings=[{'category': w.category.__name__, 'message': str(w.message)} for w in caught],
                  python_stderr=errout.getvalue(), python_stdout=stdout.getvalue())
    return result, events
