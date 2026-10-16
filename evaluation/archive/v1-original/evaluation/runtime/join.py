import bisect
import json

import numpy as np
import partitura as pt

DYN_VELOCITY = {
    "ppp": 7.5, "pp": 23.5, "p": 39.5, "mp": 55.5, "mf": 71.5,
    "f": 87.5, "ff": 103.5, "fff": 119.5,
}


def _beat_of(part, t):
    b = float(part.beat_map(t))
    return b if np.isfinite(b) else None


class ScoreModel:
    def __init__(self, notes, dynamics, pedals, beat_grad, time_anchors):
        self.notes = notes
        self.dynamics = dynamics
        self.pedals = pedals
        self.beat_grad = beat_grad

        self._anch_beats = np.array([a[0] for a in time_anchors], dtype=float)
        self._anch_ms = np.array([a[1] for a in time_anchors], dtype=float)

        self._dyn_starts = [d["start"] for d in self.dynamics]
        self._dyn_ends = [d["end"] for d in self.dynamics]
        self._ped_starts = [p["start"] for p in self.pedals]

        self._onsets = sorted({n["onset"] for n in notes})
        self._group_pitches = {}
        for n in notes:
            self._group_pitches.setdefault(n["chordId"], []).append(n["pitch"])

        self._art = {}
        for n in notes:
            if n["articulation"] and n["onset"] not in self._art:
                self._art[n["onset"]] = n["articulation"]

    def articulation_at(self, beat):
        if not self._onsets:
            return None
        i = bisect.bisect_right(self._onsets, beat) - 1
        if i < 0:
            return None
        return self._art.get(self._onsets[i])

    @classmethod
    def from_musicxml(cls, path):
        score = pt.load_score(path)
        part = score[0]

        beat_grad = float(part.beat_map(1.0)) - float(part.beat_map(0.0))
        assert beat_grad > 0, "conversione t -> beat non riuscita"

        na = part.note_array()
        by_id = {str(r["id"]): r for r in na}
        notes = []
        for n in part.notes:
            r = by_id.get(str(n.id))
            if r is None:
                continue
            nota = {
                "id": str(n.id),
                "pitch": int(r["pitch"]),
                "onset": float(r["onset_beat"]),
                "duration": float(r["duration_beat"]),
                "voice": int(r["voice"]) if "voice" in r.dtype.names else 0,
                "articulation": str(n.articulations[0]) if n.articulations else None,
            }
            notes.append(nota)
        notes.sort(key=lambda x: (x["onset"], x["pitch"]))
        cls._propagate_articulations(notes)

        onsets = sorted({n["onset"] for n in notes})
        onset_id = {o: i for i, o in enumerate(onsets)}
        group_pitches = {}
        for n in notes:
            n["chordId"] = onset_id[n["onset"]]
            group_pitches.setdefault(n["chordId"], []).append(n["pitch"])
        for n in notes:
            mates = list(group_pitches[n["chordId"]])
            mates.remove(n["pitch"])
            n["chordMates"] = sorted(mates)

        dynamics = []
        for d in part.dynamics:
            if d.start is None or d.end is None:
                continue
            inizio, fine = _beat_of(part, d.start.t), _beat_of(part, d.end.t)
            if inizio is None or fine is None:
                continue
            dynamics.append({
                "start": inizio,
                "end": fine,
                "text": d.text,
                "velocity": DYN_VELOCITY.get(d.text, 80),
            })
        dynamics.sort(key=lambda x: x["start"])

        pedals = cls._read_pedals(path, part)

        for n in notes:
            e = cls._expected_at(dynamics, pedals, n["onset"])
            n["expected_dyn"] = e["dyn"]
            n["expected_pedal"] = e["pedal"]

        time_anchors = cls._build_time_anchors(part, path, beat_grad)

        return cls(notes, dynamics, pedals, beat_grad, time_anchors)

    @staticmethod
    def _read_tempos(path):
        from lxml import etree

        root = etree.parse(path).getroot()
        out, offset = [], 0.0
        for m in root.findall(".//measure"):
            cursor = 0.0
            for child in m:
                if child.tag == "note":
                    if child.find("chord") is None:
                        d = child.findtext("duration")
                        if d:
                            cursor += float(d)
                elif child.tag == "backup":
                    d = child.findtext("duration")
                    if d:
                        cursor -= float(d)
                elif child.tag == "direction":
                    s = child.find("sound")
                    if s is not None and s.get("tempo"):
                        out.append((offset + cursor, float(s.get("tempo"))))
            offset += cursor
        return out

    @classmethod
    def _build_time_anchors(cls, part, path, beat_grad):
        tempos = cls._read_tempos(path)
        if not tempos:
            tempos = [(0.0, 120.0)]

        qd = np.asarray(part.quarter_durations(), dtype=float)
        edges, durs = qd[:, 0].tolist(), qd[:, 1].tolist()

        def quarter_dur_at(t):
            q = durs[0]
            for c, d in zip(edges, durs):
                if c <= t:
                    q = d
                else:
                    break
            return q

        def bpm_at(t):
            cur = tempos[0][1]
            for tt, bb in tempos:
                if tt <= t:
                    cur = bb
                else:
                    break
            return cur

        def ms_between(t0, t1):
            cuts = [t0] + [c for c in edges if t0 < c < t1] + [t1]
            total = 0.0
            for i in range(len(cuts) - 1):
                a, b = cuts[i], cuts[i + 1]
                if b <= a:
                    continue
                mid = (a + b) / 2.0
                total += (b - a) / quarter_dur_at(mid) * (60000.0 / bpm_at(mid))
            return total

        anchors = [(0.0, 0.0)]
        ms = 0.0
        prev = 0.0
        for t, _bpm in tempos:
            if t <= 0.0:
                continue
            ms += ms_between(prev, t)
            battuta = _beat_of(part, t)
            if battuta is not None:
                anchors.append((battuta, ms))
            prev = t

        end_t = max(float(n.start.t) + float(n.duration) for n in part.notes)
        ms += ms_between(prev, end_t)
        end_beat = _beat_of(part, end_t)
        if end_beat is not None:
            anchors.append((end_beat, ms))
        return anchors

    def beat_at(self, score_ms):
        return float(np.interp(score_ms, self._anch_ms, self._anch_beats))

    def ms_at(self, beat):
        return float(np.interp(beat, self._anch_beats, self._anch_ms))

    @staticmethod
    def _propagate_articulations(notes):
        per_attacco = {}
        for n in notes:
            per_attacco.setdefault(n["onset"], []).append(n)
        for gruppo in per_attacco.values():
            presenti = {n["articulation"] for n in gruppo if n["articulation"]}
            if len(presenti) == 1:
                simbolo = presenti.pop()
                for n in gruppo:
                    if n["articulation"] is None:
                        n["articulation"] = simbolo

    @staticmethod
    def _read_pedals(path, part):
        from lxml import etree

        tree = etree.parse(path)
        root = tree.getroot()

        pedals, offset, open_at = [], 0.0, None
        for m in root.findall(".//measure"):
            cursor = 0.0
            for child in m:
                if child.tag == "note":
                    if child.find("chord") is None:
                        d = child.findtext("duration")
                        if d:
                            cursor += float(d)
                elif child.tag == "backup":
                    d = child.findtext("duration")
                    if d:
                        cursor -= float(d)
                elif child.tag == "direction":
                    for p in child.findall(".//pedal"):
                        at = _beat_of(part, offset + cursor)
                        if at is None:
                            continue
                        if p.get("type") == "start":
                            open_at = at
                        elif p.get("type") == "stop" and open_at is not None:
                            pedals.append({"start": open_at, "end": at})
                            open_at = None
            offset += cursor
        if open_at is not None:
            pedals.append({"start": open_at, "end": float("inf")})
        pedals.sort(key=lambda x: x["start"])
        return pedals

    @staticmethod
    def _expected_at(dynamics, pedals, beat):
        dyn = None
        for d in dynamics:
            if d["start"] <= beat < d["end"]:
                dyn = d
                break
        pedal = any(p["start"] <= beat < p["end"] for p in pedals)
        span = next((p for p in pedals if p["start"] <= beat < p["end"]), None)
        return {
            "dyn": dyn["velocity"] if dyn else None,
            "dyn_text": dyn["text"] if dyn else None,
            "pedal": pedal,
            "span": span,
        }

    def expected_at(self, beat):
        return self._expected_at(self.dynamics, self.pedals, beat)

    def span_starting_at(self, beat, eps=0.05):
        return next((p for p in self.pedals if abs(p["start"] - beat) <= eps), None)

    def span_ending_at(self, beat, eps=0.05):
        return next((p for p in self.pedals if abs(p["end"] - beat) <= eps), None)

    def measure_at(self, beat):
        return int(beat // 2) + 1

    def score_pitches_at(self, beat, tol=0.25):
        return [n["pitch"] for n in self.notes
                if n["onset"] - tol <= beat < n["onset"] + n["duration"]]

    def chord_at(self, beat):
        if not self._onsets:
            return None
        i = bisect.bisect_right(self._onsets, beat) - 1
        return i if i >= 0 else None

    def snap_beat(self, beat, eps=0.05):
        if not self._onsets:
            return beat
        i = bisect.bisect_left(self._onsets, beat)
        best, best_d = None, None
        for k in (i - 1, i, i + 1):
            if 0 <= k < len(self._onsets):
                d = abs(self._onsets[k] - beat)
                if best_d is None or d < best_d:
                    best, best_d = self._onsets[k], d
        return best if best_d is not None and best_d <= eps else beat

    def chord_mates(self, beat, pitch):
        cid = self.chord_at(beat)
        if cid is None:
            return []
        mates = list(self._group_pitches.get(cid, ()))
        if pitch in mates:
            mates.remove(pitch)
        return sorted(mates)

    def nearest(self, pitches, pitch):
        if not pitches:
            return None, None
        best = min(pitches, key=lambda q: (abs(q - pitch), q - pitch))
        return best, abs(pitch - best)


def join(model, performed_notes, tempo_factor=1.0, control_changes=None):
    if tempo_factor is None or not np.isfinite(tempo_factor) or tempo_factor <= 0:
        tempo_factor = 1.0

    attacchi = sorted({float(p["time_ms"]) for p in performed_notes})

    def prossimo_attacco(t):
        i = bisect.bisect_right(attacchi, t)
        return attacchi[i] if i < len(attacchi) else None

    events = []
    for p in performed_notes:
        t = p["time_ms"]

        score_t = t / tempo_factor

        beat = model.snap_beat(model.beat_at(score_t))

        expected_ms = model.ms_at(beat) * tempo_factor

        e = model.expected_at(beat)
        expected_pitches = model.score_pitches_at(beat)
        near_pitch, pitch_dist = model.nearest(expected_pitches, p["pitch"])
        chord_id = model.chord_at(beat)
        chord_mates = model.chord_mates(beat, near_pitch)

        prossimo = prossimo_attacco(t)

        expected = {
            "dyn": e["dyn"],
            "dynExplicit": e["dyn"] is not None,
            "dynText": e["dyn_text"],
            "pedal": e["pedal"],
            "spanExplicit": e["span"] is not None,
            "spanStart": e["span"]["start"] if e["span"] else None,
            "spanEnd": e["span"]["end"] if e["span"] else None,
            "pitch": near_pitch,
            "pitchDist": pitch_dist,
            "pitches": expected_pitches,
            "chordId": chord_id,
            "chordMates": chord_mates,
            "art": model.articulation_at(beat),
        }

        expected_on = ({**expected, "pitchDist": 127} if pitch_dist is None
                       else expected)

        events.append({
            "type": "noteon",
            "note": {"number": p["pitch"], "rawAttack": p["velocity"]},
            "timestamp": t,
            "position": {"beat": round(beat, 4), "measure": model.measure_at(beat)},
            "expected": expected_on,
            "timing": {"deltaMs": round(t - expected_ms, 2)},
            "durMs": round(float(p.get("dur_ms") or 0.0), 2),
            "gapMs": (None if prossimo is None else round(prossimo - t, 2)),
        })

        if p.get("dur_ms"):
            events.append({
                "type": "noteoff",
                "note": {"number": p["pitch"]},
                "timestamp": t + p["dur_ms"],
                "position": {"beat": round(beat, 4),
                             "measure": model.measure_at(beat)},
                "expected": expected,
                "timing": {"deltaMs": round(t + p["dur_ms"] - expected_ms, 2)},
            })

    for c in control_changes or []:
        t = c["time_ms"]
        beat = model.snap_beat(model.beat_at(t / tempo_factor))
        e = model.expected_at(beat)
        if c["controller"] == 64 and c["value"] == 127:
            span = model.span_starting_at(beat)
        elif c["controller"] == 64 and c["value"] == 0:
            span = model.span_ending_at(beat)
        else:
            span = e["span"]
        events.append({
            "type": "controlchange",
            "controller": c["controller"],
            "value": c["value"],
            "timestamp": t,
            "position": {"beat": round(beat, 4), "measure": model.measure_at(beat)},
            "expected": {
                "dyn": None,
                "dynExplicit": False,
                "dynText": None,
                "pedal": e["pedal"],
                "spanExplicit": span is not None,
                "spanStart": span["start"] if span else None,
                "spanEnd": span["end"] if span else None,
                "pitch": None,
                "pitchDist": None,
                "pitches": [],
                "chordId": model.chord_at(beat),
                "chordMates": [],
            },
            "timing": {},
        })

    events.sort(key=lambda x: x["timestamp"])
    return events


def to_jsonl(events):
    return "\n".join(json.dumps(e) for e in events)