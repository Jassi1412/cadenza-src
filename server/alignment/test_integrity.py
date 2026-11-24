# -*- coding: utf-8 -*-
"""Integrita' del percorso dei dati: la prestazione che il monitor giudica e'
quella che il pianista ha suonato?

Il test costruisce una prestazione sintetica con valori esatti e noti (numeri
interi, tempi interi in millisecondi), la fa passare per il JOIN vero e
confronta campo per campo. Non verifica che i verdetti siano giusti: verifica
che i DATI non cambino di valore lungo la catena.

Invarianti controllati, uno per riga del referto:

  I1 cardinalita'   nessun evento perso o duplicato
  I2 valori         numero di tasto e intensita' identici a quelli iniettati
  I3 tempi          timestamp identico al tempo iniettato
  I4 derivati       durMs e gapMs ricalcolati a mano coincidono
  I5 ordine         i timestamp non tornano indietro
  I6 serializzazione to_jsonl -> json.loads restituisce gli stessi valori
  I7 determinismo   due esecuzioni danno lo stesso JSONL, byte per byte
  I8 non interferenza  join non modifica l'ingresso che riceve
  I9 precisione     l'unico scarto ammesso e' l'arrotondamento dichiarato

Uso:  python test_integrity.py [percorso.musicxml]
"""
import copy
import hashlib
import io
import json
import os
import sys

from join import ScoreModel, join, to_jsonl

SCORE_DEFAULT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "evaluation", "fixtures", "exercise.musicxml")

MS_PER_BEAT = 600.0          # 100 bpm: ogni battuta dura 600 ms
ROUNDING = 0.005             # round(x, 2) sposta al massimo di mezzo centesimo

report = []


def line(name, ok, detail):
    report.append((name, ok, detail))
    print("%-22s %-4s %s" % (name, "OK" if ok else "FALLITO", detail))


def build_performance(model, tempo_factor):
    """Prestazione che segue lo spartito esatto: nulla deve essere scartato.

    I tempi sono interi in millisecondi e le intensita' intere, cosi' ogni
    scarto osservato in uscita e' del software, non dell'aritmetica.
    """
    perf, truth = [], []
    for n in model.notes:
        t = round(n["onset"] * MS_PER_BEAT / tempo_factor)      # ms interi
        dur = round(n["duration"] * MS_PER_BEAT / tempo_factor)
        vel = int(round(n["expected_dyn"])) if n["expected_dyn"] else 80
        perf.append({"time_ms": t, "pitch": int(n["pitch"]), "velocity": vel,
                     "score_beat": n["onset"], "dur_ms": dur})
        truth.append((int(n["pitch"]), vel, t, dur))
    perf.sort(key=lambda x: x["time_ms"])
    return perf, truth


def main():
    score = sys.argv[1] if len(sys.argv) > 1 else SCORE_DEFAULT
    print("spartito: %s" % os.path.basename(score))
    model = ScoreModel.from_musicxml(score)
    print("note nello spartito: %d" % len(model.notes))

    score_ms_per_beat = (model.ms_at(2.0) - model.ms_at(0.0)) / 2.0
    tempo_factor = MS_PER_BEAT / score_ms_per_beat
    perf, truth = build_performance(model, tempo_factor)
    print("eventi iniettati: %d   (fattore di tempo %.4f)\n" % (len(perf), tempo_factor))

    perf_before = copy.deepcopy(perf)
    events = join(model, perf, tempo_factor)

    ons = [e for e in events if e["type"] == "noteon"]

    # I1 - cardinalita': una pressione iniettata, una pressione in uscita
    line("I1 cardinalita'", len(ons) == len(perf),
         "iniettate %d, in uscita %d" % (len(perf), len(ons)))

    # I2/I3 - valori e tempi, confrontati sull'evento corrispondente
    by_pitch_time = {}
    for e in ons:
        by_pitch_time.setdefault((e["note"]["number"], round(e["timestamp"])), []).append(e)
    val_bad, time_bad, checked = 0, 0, 0
    for (pitch, vel, t, dur) in truth:
        cand = by_pitch_time.get((pitch, t)) or by_pitch_time.get((pitch, t + 1)) \
            or by_pitch_time.get((pitch, t - 1))
        if not cand:
            continue
        e = cand.pop(0)
        checked += 1
        if e["note"]["number"] != pitch or e["note"]["rawAttack"] != vel:
            val_bad += 1
        if abs(e["timestamp"] - t) > 0.01:
            time_bad += 1
    line("I2 valori", val_bad == 0 and checked == len(perf),
         "%d campi confrontati, %d divergenze (tasto+intensita')" % (checked * 2, val_bad))
    line("I3 tempi", time_bad == 0,
         "%d timestamp confrontati, %d divergenze" % (checked, time_bad))

    # I4 - i derivati si ricalcolano a mano dai valori osservati.
    #
    # Due attenzioni, imparate sbagliando l'oracolo la prima volta:
    #  * gapMs e' la distanza dal PROSSIMO ISTANTE DI ATTACCO DISTINTO, non dal
    #    prossimo evento: le note di un accordo condividono lo stesso gap,
    #    perche' l'articolazione scritta vale per l'accordo intero;
    #  * durMs e' la durata misurata a monte e portata sull'attacco, non
    #    ricalcolata dal rilascio (due voci possono suonare insieme e non si
    #    saprebbe quale rilascio chiude quale attacco).
    truth_by_key = {(p, t): dur for (p, vel, t, dur) in truth}
    attacchi = sorted({round(e["timestamp"]) for e in ons})
    dur_bad = gap_bad = 0
    for e in ons:
        key = (e["note"]["number"], round(e["timestamp"]))
        if key in truth_by_key and e.get("durMs") != truth_by_key[key]:
            dur_bad += 1
        t = round(e["timestamp"])
        after = [a for a in attacchi if a > t]
        want = None if not after else round(after[0] - t, 2)
        if e.get("gapMs") != want:
            gap_bad += 1
    line("I4 derivati", dur_bad == 0 and gap_bad == 0,
         "durMs %d divergenze su %d, gapMs %d su %d"
         % (dur_bad, len(ons), gap_bad, len(ons)))

    # I5 - l'ordine non si inverte
    ts = [e["timestamp"] for e in events]
    line("I5 ordine", ts == sorted(ts), "timestamp monotonici su %d eventi" % len(ts))

    # I6 - la serializzazione non perde ne' deforma nulla
    back = [json.loads(l) for l in to_jsonl(events).strip().split("\n")]
    line("I6 serializzazione", back == events,
         "riletti %d eventi, identici agli originali" % len(back))

    # I7 - due esecuzioni identiche
    again = join(model, perf, tempo_factor)
    h1 = hashlib.sha256(to_jsonl(events).encode()).hexdigest()
    h2 = hashlib.sha256(to_jsonl(again).encode()).hexdigest()
    line("I7 determinismo", h1 == h2, "sha256 %s" % h1[:16])

    # I8 - il JOIN non tocca l'ingresso
    line("I8 non interferenza", perf == perf_before,
         "ingresso invariato (%d eventi)" % len(perf))

    # I9 - l'unico scarto e' l'arrotondamento dichiarato a 2 decimali
    worst = 0.0
    for (pitch, vel, t, dur) in truth:
        for e in ons:
            if e["note"]["number"] == pitch and abs(e["timestamp"] - t) <= 1:
                worst = max(worst, abs(e["timestamp"] - t))
    ok9 = worst <= ROUNDING + 1e-9
    line("I9 precisione", ok9,
         "scarto massimo sui tempi %.4f ms (ammesso %.3f)" % (worst, ROUNDING))

    bad = [n for n, ok, _ in report if not ok]
    print("\n%d invarianti su %d rispettati" % (len(report) - len(bad), len(report)))
    if bad:
        print("FALLITI:", ", ".join(bad))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
