import { useState, useEffect, useCallback, useRef } from 'react';
import { WebMidi, type Input, type PortEvent } from 'webmidi';

export interface MidiNote {
  name: string;
  octave: number;
  identifier: string;
  number: number;
  velocity: number;
  timestamp: number;
}

export interface MidiEvent {
  type: 'noteon' | 'noteoff' | 'controlchange';
  timestamp: number;
  note?: number;
  velocity?: number;
  /** Raw MIDI velocity 0-127 (noteon only; webmidi v3 e.note.rawAttack) */
  rawAttack?: number;
  controller?: number;
  value?: number;
}

/** Maximum number of events retained in the bounded stream (oldest dropped first). */
const EVENTS_CAP = 500;

/** Tetto della registrazione che viene analizzata. Alto abbastanza da non
 *  tagliare un brano, basso abbastanza da non crescere senza limite se la pagina
 *  resta aperta con la tastiera collegata per ore. */
const RECORDING_CAP = 20000;

export interface UseMidiReturn {
  isEnabled: boolean;
  isSupported: boolean;
  inputs: Input[];
  selectedInput: Input | null;
  activeNotes: Map<number, MidiNote>;
  lastNote: MidiNote | null;
  lastEvent: MidiEvent | null;
  events: MidiEvent[];
  /**
   * Esecuzione completa, senza troncamento. `events` e' un flusso di INTERFACCIA
   * e perde la coda vecchia oltre EVENTS_CAP; questa e' la registrazione che
   * viene analizzata, e non puo' perdere una nota. Un brano da 216 note produce
   * 434 eventi: gia' oltre il tetto.
   *
   * Stabilita per identita' e mutata sul posto, quindi non causa render. Va
   * letta al momento dell'analisi, non sottoscritta.
   */
  recording: MidiEvent[];
  error: string | null;
  enable: () => Promise<void>;
  selectInput: (inputId: string) => void;
  disable: () => void;
  /**
   * Svuota la registrazione e le note attualmente premute.
   *
   * Va chiamata all'inizio di ogni prova. Senza, `recording` cresce e basta:
   * due prove consecutive finirebbero sovrapposte nello stesso payload, e
   * l'allineatore le leggerebbe come un unico brano. Anche le note premute
   * vanno svuotate, altrimenti una nota tenuta dal musicista al momento del
   * countdown resterebbe " premuta" per tutta l'esecuzione.
   */
  clearRecording: () => void;
}

export function useMidi(): UseMidiReturn {
  const [isEnabled, setIsEnabled] = useState(false);
  const [isSupported] = useState(() => typeof navigator !== 'undefined' && !!navigator.requestMIDIAccess);
  const [inputs, setInputs] = useState<Input[]>([]);
  const [selectedInput, setSelectedInput] = useState<Input | null>(null);
  const [activeNotes, setActiveNotes] = useState<Map<number, MidiNote>>(new Map());
  const [lastNote, setLastNote] = useState<MidiNote | null>(null);
  const [lastEvent, setLastEvent] = useState<MidiEvent | null>(null);
  const [events, setEvents] = useState<MidiEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const selectedInputRef = useRef<Input | null>(null);
  // Every port this hook has subscribed to, so cleanup detaches exactly these.
  const attachedInputsRef = useRef<Input[]>([]);
  const [recording, setRecording] = useState<MidiEvent[]>([]);

  // Record subscriptions and make the selection follow the port that actually
  // delivers. A Bluetooth bridge enumerates as two ports (A/B) where only one
  // carries the keyboard's traffic, and which one that is can change between
  // sessions — so listening to a single port silently drops every event.
  // ponytail: selectedInput is display-only; the "preferred port" concept is
  // dropped. Add it back only if a real user-facing need for it appears.
  const trackAttachment = useCallback((input: Input) => {
    if (!attachedInputsRef.current.includes(input)) {
      attachedInputsRef.current.push(input);
    }
    if (selectedInputRef.current !== input) {
      selectedInputRef.current = input;
      setSelectedInput(input);
    }
  }, []);

  // Store listener references so we can remove ONLY ours on cleanup
  // (WebMidi is a global singleton — calling removeListener() kills ALL hooks)
  const connectedListenerRef = useRef<((e: PortEvent) => void) | null>(null);
  const disconnectedListenerRef = useRef<((e: PortEvent) => void) | null>(null);

  // Append to the bounded stream with functional setState so rapid chord-speed
  // input is never dropped between React renders (never reads stale state).
  const appendEvent = useCallback((event: MidiEvent) => {
    setRecording(prev => {
      const next = [...prev, event];
      return next.length > RECORDING_CAP ? next.slice(next.length - RECORDING_CAP) : next;
    });
    setEvents(prev => {
      const next = [...prev, event];
      return next.length > EVENTS_CAP ? next.slice(next.length - EVENTS_CAP) : next;
    });
  }, []);

  const attachListeners = useCallback((input: Input) => {
    // Clear any existing listeners on this specific input
    input.removeListener();

    // Note On
    input.addListener('noteon', (e) => {
      const note: MidiNote = {
        name: e.note.name + (e.note.accidental || ''),
        octave: e.note.octave,
        identifier: e.note.identifier,
        number: e.note.number,
        velocity: e.note.attack,
        timestamp: e.timestamp,
      };

      setActiveNotes(prev => {
        const next = new Map(prev);
        next.set(note.number, note);
        return next;
      });
      setLastNote(note);
      const event: MidiEvent = {
        type: 'noteon',
        note: note.number,
        velocity: note.velocity,
        rawAttack: e.note.rawAttack,
        timestamp: note.timestamp,
      };
      setLastEvent(event);
      appendEvent(event);
    });

    // Note Off
    input.addListener('noteoff', (e) => {
      setActiveNotes(prev => {
        const next = new Map(prev);
        next.delete(e.note.number);
        return next;
      });
      const event: MidiEvent = { type: 'noteoff', note: e.note.number, timestamp: e.timestamp };
      setLastEvent(event);
      appendEvent(event);
    });

    input.addListener('controlchange', (e) => {
      const event: MidiEvent = {
        type: 'controlchange',
        controller: e.controller.number,
        value: e.rawValue,
        timestamp: e.timestamp,
      };
      setLastEvent(event);
      appendEvent(event);
    });
  }, [appendEvent]);

  const enable = useCallback(async () => {
    try {
      setError(null);
      await WebMidi.enable();
      setIsEnabled(true);
      setInputs([...WebMidi.inputs]);

      // Subscribe to EVERY available port, not just the first. A Bluetooth MIDI
      // bridge enumerates as two ports (A/B) and only one of them carries the
      // keyboard's traffic; which one varies per session. Listening to a single
      // port yields a device that looks connected but delivers zero events.
      for (const input of WebMidi.inputs) {
        attachListeners(input);
        trackAttachment(input);
      }

      // Global hot-plug listeners are NOT registered here: the listener-ownership
      // effect below is the single registration path (it runs when isEnabled
      // flips to true, so hot-plug still works after an enable() that found
      // zero inputs) and it never duplicates a live registration.
    } catch (err) {
      console.error('MIDI enable error:', err);
      // `err.message || fallback` on unknown: a DOMException from a denied
      // permission prompt is not an Error instance, and an empty message must
      // still fall back to the guidance string (useMidi.test.ts pins both).
      const message = err instanceof Error ? err.message : '';
      setError(message || 'Failed to enable MIDI. Ensure your browser supports Web MIDI.');
      setIsEnabled(false);
    }
  }, [attachListeners, trackAttachment]);

  const selectInput = useCallback((inputId: string) => {
    // Resolve BEFORE detaching. An empty or unresolvable id leaves the live
    // input's listeners attached and the selection unchanged, so the guard
    // below only has to cover the unresolvable case.
    // NOTE: with webmidi validation on (the default) and MIDI disabled,
    // `getInputById` throws "WebMidi is not enabled." before it ever sees an
    // empty id — this is a no-op only while MIDI is enabled. Selecting through
    // a disabled WebMidi throws; it does not silently no-op.
    const input = WebMidi.getInputById(inputId);
    if (!input) {
      return;
    }

    // Re-report the chosen port. Its peers keep their listeners on purpose:
    // a Bluetooth bridge enumerates as A/B and only one carries the keyboard's
    // traffic, so silencing the other would drop every event.
    setSelectedInput(input);
    selectedInputRef.current = input;
    setActiveNotes(new Map());
    attachListeners(input);
    trackAttachment(input);
  }, [attachListeners, trackAttachment]);

  const disable = useCallback(() => {
    for (const port of attachedInputsRef.current) {
      port.removeListener();
    }
    attachedInputsRef.current = [];
    // Remove only THIS instance's global listeners
    if (connectedListenerRef.current) {
      WebMidi.removeListener('connected', connectedListenerRef.current);
      connectedListenerRef.current = null;
    }
    if (disconnectedListenerRef.current) {
      WebMidi.removeListener('disconnected', disconnectedListenerRef.current);
      disconnectedListenerRef.current = null;
    }
    WebMidi.disable();
    setIsEnabled(false);
    setInputs([]);
    setSelectedInput(null);
    selectedInputRef.current = null;
    setActiveNotes(new Map());
    setLastNote(null);
    setLastEvent(null);
    setEvents([]);
    setRecording([]);
  }, []);

  // Listener ownership: attachment lives in the SETUP, not only in cleanup, so
  // every mount and every effect remount (Vite Fast Refresh / React StrictMode
  // double-invoke) re-establishes delivery. A cleanup-only effect detached the
  // live Input on remount while isEnabled/selectedInput survived, leaving a
  // device that showed as connected but delivered zero events.
  useEffect(() => {
    if (!isEnabled) {
      return undefined;
    }

    // Subscribe to every known port on every run, so a remount (Vite Fast
    // Refresh / React StrictMode double-invoke) re-establishes delivery on all
    // of them. attachListeners clears per-port first, so re-running never
    // double-subscribes.
    for (const port of WebMidi.inputs) {
      attachListeners(port);
      // Deliberate: selection must follow the port that actually delivers, and
      // the setState is a no-op on every re-run (ref already holds that port).
      // Deriving it during render instead would break selectInput(), which is
      // an explicit user choice that overrides the "last port wins" default.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      trackAttachment(port);
    }

    // Single registration path for the global hot-plug handlers: register only
    // while the ref is missing (first enable, or after a remount's cleanup
    // nulled it) so a live registration is never duplicated.
    const onConnected = () => {
      setInputs([...WebMidi.inputs]);
      // A newly plugged port joins the same all-ports subscription set.
      for (const port of WebMidi.inputs) {
        attachListeners(port);
        trackAttachment(port);
      }
    };

    const onDisconnected = () => {
      const stillThere = new Set(WebMidi.inputs);
      setInputs([...WebMidi.inputs]);
      // Drop only the ports that actually went away; the ones still present
      // keep their listeners (removeListener() is per-port, all-listeners).
      attachedInputsRef.current = attachedInputsRef.current.filter((port) => {
        if (stillThere.has(port)) return true;
        port.removeListener();
        return false;
      });
      if (selectedInputRef.current && !stillThere.has(selectedInputRef.current)) {
        setSelectedInput(null);
        selectedInputRef.current = null;
        setActiveNotes(new Map());
      }
    };

    if (!connectedListenerRef.current) {
      connectedListenerRef.current = onConnected;
      WebMidi.addListener('connected', onConnected);
    }
    if (!disconnectedListenerRef.current) {
      disconnectedListenerRef.current = onDisconnected;
      WebMidi.addListener('disconnected', onDisconnected);
    }

    return () => {
      // Detach exactly the ports this hook subscribed to — never a bare
      // WebMidi.removeListener(), which is a global singleton wipe.
      for (const port of attachedInputsRef.current) {
        port.removeListener();
      }
      attachedInputsRef.current = [];
      if (connectedListenerRef.current) {
        WebMidi.removeListener('connected', connectedListenerRef.current);
        connectedListenerRef.current = null;
      }
      if (disconnectedListenerRef.current) {
        WebMidi.removeListener('disconnected', disconnectedListenerRef.current);
        disconnectedListenerRef.current = null;
      }
    };
  }, [isEnabled, attachListeners, trackAttachment]);

  const clearRecording = useCallback(() => {
    setRecording([]);
    setEvents([]);
    setActiveNotes(new Map());
  }, []);

  return {
    isEnabled,
    isSupported,
    inputs,
    selectedInput,
    activeNotes,
    lastNote,
    lastEvent,
    events,
    recording,
    error,
    enable,
    selectInput,
    disable,
    clearRecording,
  };
}
