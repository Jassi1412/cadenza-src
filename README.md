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

| Specification | Criterion, as the application names it | What it reads |
| --- | --- | --- |
| [`pitch-range.rml`](rml/metrics/pitch-range.rml) | **Key range** | that every attack uses a key the instrument has (21–108) |
| [`pitch-agreement.rml`](rml/metrics/pitch-agreement.rml) | **Key agreement** | the pressed key against the written note, within an octave-equivalent distance |
| [`dynamics-adherence.rml`](rml/metrics/dynamics-adherence.rml) | **Strength** | the attack velocity against the written level, in a band of eight units |
| [`articulation.rml`](rml/metrics/articulation.rml) | **Hold** | the hold against the gap to the next attack, split at a ratio of 0.75 |
| [`chord-jitter.rml`](rml/metrics/chord-jitter.rml) | **Coordination** | the spread among the members of one chord, against the window the rule sets |
| [`pedal-toggle.rml`](rml/metrics/pedal-toggle.rml) | **Pedal pairing** | the press and release against the marked span, within a quarter of a beat |
| [`syncopated-pedal.rml`](rml/metrics/syncopated-pedal.rml) | **Pedal ordering** | that the press follows the keys it applies to, with no numeric tolerance |

## Demonstrations

Five recordings cover the seven criteria, each judging two takes of a real piece: one
take that follows the score and one that breaks a single policy. Every take runs through
the same chain the deployed application uses, and all seven monitors judge both, so the
target criterion rejects while the other six accept.

### Key agreement

https://github.com/user-attachments/assets/ff5823fc-22fd-4ff6-b9f1-91547bfaad96

**Key agreement** — Satie, *Gymnopédie* no. 1. Six keys shifted up two semitones; six
attacks rejected, thirty-five accepted.

### Strength

https://github.com/user-attachments/assets/0bcfc296-80b2-46d9-9056-9c6b7a004bdc

**Strength** — Clementi, Sonatina op. 36 no. 1. One touch at 83–93 whatever the score
asks; twenty-six notes rejected.

### Hold

https://github.com/user-attachments/assets/cb590e82-82ba-49f2-bd9d-4fb4c196307c

**Hold** — Lemoine, *Étude enfantine* op. 37 no. 6. Every release cut to a third
of the gap to the next attack; three notes rejected, all of them legato or tenuto.

### Coordination

https://github.com/user-attachments/assets/2bf5216a-f728-4181-a9b5-1d64218456b2

**Coordination** — Chopin, Prelude op. 28 no. 20. Three chords rolled by 170, 90 and
90 ms; four attacks rejected.

### Pedal pairing and ordering

https://github.com/user-attachments/assets/6f957a84-61ef-4f2b-9846-d53088912dda

**Pedal pairing** and **pedal ordering** — Chopin, Prelude op. 28 no. 7, the page where six spans
apply. Two releases 580 ms late are rejected by pairing alone; two presses 140 ms early
are rejected by ordering alone.

## Repository layout

| Path | What it contains |
| --- | --- |
| [`web-app/`](web-app/) | the browser application: capture, score rendering, verdict display |
| [`server/`](server/) | the analysis service that joins a take with the score and writes the annotated trace |
| [`rml/`](rml/) | the seven specifications and the Prolog monitors compiled from them |
| [`evaluation/`](evaluation/) | the measurements, their frozen expectations and the videos above |
| [`evaluation/fixtures/`](evaluation/fixtures/) | a small score the harness runs on; a take played against it |
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

## Licence

Cadenza is released under the GNU General Public License, version 3. The full text is in
[`LICENSE`](LICENSE). The application bundles
[`@music-i18n/musicxml-player`](https://github.com/infojunkie/musicxml-player), which is
GPL-3.0, and that is why the combined work carries the same licence. The other
dependencies keep their own terms, all of them compatible with the GPL: React (MIT),
OpenSheetMusicDisplay (BSD-3-Clause), webmidi.js (Apache-2.0), lucide-react (ISC),
Partitura (Apache-2.0) and SWI-Prolog (BSD-2-Clause).

The scores in `scores/` and `evaluation/fixtures/` are public-domain works or files the
authors of this repository encoded themselves. Two arrangements used in an earlier round of
measurements have been removed from the repository because their composers hold the
copyright, and they were never part of the demonstration takes.
