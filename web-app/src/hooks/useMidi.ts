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
  rawAttack?: number;
  controller?: number;
  value?: number;
}


const EVENTS_CAP = 500;

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
  recording: MidiEvent[];
  error: string | null;
  enable: () => Promise<void>;
  selectInput: (inputId: string) => void;
  disable: () => void;
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
  const attachedInputsRef = useRef<Input[]>([]);
  const [recording, setRecording] = useState<MidiEvent[]>([]);

  const trackAttachment = useCallback((input: Input) => {
    if (!attachedInputsRef.current.includes(input)) {
      attachedInputsRef.current.push(input);
    }
    if (selectedInputRef.current !== input) {
      selectedInputRef.current = input;
      setSelectedInput(input);
    }
  }, []);

  const connectedListenerRef = useRef<((e: PortEvent) => void) | null>(null);
  const disconnectedListenerRef = useRef<((e: PortEvent) => void) | null>(null);

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
    input.removeListener();

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

      for (const input of WebMidi.inputs) {
        attachListeners(input);
        trackAttachment(input);
      }

    } catch (err) {
      console.error('MIDI enable error:', err);
      const message = err instanceof Error ? err.message : '';
      setError(message || 'Failed to enable MIDI. Ensure your browser supports Web MIDI.');
      setIsEnabled(false);
    }
  }, [attachListeners, trackAttachment]);

  const selectInput = useCallback((inputId: string) => {
    const input = WebMidi.getInputById(inputId);
    if (!input) {
      return;
    }

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
    // Stacca solo i listener di questa istanza.
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

// Si agganciano anche nel setup: sopravvivono a Fast Refresh/StrictMode.
  useEffect(() => {
    if (!isEnabled) {
      return undefined;
    }

    // Ri-sottoscrivi tutte le porte; attachListeners pulisce prima per porta.
    for (const port of WebMidi.inputs) {
      attachListeners(port);
// Selezione sulla porta che consegna; setState no-op ai riesecuzioni.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      trackAttachment(port);
    }

    // Registrati handler hot-plug una sola volta (ref vuoto), mai duplicati.
    const onConnected = () => {
      setInputs([...WebMidi.inputs]);
      for (const port of WebMidi.inputs) {
        attachListeners(port);
        trackAttachment(port);
      }
    };

    const onDisconnected = () => {
      const stillThere = new Set(WebMidi.inputs);
      setInputs([...WebMidi.inputs]);
      // Stacca solo le porte sparite; le altre tengono i listener.
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
      // Stacca solo le nostre porte, mai un removeListener globale.
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
