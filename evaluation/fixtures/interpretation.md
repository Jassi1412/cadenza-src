# Original exercise and manual interpretation

`exercise.musicxml` is an original, two-measure, single-part fixture. It has
eight noteheads, seven score attacks, 4/4 metre, 100 divisions per quarter, and
quarter-note tempo 120 throughout. Beat numbers below start at zero. The service
uses the first part. The time column uses its own `ScoreModel.ms_at` map, which
is not an independent test of alignment correctness.

| Beat | Time (ms) | MIDI pitches | Written duration (beats) | Marking | Baseline played duration (ms) |
|---:|---:|---|---:|---|---:|
| 0 | 0 | C4 (60) | 1 | mf, staccato | 200 |
| 1 | 500 | D4 (62) | 1 | tenuto | 400 |
| 2 | 1000 | E4 (64) | 1 | pedal begins | 400 |
| 3 | 1500 | F4 (65) | 1 | none | 400 |
| 4 | 2000 | G4 (67), B4 (71) | 2 each | f, pedal ends | 400 each |
| 6 | 3000 | A4 (69) | 1 | none | 400 |
| 7 | 3500 | C5 (72) | 1 | none | 400 |

The mf segment is [0,4), with expected velocity 71.5; f is [4,8), with
expected velocity 87.5. Baseline integer velocities are 72 and 88. The baseline
pedal has CC64=127 at 1010 ms, then CC64=0 at 2000 ms. Its first attack at zero
sets an explicit synthetic score-time origin, including in the pre-attack-pedal case.
The live capture/playback clock relationship is outside this experiment; the
current capture/conversion path contains no explicit timestamp rebasing.
No random generation is used.

The initial parse with the isolated Partitura installation emitted
`ignoring direction type: metronome {}` for the visual metronome direction.
The accompanying `<sound tempo="120"/>` still supplies the implementation's
time map; the parsed anchors were (beat 0, 0 ms) and (beat 8, 4000 ms). Runners
should retain parser warnings in their diagnostics.

The written half-note chord is intentionally unmarked for articulation. The
implemented articulation check uses the gap to the **next performed attack**,
not the written duration. The fixture separates this from its chord-spread
tests. It also leaves the final attack unmarked. The archived original specification
attempted marked arithmetic before `noGap` and raised
`type_error(clpr_expression,null)` for the separate final-marked diagnostic.
The repaired RML places the existing `noGap` exemption first. The version-2 ledger
predicts acceptance for that diagnostic because the duration requirement is
inapplicable; it does not predict verification of the final duration. The old
frozen expectation ledger remains unchanged in both `results/` and the archive.
Only staccato and tenuto are claimed here; a MusicXML slur
is not assumed to become the `legato` articulation expected by the RML.

## Teacher-error labels

`teacher_error` is a declared pedagogical interpretation for this synthetic
exercise, not a judgement collected from teachers. Missing/replaced notes,
extra re-attacks, unplayable pitches and omitted pedal gestures count as errors.
For numerical boundary cases, use the implementation's dynamics band and
75%-of-next-attack articulation convention, a chord spread strictly below
30 ms, a pedal press after the relevant attack within 0.25 beat (125 ms), and a
release within +/-0.25 beat of the marked end. This explicit rubric permits
comparison with implementation outcomes without claiming these thresholds are
universal performance practice. Unmarked note lengths do not imply a separate
articulation requirement.

## A priori implementation predictions

`scripts/behaviour_cases.py` contains the complete manually reasoned expectation
ledger for every case and all seven specifications. Code 0 predicts acceptance;
1 predicts rejection. The service reserves 2 for runtime errors. The generator
does not call `join`, Prolog or a monitor, and predictions must be exported
before execution. The runner must retain all discrepancies, including runtime
errors, rather than change this ledger to fit observations.

The actual RML files and `server/alignment/join.py` are authoritative. The
metric README describes older definitions (including six rather than seven
metrics) and does not describe the current predicates accurately.

| Specification | Manually read obligation |
|---|---|
| pitch-range | Every performed note-on pitch is in inclusive [21,108]. |
| pitch-agreement | Every performed note-on has nearest sounding-score pitch distance zero; no obligation to perform every score note. |
| dynamics-adherence | A marked note-on velocity is within inclusive expected +/-8; unmarked note-ons pass. |
| articulation | The repaired `noGap` exemption is tried before numeric arithmetic; with no next gap this duration requirement is inapplicable. With a gap, staccato duration <=0.75 next-performed-attack gap; tenuto/legato >=0.75 gap. Unmarked attacks retain their exemption. |
| chord-jitter | A non-solo scored chord needs at least two performed note-ons with the same chordId and spread strictly <30 ms; no pitch-identity or general score-coverage test is added here. |
| pedal-toggle | Each CC64 gesture must be a press/release pair, with associated explicit score boundaries and RML beat distances <=0.25; no CC64 events pass vacuously. |
| syncopated-pedal | A region begins with one or more score-pedal note-ons, then a press, followed by score-pedal note-ons/noteoffs. No elapsed-time deadline or release requirement appears in this RML. |

An important composition boundary occurs before the pedal RML: `join` uses
`span_starting_at`/`span_ending_at` with inclusive epsilon 0.05 beat after
`snap_beat`, so the effective boundary association at 120 BPM is +/-25 ms.
A 26 ms press is within the RML's nominal +/-125 ms test but lacks
`spanExplicit=true` and should be rejected by pedal-toggle. Presses at
24/25/26 and 124/125/126 ms test both windows. The floating-point values 2.05
and 4.05 are represented with errors below 0.05 relative to the corresponding
integer in this fixture, so exactly +25 ms is expected to associate/snap.
The RML receives rounded `position.beat` values after that lookup. A 300 ms
late press before the first noteoff should still pass syncopated-pedal's order
test while failing pedal-toggle.

Missing F4 and the added E4 at beat 2.9 are teacher errors that the observation
model should accept: they leave the required local predicates satisfied.
A missing release should fail pedal-toggle while passing syncopated-pedal; removing the
whole pedal gesture reverses which obligation is violated. A press 10 ms
before the relevant attack should pass the boundary check but fail the
syncopated order check.

These predictions deliberately make no claim that an accepting trace realises
all musical requirements. Actual results are stored separately by the runner.
