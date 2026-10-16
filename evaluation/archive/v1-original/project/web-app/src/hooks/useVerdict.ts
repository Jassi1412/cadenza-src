import { useCallback, useRef, useState } from 'react';
import type { MidiEvent } from './useMidi';

export const API_URL =
  (import.meta.env.VITE_CADENZA_API as string | undefined) ??
  'https://cadenza-etji.onrender.com';

export interface PerformedNote {
  time_ms: number;
  dur_ms: number;
  pitch: number;
  velocity: number;
}

export interface ControlChange {
  time_ms: number;
  controller: number;
  value: number;
}

export interface Verdict {
  ok: boolean;
  exit: number;
}

export type VerdictMap = Record<string, Verdict>;

export interface PerformancePayload {
  notes: PerformedNote[];
  control_changes: ControlChange[];
  tempo_factor: number;
}

const MIN_DURATION_MS = 30;

function isNoteOff(event: MidiEvent): boolean {
  return event.type === 'noteoff' || (event.type === 'noteon' && (event.rawAttack ?? 0) === 0);
}

export function toPerformance(
  events: readonly MidiEvent[],
  tempoFactor = 1.0,
): PerformancePayload {
  const notes: PerformedNote[] = [];
  const control_changes: ControlChange[] = [];
  const pending = new Map<number, PendingAttack[]>();
  let last = 0;

  for (const event of events) {
    last = event.timestamp;
    const pitch = event.note;

    if (event.type === 'controlchange') {
      if (event.controller === undefined || event.value === undefined) continue;
      control_changes.push({ time_ms: event.timestamp, controller: event.controller, value: event.value });
      continue;
    }

    if (pitch === undefined) continue;

    if (isNoteOff(event)) {
      const queue = pending.get(pitch);
      const attack = queue?.shift();
      if (queue && queue.length === 0) pending.delete(pitch);
      if (attack === undefined) continue;
      const dur = event.timestamp - attack.time_ms;
      notes.push({ time_ms: attack.time_ms, dur_ms: dur, pitch, velocity: attack.velocity });
      continue;
    }

    const queue = pending.get(pitch) ?? [];
    queue.push({ time_ms: event.timestamp, velocity: event.rawAttack ?? 64 });
    pending.set(pitch, queue);
  }

  for (const [pitch, queue] of pending) {
    for (const attack of queue) {
      notes.push({
        time_ms: attack.time_ms,
        dur_ms: Math.max(last - attack.time_ms, MIN_DURATION_MS),
        pitch,
        velocity: attack.velocity,
      });
    }
  }

  notes.sort((a, b) => a.time_ms - b.time_ms);
  control_changes.sort((a, b) => a.time_ms - b.time_ms);
  return { notes, control_changes, tempo_factor: tempoFactor };
}

interface PendingAttack {
  time_ms: number;
  velocity: number;
}

export type VerdictStatus = 'idle' | 'working' | 'done' | 'error';

export interface UseVerdictReturn {
  status: VerdictStatus;
  verdicts: VerdictMap | null;
  error: string | null;
  noteCount: number;
  analyse: (scoreXml: string, tempoFactor?: number) => Promise<void>;
  reset: () => void;
}

export function useVerdict(events: readonly MidiEvent[]): UseVerdictReturn {
  const [status, setStatus] = useState<VerdictStatus>('idle');
  const [verdicts, setVerdicts] = useState<VerdictMap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [noteCount, setNoteCount] = useState(0);
  const busy = useRef(false);

  const analyse = useCallback(async (scoreXml: string, tempoFactor = 1.0) => {
    if (busy.current) return;
    const { notes, control_changes, tempo_factor } = toPerformance(events, tempoFactor);
    if (notes.length === 0) {
      setError('Nessuna nota registrata: suona il brano prima di chiedere il verdetto.');
      setStatus('error');
      return;
    }
    busy.current = true;
    setStatus('working');
    setError(null);
    setNoteCount(notes.length);
    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ score: scoreXml, notes, control_changes, tempo_factor }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.error ?? `il servizio ha risposto ${response.status}`);
      }
      setVerdicts(payload.verdicts as VerdictMap);
      setStatus('done');
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus('error');
    } finally {
      busy.current = false;
    }
  }, [events]);

  const reset = useCallback(() => {
    setStatus('idle');
    setVerdicts(null);
    setError(null);
    setNoteCount(0);
  }, []);

  return { status, verdicts, error, noteCount, analyse, reset };
}