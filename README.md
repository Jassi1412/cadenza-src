# Cadenza

Cadenza compares what a student plays at a MIDI piano with what the score asks, and
returns one verdict per criterion instead of a single grade. The criteria are written in
RML (Rewrite Modulo Logic) and compiled to Prolog monitors; the web application draws the
verdicts on the score while the student plays and stops the piece on the note that
departs from the instructions.

**Live application**: <https://cadenza-unlikekats-projects.vercel.app>

## The seven criteria

Each criterion is one specification in [`rml/metrics/`](rml/metrics/), compiled to a
Prolog monitor that reads the annotated trace of a take.

| Specification | Criterion | What it reads |
| --- | --- | --- |
| [`pitch-agreement.rml`](rml/metrics/pitch-agreement.rml) | key identifiers | the pressed key against the written note, within an octave-equivalent distance |
| [`pitch-range.rml`](rml/metrics/pitch-range.rml) | range | that every attack uses a key the instrument has (21–108) |
| [`dynamics-adherence.rml`](rml/metrics/dynamics-adherence.rml) | touch | the attack velocity against the written level, in a band of eight units |
| [`articulation.rml`](rml/metrics/articulation.rml) | holds | the hold against the gap to the next attack, split at a ratio of 0.75 |
| [`chord-jitter.rml`](rml/metrics/chord-jitter.rml) | grouping | the spread among the members of one chord, against the window the rule sets |
| [`pedal-toggle.rml`](rml/metrics/pedal-toggle.rml) | pedal pairing | the press and release against the marked span, within a quarter of a beat |
| [`syncopated-pedal.rml`](rml/metrics/syncopated-pedal.rml) | pedal ordering | that the press follows the keys it applies to, with no numeric tolerance |

## Demonstrations

### Pitch Agreement

https://github.com/user-attachments/assets/ff5823fc-22fd-4ff6-b9f1-91547bfaad96

### Dynamics

https://github.com/user-attachments/assets/0bcfc296-80b2-46d9-9056-9c6b7a004bdc

### Articulation

https://github.com/user-attachments/assets/cb590e82-82ba-49f2-bd9d-4fb4c196307c

### Chord Coordination

https://github.com/user-attachments/assets/2bf5216a-f728-4181-a9b5-1d64218456b2

### Pedal

https://github.com/user-attachments/assets/6f957a84-61ef-4f2b-9846-d53088912dda

## Repository layout

| Path | What it contains |
| --- | --- |
| [`web-app/`](web-app/) | the browser application: capture, score rendering, verdict display |
| [`server/`](server/) | the analysis service that joins a take with the score and writes the annotated trace |
| [`rml/`](rml/) | the seven specifications and the Prolog monitors compiled from them |
| [`scores/`](scores/) | the scores the application parses, as MusicXML |
| [`evaluation/`](evaluation/) | the measurements, their frozen expectations and the videos above |
| `render.yaml`, `vendor/` | deployment to Render and the Prolog runtime it carries |

## Running it locally

The service needs Python 3.11, Java and SWI-Prolog; the browser application needs Node 20.

```bash
cd server && pip install -r requirements.txt
cd web-app && npm install && npm run dev
```

`evaluation/scripts/run.sh` reproduces the measurements, with the exact environment,
recorded versions and provenance in [`evaluation/README.md`](evaluation/README.md).

## Deploying

The browser application is built from [`web-app/`](web-app/) and deployed to Vercel; the
analysis service is built from [`server/Dockerfile`](server/Dockerfile) and deployed to
Render as the Docker service declared in [`render.yaml`](render.yaml), which redeploys on
every commit to `main`. Vercel needs `web-app/` as the project's root directory, since
`package.json` lives there and not at the repository root; the settings that matter are
also written down in [`web-app/vercel.json`](web-app/vercel.json) so a project with a
stale dashboard configuration still builds.

## Status and limits

The system assesses what a MIDI keyboard reports, so an acoustic piano played without
sampling is out of reach, and a marking the score does not encode cannot constrain a
verdict. The numeric policies are calibrated on a handful of performances, not on a corpus
of student attempts, and should be re-tuned as traces accumulate. Cadenza reports objective
parameters of an attempt; it is not a substitute for a teacher.
