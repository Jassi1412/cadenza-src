# Implementation inspected for this evaluation

This document records source-level interpretation. Experimental outcomes and timing
measurements belong in the generated results; statements below do not assert that
a particular performance has been executed successfully.

## Browser input boundary

`useMidi` forwards event timestamps ([useMidi.ts](../web-app/src/hooks/useMidi.ts)),
and `ScorePage` supplies the recording directly to `useVerdict`
([ScorePage.tsx:68](../web-app/src/pages/ScorePage.tsx#L68)). The exported
`toPerformance` pairs note attacks/releases, retains attack timestamps and control
changes, and constructs the service payload
([useVerdict.ts](../web-app/src/hooks/useVerdict.ts)). No explicit playback-start
timestamp rebasing appears in this path. Synthetic inputs already have the intended
score-relative origin, so these experiments exercise the actual converter but
leave live capture/playback clock alignment unvalidated. Recording capture and
React lifecycle behaviour are outside the replay boundary.

## Current properties

The service runs seven specifications, in the order listed in
[server.py:19](../server/alignment/server.py#L19). The properties consume enriched
events produced by the original alignment code, rather than raw MIDI messages.
`noteon` filters ignore other event types for the first five properties in the
table. The two pedal properties inspect the combined event stream.

| Specification | Operational acceptance condition | Source |
|---|---|---|
| `pitch-range` | Every performed attack has MIDI pitch 21–108, inclusive. | [pitch-range.rml:2](../rml/metrics/pitch-range.rml#L2) |
| `pitch-agreement` | Every attack has enriched `pitchDist == 0`. The specification also accepts null distances, but the service replaces a missing attack distance with 127. | [pitch-agreement.rml:1](../rml/metrics/pitch-agreement.rml#L1), [join.py:361](../server/alignment/join.py#L361) |
| `dynamics-adherence` | For an explicit dynamic, velocity is within eight units of the target, inclusive. Attacks without an explicit dynamic pass. | [dynamics-adherence.rml:2](../rml/metrics/dynamics-adherence.rml#L2) |
| `articulation` | Staccato requires performed duration ≤0.75 times the gap to the next distinct performed attack; tenuto and legato require ≥0.75 times that gap. Unmarked attacks and attacks without a next gap have accepting alternatives, subject to the null-arithmetic defect below. | [articulation.rml:1](../rml/metrics/articulation.rml#L1) |
| `chord-jitter` | A solo-labelled attack passes alone. Otherwise, a group requires at least two consecutive attacks with the same enriched chord ID; subsequent members must be strictly less than 30 ms from the first. It does not count expected members or require distinct pitches. | [chord-jitter.rml:2](../rml/metrics/chord-jitter.rml#L2) |
| `pedal-toggle` | CC64 press value 127 and release value 0 must alternate as complete pairs. Each must have an explicit endpoint annotation and lie within 0.25 beat of it, inclusive. While a pair is open, only noteon/noteoff filler is accepted. Endpoint annotation imposes a narrower condition, described below. | [pedal-toggle.rml:4](../rml/metrics/pedal-toggle.rml#L4) |
| `syncopated-pedal` | One or more pedal-marked attacks precede a CC64 press, followed by pedal-marked attacks and/or noteoffs. Plain attacks, noteoffs and pedal releases can occur outside such regions. There is no timestamp comparison or millisecond tolerance. | [syncopated-pedal.rml:2](../rml/metrics/syncopated-pedal.rml#L2) |

Dynamic targets are `ppp=7.5`, `pp=23.5`, `p=39.5`, `mp=55.5`, `mf=71.5`,
`f=87.5`, `ff=103.5`, and `fff=119.5`; an unrecognised dynamic text defaults
to 80 ([join.py:7](../server/alignment/join.py#L7),
[join.py:88](../server/alignment/join.py#L88)). With integer MIDI velocities,
the half-integer targets and inclusive ±8 constraint should be considered when
choosing boundary cases.

## Score interpretation and observation limits

`ScoreModel.from_musicxml` loads the score using Partitura and selects only its
first part. It obtains note-array IDs and retains corresponding note objects,
then groups equal onsets into chord IDs
([join.py:51](../server/alignment/join.py#L51)). Thus XML note-element counts,
pitched-note counts and the number of parsed sounding notes can differ, including
through ties. The repository's Zelda score has 216 pitched XML notes and 16 rests.
The Merry-Go-Round score has 2,418 pitched XML notes, 69 rests, and 94 tie starts
and stops. Subtracting the 94 continuations suggests 2,324 sounding notes; the
evaluation must record the actual `ScoreModel` counts rather than assume this
arithmetic establishes parser behaviour.

Performance time is divided by `tempo_factor`, converted to beats through the
implementation's score timing map and snapped to a score onset within 0.05 beat
([join.py:289](../server/alignment/join.py#L289),
[join.py:331](../server/alignment/join.py#L331)). Pitch candidates include notes
from 0.25 beat before their attack until their notated end. The closest pitch is
selected, breaking equal distances towards the lower pitch
([join.py:279](../server/alignment/join.py#L279),
[join.py:310](../server/alignment/join.py#L310)). This permits any active candidate
pitch, rather than requiring a one-to-one match with a particular score note.

The trace contains observations derived from performed notes; it contains no
separate event for an omitted score obligation. Consequently, a missing solo or
an entirely omitted chord can pass. A remaining singleton from a partially
omitted chord can fail `chord-jitter`, but this is not a general completeness
check. Duplicate solo attacks can pass; repeated chord pitches can supply the
required second event without supplying a missing pitch. These are observation
limits that should remain visible even when a teacher would identify errors.

Articulation uses the next *distinct performed onset*, shared by simultaneous
attacks, and the supplied performed duration
([join.py:321](../server/alignment/join.py#L321),
[join.py:371](../server/alignment/join.py#L371)). It does not directly compare
duration with the notated note length. Missing notes and chord onset spread can
therefore change its duration threshold. Supported non-null marks are exactly
`staccato`, `tenuto` and `legato`; other strings have no dedicated accepting
branch. A single articulation is propagated to otherwise unmarked notes at the
same score onset ([join.py:202](../server/alignment/join.py#L202)).

The timing map is constructed from a handwritten MusicXML tempo scan and linear
interpolation ([join.py:114](../server/alignment/join.py#L114),
[join.py:196](../server/alignment/join.py#L196)). The scan advances on non-chord
notes and backups, but does not handle `forward` elements or direction offsets;
it scans all measures despite selecting the first Partitura part. Times outside
the interpolation anchors are clamped to their endpoints. These are limitations
of the inspected mapping, not independently validated alignment behaviour.
Synthetic workloads generated from this map explicitly depend on the system
under test. Reported measure numbers also assume two beats per measure
([join.py:276](../server/alignment/join.py#L276)).

## Pedal boundaries and defects

The nominal `pedal-toggle` tolerance is ±0.25 beat, but a CC64 press receives its
explicit span annotation only when its mapped beat is within 0.05 beat of the
span start; release uses the corresponding end test
([join.py:270](../server/alignment/join.py#L270),
[join.py:386](../server/alignment/join.py#L386)). Snapping happens first, and the
event beat is subsequently rounded to four decimals. Therefore the nominal RML
tolerance is not the effective end-to-end tolerance. For endpoints that coincide
with otherwise isolated score attacks at 120 beats/minute, ±0.05 beat corresponds
to ±25 ms before accounting for floating-point comparisons. Endpoint clamping
can create further exceptions, especially outside the score's time range.

`pedal-toggle` accepts a trace with no CC64 events: it does not require a pair
for every notated span. Once a press has been observed, a missing release leaves
an incomplete pair and should reject at end of trace. `syncopated-pedal` does not
require release. A press before the first relevant attack has no accepting
branch; a delayed press can satisfy the region without any upper time bound.
This differs from the README's historical 200 ms claim. Other controller values
and events may also be rejected because the pedal languages enumerate their
accepted stream shapes.

For a final attack marked staccato, tenuto or legato, enrichment supplies
`gapMs:null`. Its arithmetic branch is attempted before `noGap`; CLP(R) cannot
evaluate `0.75 * null` and raises a type error. The source-level expected outcome
is a monitor error, rather than the intended no-gap exemption
([articulation.rml:1](../rml/metrics/articulation.rml#L1),
[join.py:372](../server/alignment/join.py#L372)). The evaluation should preserve
this original and exercise it separately from a baseline ending on an unmarked
attack.

## Monitor semantics and diagnostics

The monitor uses deterministic, committed transitions: union selects the first
branch that accepts the current event; concatenation consumes the left branch
when it can, without later backtracking to reconsider a rejected suffix
([trace_expressions_semantics.pl:27](../rml/monitor/trace_expressions_semantics.pl#L27)).
End-of-trace acceptance requires `may_halt`. The service batch returns per-metric
code 0 for acceptance, 1 for rejection and 2 for caught errors
([batch.pl:25](../server/batch.pl#L25),
[batch.pl:45](../server/batch.pl#L45)). These are finite-trace results, not a
four-valued runtime-verification interface. Early rejection stops parsing for
that metric, so timing samples cannot be described as full-trace or worst-case
costs for every specification.

The Python service records empty diagnostic strings for all emitted metric
lines, including code 2. It uses the final 400 stderr characters only when a
metric line is missing ([server.py:82](../server/alignment/server.py#L82)). A
reproducible harness should retain the raw subprocess stdout/stderr in addition
to the unchanged service result, so caught Prolog errors remain inspectable.

## Service timing boundary and runtime layout

A direct call to the original `analyse(body)` includes validation/conversion of
the supplied fields; temporary directory creation; MusicXML writing; Partitura
parsing and score-model construction; joining/enrichment; JSONL serialisation
and writing; one new Prolog process; monitor/spec loading and the seven
sequential checks; subprocess output decoding and verdict assembly; and
temporary-file cleanup before return
([server.py:61](../server/alignment/server.py#L61)). The Prolog process opens the
trace once and seeks to its start before each specification
([batch.pl:5](../server/batch.pl#L5)). It is not one process per metric.

This boundary excludes browser capture, MIDI decoding, browser conversion,
HTTP/network transport, HTTP JSON decoding/response encoding, rendering and
ahead-of-time RML compilation. A benchmark process can keep Python imports and
the interpreter warm; each `analyse` still reparses the score and creates a new
Prolog process. Filesystem and operating-system caches may remain warm. Total
request durations must be timed independently from component-stage summaries.

The source-tree file layout differs from the deployed layout. `ROOT` is the
directory containing `server.py`, and the subprocess command expects
`ROOT/batch.pl` ([server.py:18](../server/alignment/server.py#L18),
[server.py:78](../server/alignment/server.py#L78)). Direct import from
`server/alignment` therefore points to a missing batch file. Docker deliberately
copies `server.py`, `join.py` and `batch.pl` together into `/opt`
([Dockerfile:41](../server/Dockerfile#L41)). The evaluation harness stages
byte-identical copies together in its isolated runtime directory and sets
`RML_MONITOR`/`RML_SPECS` to the original monitor and compiled specifications.
This reproduces the deployment layout without modifying application code.

## Documentation drift

[The metrics README](../rml/metrics/README.md) describes six older metrics,
including a fixed dynamics threshold of 80, a hard-coded C4/E4 chord, a 200 ms
pedal delay and a 30 ms articulation gap. Current source has seven metrics and
the score-aware conditions above. It also refers to historical `RML_DOCS` and
other files absent from this checkout. Its historical validation claims should
not be reused as results for this evaluation. The vendored compiler and current
sources are the executable artefacts used here.
