#!/usr/bin/env python3
"""Deterministic cases and a priori manual verdicts for the original exercise.

This module neither imports nor calls the join or monitor implementations. Its
only dependency on the supplied ScoreModel is inspection of the score and its
score-to-time map. Export and retain the returned expected ledger before running
the service. A runtime error must be recorded as an observed discrepancy, never
used to revise these manually reasoned expectations.
"""

from copy import deepcopy


METRICS = (
    "articulation", "chord-jitter", "dynamics-adherence", "pedal-toggle",
    "pitch-agreement", "pitch-range", "syncopated-pedal",
)


def build_cases(model):
    """Return independent {notes, control_changes, expected, ...} dictionaries.

    Verdicts use the service's codes: 0 = acceptance, 1 = rejection, 2 = runtime
    error. No errors are predicted by the RML-level manual reading; observed code
    2 results remain visible in the runner. Teacher labels follow the explicitly
    declared rubric in fixtures/interpretation.md, rather than a human study.
    """
    layout = [(0, 60), (1, 62), (2, 64), (3, 65), (4, 67), (4, 71), (6, 69), (7, 72)]
    actual = [(float(n["onset"]), int(n["pitch"])) for n in model.notes]
    if actual != layout:
        raise ValueError("build_cases requires evaluation/fixtures/exercise.musicxml")
    if abs(model.ms_at(1) - model.ms_at(0) - 500) > 1e-8:
        raise ValueError("exercise must map one beat to 500 ms")
    if [(p["start"], p["end"]) for p in model.pedals] != [(2, 4)]:
        raise ValueError("exercise must contain precisely pedal span [2, 4)")
    if [n["articulation"] for n in model.notes] != ["staccato", "tenuto", None, None, None, None, None, None]:
        raise ValueError("exercise articulation interpretation has changed")
    if [n["expected_dyn"] for n in model.notes] != [71.5] * 4 + [87.5] * 4:
        raise ValueError("exercise must expose mf then f in the score model")

    notes = [
        {"time_ms": model.ms_at(beat), "dur_ms": 200.0 if i == 0 else 400.0,
         "pitch": pitch, "velocity": 72 if beat < 4 else 88}
        for i, (beat, pitch) in enumerate(layout)
    ]
    controls = [
        {"time_ms": model.ms_at(2) + 10.0, "controller": 64, "value": 127},
        {"time_ms": model.ms_at(4), "controller": 64, "value": 0},
    ]
    cases = []

    def add(name, rationale, teacher_error=False, teacher_interpretation="Within the declared exercise tolerances.",
            rejected=(), changed_notes=None, changed_controls=None):
        cases.append({
            "name": name,
            "notes": deepcopy(notes if changed_notes is None else changed_notes),
            "control_changes": deepcopy(controls if changed_controls is None else changed_controls),
            "expected": {m: int(m in rejected) for m in METRICS},
            "teacher_error": bool(teacher_error),
            "teacher_interpretation": teacher_interpretation,
            "rationale": rationale,
            "expectation_basis": "Manual reading of repository RML and join.py before monitor execution; not inferred from observed verdicts.",
        })

    def note_change(index, **updates):
        out = deepcopy(notes)
        out[index].update(updates)
        return out

    add("baseline", "All pitches are in range and in the sounding score; velocities are within +/-8 of mf/f. "
        "Staccato 200 <= 375 ms and tenuto 400 >= 375 ms; unmarked attacks have no duration constraint. "
        "Both chord tones coincide. The pedal press follows the beat-2 attack by 10 ms and snaps to beat 2; "
        "the release is at beat 4. All seven specifications should accept.")
    add("wrong_pitch", "C-sharp4 replaces the first C4: nearest score pitch distance is 1, so only pitch-agreement rejects.",
        True, "A notated pitch is replaced.", ("pitch-agreement",), note_change(0, pitch=61))
    add("outside_range", "MIDI pitch 20 is below the inclusive [21,108] range and is not a score pitch; both pitch checks reject.",
        True, "The first note is outside an 88-key piano and replaces C4.",
        ("pitch-range", "pitch-agreement"), note_change(0, pitch=20))
    add("bad_velocity", "Velocity 40 is outside mf's [63.5,79.5] interval; only dynamics-adherence rejects.",
        True, "The mf attack is much too soft.", ("dynamics-adherence",), note_change(0, velocity=40))
    add("bad_articulation", "The first staccato lasts 450 ms, above 0.75 * the 500 ms next-attack gap (375 ms).",
        True, "The first staccato is held beyond the declared duration limit.",
        ("articulation",), note_change(0, dur_ms=450.0))

    for spread in (29, 30, 31):
        add(f"chord_spread_{spread}ms",
            f"The chord's B4 follows G4 by {spread} ms. Both retain chordId=4 and valid score pitches. "
            "chord-jitter requires abs(t2-t1) < 30, so equality rejects. Other marks are unaffected.",
            spread >= 30, "Chord spread is within the declared <30 ms tolerance." if spread < 30 else "Chord spread reaches or exceeds 30 ms.",
            () if spread < 30 else ("chord-jitter",), note_change(5, time_ms=model.ms_at(4) + spread))

    for delay in (24, 25, 26, 124, 125, 126):
        cc = deepcopy(controls)
        cc[0]["time_ms"] = model.ms_at(2) + delay
        accepted = delay <= 25
        add(f"pedal_press_{delay}ms",
            f"Press is {delay} ms after beat 2. At 120 BPM, join.py's span lookup has an effective +/-25 ms "
            "(0.05 beat) association window after onset snapping, narrower than RML's +/-125 ms (0.25 beat) test. "
            "At 25 ms the computed 2.05 beat is within floating-point epsilon of the inclusive boundary and snaps to 2. "
            "Beyond 25 ms spanExplicit is false, so pedal-toggle rejects even within its nominal tolerance. "
            "The press still follows notePedal before the first noteoff, so syncopated-pedal accepts.",
            delay > 125, "Pedal follows the relevant attack within the declared 125 ms tolerance." if delay <= 125 else "Pedal press is later than the declared 125 ms tolerance.",
            () if accepted else ("pedal-toggle",), changed_controls=cc)

    for delay in (25, 26):
        cc = deepcopy(controls)
        cc[1]["time_ms"] = model.ms_at(4) + delay
        add(f"pedal_release_late_{delay}ms",
            f"Release is {delay} ms after beat 4. At 25 ms, 4.05 is within the inclusive 0.05-beat "
            "span association/snap boundary; at 26 ms spanExplicit becomes false and pedal-toggle rejects. "
            "syncopated-pedal imposes no release deadline. Other specifications are unaffected.",
            False, "Release is within the declared +/-125 ms tolerance.",
            () if delay == 25 else ("pedal-toggle",), changed_controls=cc)

    add("missing_note", "F4 at beat 3 is absent. No score-to-performance coverage obligation is generated. "
        "E4 still opens the pedal region and both chord tones remain, so all seven specifications accept.",
        True, "A required score note is omitted.", changed_notes=[n for i, n in enumerate(notes) if i != 3])
    duplicate = deepcopy(notes)
    duplicate.append({"time_ms": model.ms_at(2) + 450, "dur_ms": 20.0, "pitch": 64, "velocity": 72})
    duplicate.sort(key=lambda n: (n["time_ms"], n["pitch"]))
    add("duplicate_note", "E4 is re-attacked at beat 2.9 after its first release. E4 is still in the score's "
        "sounding interval; the added attack is unmarked, solo and inside the open pedal region. No uniqueness "
        "or one-to-one matching requirement exists, so all seven specifications accept.",
        True, "An extra E4 re-attack is inserted.", changed_notes=duplicate)
    add("missing_release", "The pedal press has no release. pedal-toggle cannot finish Toggle=press filler* release "
        "and rejects. syncopated-pedal requires the post-attack press but does not require a release.",
        True, "Pedal release at the end of the marked region is omitted.", ("pedal-toggle",), changed_controls=controls[:1])
    cc = deepcopy(controls)
    cc[0]["time_ms"] = model.ms_at(2) - 10
    add("pre_attack", "The press precedes E4 by 10 ms but snaps to beat 2, so pedal-toggle accepts its "
        "boundary association. syncopated-pedal encounters a pedalPress before notePedal and rejects it.",
        True, "Syncopated pedal is activated before the relevant attack.", ("syncopated-pedal",), changed_controls=cc)
    add("pedal_all_absent", "Without any CC64 events, pedal-toggle accepts other*. The scored-pedal notes "
        "still require a subsequent press in syncopated-pedal, which rejects. Absence is not an error for the toggle-only obligation.",
        True, "The entire notated pedal region is omitted.", ("syncopated-pedal",), changed_controls=[])
    cc = deepcopy(controls)
    cc[0]["time_ms"] = model.ms_at(2) + 300
    add("late_press_300ms", "The 300 ms delayed press precedes E4's noteoff at 1400 ms. syncopated-pedal "
        "checks event ordering without a millisecond bound and accepts. The press has no associated span start, so pedal-toggle rejects.",
        True, "Pedal press is 300 ms late, beyond the declared 125 ms tolerance.", ("pedal-toggle",), changed_controls=cc)
    add("staccato_375ms", "First duration equals 0.75 * its 500 ms next-attack gap. "
        "staccatoOk uses <=, including equality at 375 ms.",
        changed_notes=note_change(0, dur_ms=375.0))
    for duration in (374, 375):
        add(f"tenuto_{duration}ms", f"Second duration is {duration} ms with a 500 ms next-attack gap. "
            "tenutoOk uses d >= 0.75*g, including equality at 375 ms.",
            duration < 375, "Tenuto falls short of 375 ms." if duration < 375 else "Tenuto meets the declared >=375 ms limit.",
            ("articulation",) if duration < 375 else (), note_change(1, dur_ms=float(duration)))

    for velocity in (64, 80):
        accepted = 64 <= velocity <= 79
        add(f"mf_velocity_{velocity}", f"First velocity is {velocity}; the mf centre is 71.5 and the RML interval is "
            "inclusive [63.5,79.5]. MIDI's integer velocities can test adjacent values but cannot equal the half-integer limits.",
            not accepted, "Velocity lies in the declared mf interval." if accepted else "Velocity lies outside the declared mf interval.",
            () if accepted else ("dynamics-adherence",), note_change(0, velocity=velocity))

    return cases
