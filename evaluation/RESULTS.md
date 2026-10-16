# Results generated from local raw data

All performances are deterministic synthetic MIDI. Raw inputs are `results/workloads.json`, `results/behaviour.json` and `results/timings.jsonl`.

Durations are seconds. Quartiles use NumPy percentile with `method="linear"`. Warm-ups are excluded from timing statistics. Every measured run contributes its total duration, including service failures and timeouts; no outliers are discarded. Timeouts are a subset of service failures. Monitor errors (exit 2) are counted separately.

Generated events count decoded MIDI noteon, noteoff and control-change messages; the enriched trace count is reported separately.

| Workload | Parsed notes | MIDI events | Enriched events | Warm-ups | Measured | Median | Q1 | Q3 | Min | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| score-2324 | 2324 | 4946 | 4946 | 3 | 30 | 6.037239 | 5.956440 | 6.375752 | 5.754788 | 6.750570 |
| score-216 | 216 | 464 | 464 | 3 | 30 | 0.779284 | 0.758785 | 0.799557 | 0.726207 | 0.868918 |

## Failures, errors and warnings

| Workload | Service failures | Timeouts | Runs with monitor error | Warning occurrences | Runs with Prolog stderr | Generation warnings |
|---|---:|---:|---:|---:|---:|---:|
| score-2324 | 0 | 0 | 0 | 720 | 30 | 24 |
| score-216 | 0 | 0 | 0 | 30 | 30 | 1 |

- `score-2324`: score `scores/Merry-Go-Round of Life_ Howl's Moving Castle Piano Tutorial (3).musicxml`; SHA-256 `8bdc72bfdadcdca1730567ad8cd606fac323c588cac6548bb845b5754e4f92fd`.
  Warm-ups: 0 service failures, 0 timeouts, 0 runs with monitor errors, 72 warning occurrences.
  Measured warning (30 occurrences): UserWarning: Did not find a pedal start element for pedal stop!
  Measured warning (60 occurrences): UserWarning: error parsing "giocoso" (UnexpectedCharacters)
  Measured warning (30 occurrences): UserWarning: error parsing "poco rapido" (UnexpectedCharacters)
  Measured warning (30 occurrences): UserWarning: error parsing "rapido accel" (UnexpectedCharacters)
  Measured warning (30 occurrences): UserWarning: error parsing "rubarto" (UnexpectedCharacters)
  Measured warning (30 occurrences): UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'default-x': '-29.38', 'default-y': '66.70', 'relative-x': '-7.44', 'relative-y': '10.00'}
  Measured warning (30 occurrences): UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'default-x': '-36.00', 'default-y': '68.80', 'relative-x': '-22.50', 'relative-y': '20.00'}
  Measured warning (30 occurrences): UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'relative-x': '-5.00', 'relative-y': '15.00'}
  Measured warning (30 occurrences): UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'relative-y': '10.00'}
  Measured warning (30 occurrences): UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'relative-y': '20.00'}
  Measured warning (120 occurrences): UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'relative-y': '25.00'}
  Measured warning (60 occurrences): UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'relative-y': '30.00'}
  Measured warning (60 occurrences): UserWarning: unhandled: doppio movimento
  Measured warning (150 occurrences): UserWarning: unhandled: mezzo movimento
  Generation warning: UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'default-x': '-36.00', 'default-y': '68.80', 'relative-x': '-22.50', 'relative-y': '20.00'}
  Generation warning: UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'relative-y': '25.00'}
  Generation warning: UserWarning: unhandled: mezzo movimento
  Generation warning: UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'relative-y': '25.00'}
  Generation warning: UserWarning: error parsing "rubarto" (UnexpectedCharacters)
  Generation warning: UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'relative-y': '30.00'}
  Generation warning: UserWarning: unhandled: doppio movimento
  Generation warning: UserWarning: Did not find a pedal start element for pedal stop!
  Generation warning: UserWarning: error parsing "giocoso" (UnexpectedCharacters)
  Generation warning: UserWarning: unhandled: mezzo movimento
  Generation warning: UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'relative-y': '20.00'}
  Generation warning: UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'relative-y': '10.00'}
  Generation warning: UserWarning: unhandled: mezzo movimento
  Generation warning: UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'default-x': '-29.38', 'default-y': '66.70', 'relative-x': '-7.44', 'relative-y': '10.00'}
  Generation warning: UserWarning: error parsing "giocoso" (UnexpectedCharacters)
  Generation warning: UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'relative-y': '30.00'}
  Generation warning: UserWarning: error parsing "poco rapido" (UnexpectedCharacters)
  Generation warning: UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'relative-y': '25.00'}
  Generation warning: UserWarning: unhandled: doppio movimento
  Generation warning: UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'relative-x': '-5.00', 'relative-y': '15.00'}
  Generation warning: UserWarning: unhandled: mezzo movimento
  Generation warning: UserWarning: error parsing "rapido accel" (UnexpectedCharacters)
  Generation warning: UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'relative-y': '25.00'}
  Generation warning: UserWarning: unhandled: mezzo movimento

- `score-216`: score `scores/The Legend of Zelda_ Great Fairy Fountain (Piano Cover) - con dinamiche.musicxml`; SHA-256 `ace12e07d937988ef2e7a1e5b35618d73d5ba763bbc9de153af979eadc24c6fe`.
  Warm-ups: 0 service failures, 0 timeouts, 0 runs with monitor errors, 3 warning occurrences.
  Measured warning (30 occurrences): UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'default-x': '-68.04', 'default-y': '29.02', 'relative-y': '20.00'}
  Generation warning: UserWarning: ignoring direction type: metronome {'parentheses': 'no', 'default-x': '-68.04', 'default-y': '29.02', 'relative-y': '20.00'}

## Measured monitor outcomes

These are finite-trace exit codes: 0 acceptance, 1 rejection, 2 error. A metric may reject before reading the complete trace. Missing means no metric result was returned.

| Workload | Metric | Exit 0 | Exit 1 | Exit 2 | Missing |
|---|---|---:|---:|---:|---:|
| score-2324 | articulation | 30 | 0 | 0 | 0 |
| score-2324 | chord-jitter | 30 | 0 | 0 | 0 |
| score-2324 | dynamics-adherence | 30 | 0 | 0 | 0 |
| score-2324 | pedal-toggle | 30 | 0 | 0 | 0 |
| score-2324 | pitch-agreement | 30 | 0 | 0 | 0 |
| score-2324 | pitch-range | 30 | 0 | 0 | 0 |
| score-2324 | syncopated-pedal | 0 | 30 | 0 | 0 |
| score-216 | articulation | 30 | 0 | 0 | 0 |
| score-216 | chord-jitter | 30 | 0 | 0 | 0 |
| score-216 | dynamics-adherence | 30 | 0 | 0 | 0 |
| score-216 | pedal-toggle | 30 | 0 | 0 | 0 |
| score-216 | pitch-agreement | 30 | 0 | 0 | 0 |
| score-216 | pitch-range | 30 | 0 | 0 | 0 |
| score-216 | syncopated-pedal | 0 | 30 | 0 | 0 |

## Component timings

Each component is measured around the unchanged function or subprocess call. Component statistics include available samples, with their counts shown; they do not sum to the independently measured request time. `trace_serialise` excludes writing the file. `prolog_process` includes subprocess startup, the seven checks and output capture.

| Workload | Stage | Samples | Median | Q1 | Q3 | Min | Max |
|---|---|---:|---:|---:|---:|---:|---:|
| score-2324 | join | 30 | 0.516819 | 0.491985 | 0.546502 | 0.454786 | 0.670630 |
| score-2324 | prolog_process | 30 | 4.676406 | 4.574278 | 4.871705 | 4.400619 | 5.129402 |
| score-2324 | score_parse | 30 | 0.830184 | 0.792696 | 0.867083 | 0.760994 | 1.049654 |
| score-2324 | trace_serialise | 30 | 0.050387 | 0.047877 | 0.054454 | 0.046695 | 0.069422 |
| score-216 | join | 30 | 0.009201 | 0.008507 | 0.010111 | 0.007684 | 0.017341 |
| score-216 | prolog_process | 30 | 0.682557 | 0.672532 | 0.715160 | 0.640742 | 0.769670 |
| score-216 | score_parse | 30 | 0.070130 | 0.066826 | 0.075274 | 0.060857 | 0.112245 |
| score-216 | trace_serialise | 30 | 0.004722 | 0.004435 | 0.005209 | 0.004025 | 0.006512 |

## Behavioural validation

Executed 28 cases: 0 differ from the frozen manual expectations; 0 service failures; 0 cases with a monitor error; 28 warning occurrences.

Of 15 cases labelled as teacher errors, 2 were accepted by all seven metrics.

Cases accepted despite a teacher error: `missing_note`, `duplicate_note`.

Cells below are **expected/actual** exit codes. A=articulation, C=chord-jitter, D=dynamics-adherence, T=pedal-toggle, P=pitch-agreement, R=pitch-range, S=syncopated-pedal.

| Case | Teacher error | A | C | D | T | P | R | S | Discrepancy |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| baseline | no | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | no |
| wrong_pitch | yes | 0/0 | 0/0 | 0/0 | 0/0 | 1/1 | 0/0 | 0/0 | no |
| outside_range | yes | 0/0 | 0/0 | 0/0 | 0/0 | 1/1 | 1/1 | 0/0 | no |
| bad_velocity | yes | 0/0 | 0/0 | 1/1 | 0/0 | 0/0 | 0/0 | 0/0 | no |
| bad_articulation | yes | 1/1 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | no |
| chord_spread_29ms | no | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | no |
| chord_spread_30ms | yes | 0/0 | 1/1 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | no |
| chord_spread_31ms | yes | 0/0 | 1/1 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | no |
| pedal_press_24ms | no | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | no |
| pedal_press_25ms | no | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | no |
| pedal_press_26ms | no | 0/0 | 0/0 | 0/0 | 1/1 | 0/0 | 0/0 | 0/0 | no |
| pedal_press_124ms | no | 0/0 | 0/0 | 0/0 | 1/1 | 0/0 | 0/0 | 0/0 | no |
| pedal_press_125ms | no | 0/0 | 0/0 | 0/0 | 1/1 | 0/0 | 0/0 | 0/0 | no |
| pedal_press_126ms | yes | 0/0 | 0/0 | 0/0 | 1/1 | 0/0 | 0/0 | 0/0 | no |
| pedal_release_late_25ms | no | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | no |
| pedal_release_late_26ms | no | 0/0 | 0/0 | 0/0 | 1/1 | 0/0 | 0/0 | 0/0 | no |
| missing_note | yes | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | no |
| duplicate_note | yes | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | no |
| missing_release | yes | 0/0 | 0/0 | 0/0 | 1/1 | 0/0 | 0/0 | 0/0 | no |
| pre_attack | yes | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 1/1 | no |
| pedal_all_absent | yes | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 1/1 | no |
| late_press_300ms | yes | 0/0 | 0/0 | 0/0 | 1/1 | 0/0 | 0/0 | 0/0 | no |
| staccato_375ms | no | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | no |
| tenuto_374ms | yes | 1/1 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | no |
| tenuto_375ms | no | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | no |
| mf_velocity_64 | no | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | no |
| mf_velocity_80 | yes | 0/0 | 0/0 | 1/1 | 0/0 | 0/0 | 0/0 | 0/0 | no |
| final_marked_note | no | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | no |

These observations concern the evaluated specifications and synthetic inputs on this machine. They establish neither worst-case costs nor real-time guarantees, general scalability, independent alignment accuracy, pianist performance or user-facing latency.
