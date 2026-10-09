/** useMidi — acceptance: stream bounded 500, appendEvent funzionale, rawAttack 0-127, export stabile. */

// bun:test ha tipi assenti: tsconfig.app.json blocca `types`, diagnostica soppressa.
// @ts-expect-error bun:test has no installed type declarations — see the note above.
import { describe, test, expect, mock, beforeEach, afterEach, afterAll } from 'bun:test';
import type { MidiEvent, MidiNote, UseMidiReturn } from './useMidi';

// Riferimenti reali catturati prima del mock: afterAll li ripristina.

const realReact = await import('react');
let realWebMidi: unknown = null;
try {
  realWebMidi = await import('webmidi');
} catch {
  realWebMidi = null;
}

// Runtime React minimale: gli slot persistono fra i render.

interface Slot {
  value?: unknown;
  deps?: readonly unknown[];
}

let slots: Slot[] = [];
let cursor = 0;
// Ultimo body d'effetto per slot: remount() rilancia il setup.
let mountedEffects = new Map<number, () => void | (() => void)>();
let pendingEffects: Array<{ index: number; run: () => void | (() => void) }> = [];
let cleanups: Array<() => void> = [];

function sameDeps(a: readonly unknown[] | undefined, b: readonly unknown[] | undefined): boolean {
  if (a === undefined || b === undefined) return false;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (!Object.is(a[i], b[i])) return false;
  }
  return true;
}

function useStateImpl<T>(initial: T | (() => T)): [T, (next: T | ((prev: T) => T)) => void] {
  const i = cursor++;
  let slot = slots[i];
  if (!slot) {
    slot = { value: typeof initial === 'function' ? (initial as () => T)() : initial };
    slots[i] = slot;
  }
  const current = slot;
  const setValue = (next: T | ((prev: T) => T)): void => {
    current.value = typeof next === 'function' ? (next as (prev: T) => T)(current.value as T) : next;
  };
  return [current.value as T, setValue];
}

function useRefImpl<T>(initial: T): { current: T } {
  const i = cursor++;
  let slot = slots[i];
  if (!slot) {
    slot = { value: { current: initial } };
    slots[i] = slot;
  }
  return slot.value as { current: T };
}

function useCallbackImpl<T>(fn: T, deps: readonly unknown[]): T {
  const i = cursor++;
  const slot = slots[i];
  if (!slot || !sameDeps(slot.deps, deps)) {
    slots[i] = { value: fn, deps: [...deps] };
  }
  return slots[i].value as T;
}

function useEffectImpl(effect: () => void | (() => void), deps: readonly unknown[]): void {
  const i = cursor++;
  const slot = slots[i];
  if (!slot || !sameDeps(slot.deps, deps)) {
    slots[i] = { deps: [...deps] };
    pendingEffects.push({ index: i, run: effect });
  }
}

const reactModuleExports: Record<string, unknown> = {
  useState: useStateImpl,
  useEffect: useEffectImpl,
  useCallback: useCallbackImpl,
  useRef: useRefImpl,
};
reactModuleExports['default'] = reactModuleExports;

// Mock webmidi: WebMidi singleton + FakeMidiInput.

type Listener = (event: unknown) => void;

class FakeMidiInput {
  id: string;
  listeners = new Map<string, Listener[]>();

  constructor(id: string) {
    this.id = id;
  }

  removeListener = mock((type?: string): void => {
    if (type) {
      this.listeners.delete(type);
    } else {
      this.listeners.clear();
    }
  });

  addListener = mock((type: string, listener: Listener): void => {
    const list = this.listeners.get(type) ?? [];
    list.push(listener);
    this.listeners.set(type, list);
  });

  listenerCount(type: string): number {
    return (this.listeners.get(type) ?? []).length;
  }

  emit(type: string, event: unknown): void {
    const listeners = this.listeners.get(type) ?? [];
    if (listeners.length === 0) {
      throw new Error(`no ${type} listener registered on input ${this.id}`);
    }
    for (const listener of [...listeners]) {
      listener(event);
    }
  }
}

const webMidiState = {
  enabled: false,
  inputs: [] as FakeMidiInput[],
  failEnableWith: null as Error | null,
};

const webMidiMock = {
  get enabled(): boolean {
    return webMidiState.enabled;
  },
  get inputs(): FakeMidiInput[] {
    return webMidiState.inputs;
  },
  enable: mock(async (): Promise<void> => {
    if (webMidiState.failEnableWith) {
      throw webMidiState.failEnableWith;
    }
    webMidiState.enabled = true;
  }),
  disable: mock((): void => {
    webMidiState.enabled = false;
  }),
  addListener: mock((): void => {}),
  removeListener: mock((): void => {}),
  getInputById: (id: string): FakeMidiInput | null =>
    webMidiState.inputs.find((input) => input.id === id) ?? null,
};

// Mock di modulo: vanno registrati prima di importare l'hook.

mock.module('react', () => reactModuleExports);
mock.module('webmidi', () => ({ WebMidi: webMidiMock }));

const { useMidi } = await import('./useMidi');

// Harness

function useRenderHook(): UseMidiReturn {
  cursor = 0;
  const result = useMidi();
  const effects = pendingEffects;
  pendingEffects = [];
  for (const effect of effects) {
    mountedEffects.set(effect.index, effect.run);
    const cleanup = effect.run();
    if (typeof cleanup === 'function') {
      cleanups.push(cleanup);
    }
  }
  return result;
}

/** remount(): rilancia cleanup e setup; deps intatti, come in StrictMode. */
function remount(): void {
  for (const cleanup of cleanups) {
    try {
      cleanup();
    } catch {
// Teardown in corsa con disable(): il test seguente resetta.
    }
  }
  cleanups = [];
  for (const run of mountedEffects.values()) {
    const cleanup = run();
    if (typeof cleanup === 'function') {
      cleanups.push(cleanup);
    }
  }
}

interface NoteOnSpec {
  timestamp: number;
  number: number;
  name: string;
  accidental: string;
  octave: number;
  identifier: string;
  attack: number;
  rawAttack: number;
}

function makeNoteOn(spec: Partial<NoteOnSpec> = {}): unknown {
  const s: NoteOnSpec = {
    timestamp: 1000,
    number: 60,
    name: 'C',
    accidental: '',
    octave: 4,
    identifier: 'C4',
    attack: 0.5,
    rawAttack: 100,
    ...spec,
  };
  return {
    timestamp: s.timestamp,
    note: {
      name: s.name,
      accidental: s.accidental,
      octave: s.octave,
      identifier: s.identifier,
      number: s.number,
      attack: s.attack,
      rawAttack: s.rawAttack,
    },
  };
}

function makeNoteOff(timestamp: number, noteNumber: number): unknown {
  return { timestamp, note: { number: noteNumber } };
}

function makeControlChange(timestamp: number, controller: number, value: number): unknown {
  return { timestamp, controller: { number: controller }, rawValue: value };
}

async function useCreateHookWithInputs(inputIds: string[]): Promise<{
  inputs: FakeMidiInput[];
  result: UseMidiReturn;
}> {
  const inputs = inputIds.map((id) => new FakeMidiInput(id));
  webMidiState.inputs = inputs;
  const first = useRenderHook();
  await first.enable();
  return { inputs, result: useRenderHook() };
}

function globalListener(type: string): () => void {
  const calls: unknown[][] = webMidiMock.addListener.mock.calls;
  const found = calls.find((call) => call[0] === type);
  if (!found) {
    throw new Error(`missing global ${type} listener`);
  }
  return found[1] as () => void;
}

/** Handler passati a addListener per type, in ordine di registrazione. */
function globalRegistrations(type: string): Array<() => void> {
  return webMidiMock.addListener.mock.calls
    .filter((call: unknown[]) => call[0] === type)
    .map((call: unknown[]) => call[1] as () => void);
}

/** Handler passati a removeListener per type, in ordine di rimozione. */
function globalRemovals(type: string): Array<() => void> {
  return webMidiMock.removeListener.mock.calls
    .filter((call: unknown[]) => call[0] === type)
    .map((call: unknown[]) => call[1] as () => void);
}

async function withSuppressedConsoleError(fn: () => Promise<void>): Promise<void> {
  const originalError = console.error;
  console.error = (): void => {};
  try {
    await fn();
  } finally {
    console.error = originalError;
  }
}

function clearAllTestMocks(): void {
  webMidiMock.enable.mockClear();
  webMidiMock.disable.mockClear();
  webMidiMock.addListener.mockClear();
  webMidiMock.removeListener.mockClear();
}

// navigator: il support check legge globalThis.navigator.requestMIDIAccess.

interface NavLike {
  requestMIDIAccess?: unknown;
}

interface NavigatorSaveState {
  saved: boolean;
  original?: PropertyDescriptor;
  installedOwn: boolean;
  mutatedExisting: boolean;
}

let navigatorSaveState: NavigatorSaveState = {
  saved: false,
  installedOwn: false,
  mutatedExisting: false,
};

function installNavigator(midiCapable: boolean): void {
  if (!navigatorSaveState.saved) {
    navigatorSaveState.saved = true;
    navigatorSaveState.original = Object.getOwnPropertyDescriptor(globalThis, 'navigator');
  }
  const nav: NavLike = midiCapable ? { requestMIDIAccess: async () => true } : {};
  try {
    Object.defineProperty(globalThis, 'navigator', {
      value: nav,
      configurable: true,
      writable: true,
      enumerable: true,
    });
    navigatorSaveState.installedOwn = true;
    navigatorSaveState.mutatedExisting = false;
  } catch {
    // Existing navigator is non-configurable: mutate it in place instead.
    const existing = (globalThis as { navigator?: NavLike }).navigator;
    if (!existing) {
      throw new Error('cannot install navigator for MIDI support tests');
    }
    navigatorSaveState.installedOwn = false;
    if (midiCapable) {
      Object.defineProperty(existing, 'requestMIDIAccess', {
        value: async () => true,
        configurable: true,
        writable: true,
      });
      navigatorSaveState.mutatedExisting = true;
    } else {
      Reflect.deleteProperty(existing, 'requestMIDIAccess');
      navigatorSaveState.mutatedExisting = false;
    }
  }
}

function restoreNavigator(): void {
  const state = navigatorSaveState;
  if (!state.saved) return;
  if (state.mutatedExisting) {
    const existing = (globalThis as { navigator?: NavLike }).navigator;
    if (existing) {
      Reflect.deleteProperty(existing, 'requestMIDIAccess');
    }
  } else if (state.installedOwn) {
    if (state.original) {
      Object.defineProperty(globalThis, 'navigator', state.original);
    } else {
      Reflect.deleteProperty(globalThis, 'navigator');
    }
  }
  navigatorSaveState = { saved: false, installedOwn: false, mutatedExisting: false };
}

beforeEach(() => {
  slots = [];
  cursor = 0;
  pendingEffects = [];
  cleanups = [];
  mountedEffects = new Map();
  webMidiState.inputs = [];
  webMidiState.enabled = false;
  webMidiState.failEnableWith = null;
  clearAllTestMocks();
  installNavigator(true);
});

afterEach(() => {
  for (const cleanup of cleanups) {
    try {
      cleanup();
    } catch {
// Teardown in corsa con disable(): lo stato si resetta al test dopo.
    }
  }
  cleanups = [];
  restoreNavigator();
  clearAllTestMocks();
});

afterAll(() => {
// Ripristina i moduli reali per i test successivi.
  mock.module('react', () => realReact);
  if (realWebMidi) {
    mock.module('webmidi', () => realWebMidi);
  }
});

// Tests

describe('useMidi — task 2.1: bounded event stream, rawAttack, export stability', () => {
  test('export surface: useMidi is a function, UseMidiReturn shape and initial state are stable', () => {
    const fn: () => UseMidiReturn = useMidi;
    expect(typeof fn).toBe('function');

    // Type-surface stability for the exported interfaces (compile-time contract).
    const noteSample: MidiNote = {
      name: 'C',
      octave: 4,
      identifier: 'C4',
      number: 60,
      velocity: 0.5,
      timestamp: 1,
    };
    expect(noteSample.identifier).toBe('C4');
    const eventSample: MidiEvent = {
      type: 'noteon',
      note: 60,
      velocity: 0.5,
      rawAttack: 64,
      timestamp: 1,
    };
    expect(eventSample.rawAttack).toBe(64);
    expect(eventSample.type).toBe('noteon');

    const r = useRenderHook();
    expect(Object.keys(r).sort()).toEqual([
      'activeNotes',
      'clearRecording',
      'disable',
      'enable',
      'error',
      'events',
      'inputs',
      'isEnabled',
      'isSupported',
      'lastEvent',
      'lastNote',
      'recording',
      'selectInput',
      'selectedInput',
    ]);
    expect(r.isEnabled).toBe(false);
    expect(r.isSupported).toBe(true);
    expect(r.events).toEqual([]);
    expect(r.lastEvent).toBeNull();
    expect(r.lastNote).toBeNull();
    expect(r.error).toBeNull();
    expect(r.activeNotes.size).toBe(0);
    expect(r.inputs).toEqual([]);
    expect(r.selectedInput).toBeNull();
    expect(typeof r.enable).toBe('function');
    expect(typeof r.selectInput).toBe('function');
    expect(typeof r.disable).toBe('function');
  });

  test('support check: isSupported stays true when navigator exposes requestMIDIAccess', () => {
    const r = useRenderHook();
    expect(r.isSupported).toBe(true);
  });

  test('support check: isSupported flips to false when requestMIDIAccess is missing', () => {
    installNavigator(false);
    useRenderHook(); // first render runs the effect and schedules the state change
    const r = useRenderHook(); // second render observes it, mirroring React
    expect(r.isSupported).toBe(false);
  });

  test('enable() enables the adapter, subscribes to EVERY port, and reports the last as selected', async () => {
    const { inputs, result } = await useCreateHookWithInputs(['input-1', 'input-2']);
    const [input1, input2] = inputs;

    expect(result.isEnabled).toBe(true);
    expect(result.error).toBeNull();
    expect(result.inputs.length).toBe(2);
    expect(result.inputs[0]).toBe(input1);
    expect(result.selectedInput).toBe(input2);

// Ogni porta riceve i tre listener: i bridge Bluetooth si enumerano come A/B.
    for (const port of inputs) {
      expect(port.listenerCount('noteon')).toBe(1);
      expect(port.listenerCount('noteoff')).toBe(1);
      expect(port.listenerCount('controlchange')).toBe(1);
    }

    expect(webMidiMock.addListener.mock.calls.map((call: unknown[]) => call[0])).toEqual([
      'connected',
      'disconnected',
    ]);
    expect(webMidiState.enabled).toBe(true);
  });

  test('noteon appends one event with integer rawAttack and updates note state (before/after)', async () => {
    const { inputs, result } = await useCreateHookWithInputs(['input-1']);
    const [input1] = inputs;

    // BEFORE: empty stream, no active notes.
    expect(result.events.length).toBe(0);
    expect(result.activeNotes.size).toBe(0);

    input1.emit(
      'noteon',
      makeNoteOn({ timestamp: 1000.5, number: 60, attack: 0.75, rawAttack: 96 }),
    );
    const r = useRenderHook();

// AFTER: un evento, shape esatto — channel/rawBytes assenti.
    expect(r.events.length).toBe(1);
    expect(r.events[0]).toEqual({
      type: 'noteon',
      note: 60,
      velocity: 0.75,
      rawAttack: 96,
      timestamp: 1000.5,
    });
    expect('channel' in r.events[0]).toBe(false);
    expect('rawBytes' in r.events[0]).toBe(false);
    expect(Number.isInteger(r.events[0].rawAttack)).toBe(true);
    expect(r.events[0].rawAttack as number).toBeGreaterThanOrEqual(0);
    expect(r.events[0].rawAttack as number).toBeLessThanOrEqual(127);

    expect(r.lastEvent).toBe(r.events[0]);
    expect(r.lastNote?.identifier).toBe('C4');
    expect(r.lastNote?.name).toBe('C');
    expect(r.activeNotes.size).toBe(1);
    expect(r.activeNotes.get(60)?.identifier).toBe('C4');
  });

  test('rawAttack round-trips exactly for boundary values 0, 1, 64, 127 (0 is kept, not dropped)', async () => {
    const { inputs } = await useCreateHookWithInputs(['input-1']);
    const [input1] = inputs;

    const boundaries = [0, 1, 64, 127];
    for (const raw of boundaries) {
      input1.emit('noteon', makeNoteOn({ timestamp: 100 + raw, rawAttack: raw, attack: raw / 127 }));
    }
    const r = useRenderHook();

    expect(r.events.length).toBe(4);
    expect(r.events.map((e) => e.rawAttack)).toEqual(boundaries);
    expect(r.events.every((e) => Number.isInteger(e.rawAttack))).toBe(true);
    expect(r.events.every((e) => (e.rawAttack as number) >= 0 && (e.rawAttack as number) <= 127)).toBe(
      true,
    );
// rawAttack è l'intero 0-127, indipendente dalla velocity float.
    expect(r.events.map((e) => e.velocity)).toEqual([0, 1 / 127, 64 / 127, 1]);
  });

  test('appendEvent is functional: an 8-event chord-speed batch with no intermediate render is kept in order', async () => {
    const { inputs } = await useCreateHookWithInputs(['input-1']);
    const [input1] = inputs;

    input1.emit('noteon', makeNoteOn({ timestamp: 1 }));
    input1.emit('noteoff', makeNoteOff(2, 60));
    input1.emit('controlchange', makeControlChange(3, 64, 127));
    input1.emit('noteon', makeNoteOn({ timestamp: 4, number: 64, identifier: 'E4', name: 'E' }));
    input1.emit('noteoff', makeNoteOff(5, 64));
    input1.emit('controlchange', makeControlChange(6, 64, 0));
    input1.emit('noteon', makeNoteOn({ timestamp: 7, number: 67, identifier: 'G4', name: 'G' }));
    input1.emit('noteoff', makeNoteOff(8, 67));

    const r = useRenderHook();
    expect(r.events.length).toBe(8);
    expect(r.events.map((e) => e.timestamp)).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
    expect(r.events.map((e) => e.type)).toEqual([
      'noteon',
      'noteoff',
      'controlchange',
      'noteon',
      'noteoff',
      'controlchange',
      'noteon',
      'noteoff',
    ]);
  });

  test('stream is bounded at 500: oldest dropped first, newest retained, cap stable over time', async () => {
    const { inputs } = await useCreateHookWithInputs(['input-1']);
    const [input1] = inputs;

// PROPERTY: dopo N > cap lo stream tiene gli ULTIMI 500 timestamp, in ordine.
    for (let i = 0; i < 600; i++) {
      input1.emit('noteon', makeNoteOn({ timestamp: i }));
    }
    let r = useRenderHook();
    expect(r.events.length).toBe(500);
    expect(r.events.map((e) => e.timestamp)).toEqual(
      Array.from({ length: 500 }, (_, i) => i + 100),
    );
    expect(r.events.every((e) => (e.timestamp as number) >= 100)).toBe(true);

// PROPERTY: il cap è stabile — un evento butta fuori uno vecchio.
    input1.emit('noteon', makeNoteOn({ timestamp: 600 }));
    r = useRenderHook();
    expect(r.events.length).toBe(500);
    expect(r.events[r.events.length - 1].timestamp).toBe(600);
    expect(r.events[0].timestamp).toBe(101);
  });

  test('noteoff removes the active note and appends an exact event', async () => {
    const { inputs, result } = await useCreateHookWithInputs(['input-1']);
    const [input1] = inputs;
    expect(result.events.length).toBe(0);

    input1.emit('noteon', makeNoteOn({ timestamp: 10 }));
    let r = useRenderHook();
    expect(r.activeNotes.size).toBe(1); // BEFORE noteoff

    input1.emit('noteoff', makeNoteOff(11, 60));
    r = useRenderHook();
    expect(r.activeNotes.size).toBe(0); // AFTER noteoff
    expect(r.events.length).toBe(2);
    expect(r.events[1]).toEqual({ type: 'noteoff', note: 60, timestamp: 11 });
    expect(r.lastEvent).toBe(r.events[1]);
    expect(r.lastNote?.identifier).toBe('C4'); // lastNote is retained on noteoff
  });

  test('controlchange appends controller/value event without note or rawAttack', async () => {
    const { inputs, result } = await useCreateHookWithInputs(['input-1']);
    const [input1] = inputs;
    expect(result.events.length).toBe(0);

    input1.emit('controlchange', makeControlChange(66, 64, 127));
    const r = useRenderHook();
    expect(r.events.length).toBe(1);
    expect(r.events[0]).toEqual({
      type: 'controlchange',
      controller: 64,
      value: 127,
      timestamp: 66,
    });
    expect('note' in r.events[0]).toBe(false);
    expect('rawAttack' in r.events[0]).toBe(false);
    expect(r.lastEvent).toBe(r.events[0]);
  });

  test('unicode boundary: accidental ♯ survives into lastNote.name exactly', async () => {
    const { inputs } = await useCreateHookWithInputs(['input-1']);
    const [input1] = inputs;

    input1.emit(
      'noteon',
      makeNoteOn({
        timestamp: 90,
        name: 'B',
        accidental: '♯',
        octave: 4,
        identifier: 'B4',
        number: 71,
      }),
    );
    const r = useRenderHook();
    expect(r.lastNote?.name).toBe('B♯');
    expect(r.events[0]).toEqual({
      type: 'noteon',
      note: 71,
      velocity: 0.5,
      rawAttack: 100,
      timestamp: 90,
    });
  });

  test('selectInput() moves the reported selection to the chosen input, clears active notes, keeps history', async () => {
    const { inputs, result } = await useCreateHookWithInputs(['input-1', 'input-2']);
    const [input1, input2] = inputs;
// enable() sottoscrive ogni porta: l'ultima è la selezione riportata.
    expect(result.selectedInput).toBe(input2);

    input1.emit('noteon', makeNoteOn({ timestamp: 50 }));
    let r = useRenderHook();
    expect(r.activeNotes.size).toBe(1); // BEFORE switch — any port can deliver
    expect(r.events.length).toBe(1);

    r.selectInput('input-1');
    r = useRenderHook();
    expect(r.selectedInput).toBe(input1);
// selectInput risottoscrive la scelta; le altre porte non si zittiscono.
    expect(input1.listenerCount('noteon')).toBe(1);
    expect(input2.listenerCount('noteon')).toBe(1);
    expect(r.activeNotes.size).toBe(0); // AFTER switch — cleared
    expect(r.events.length).toBe(1); // history survives the switch

    input2.emit(
      'noteon',
      makeNoteOn({ timestamp: 51, number: 64, identifier: 'E4', name: 'E' }),
    );
    r = useRenderHook();
    expect(r.events.length).toBe(2); // stream continues losslessly on the other port
    expect(r.events[1].note).toBe(64);
  });

  test('selectInput() with an unknown id keeps the current selection and does not throw', async () => {
    const { inputs, result } = await useCreateHookWithInputs(['input-1']);
    const [input1] = inputs;

    result.selectInput('does-not-exist');
    const r = useRenderHook();
    expect(r.selectedInput).toBe(input1);
    expect(r.error).toBeNull();
    expect(r.isEnabled).toBe(true);
  });

  test('clearRecording() empties recording, the live stream and the held notes, and keeps listening', async () => {
// Serve a ogni prova: senza, due prese si leggerebbero come una.
    const { inputs } = await useCreateHookWithInputs(['input-1']);
    const [input1] = inputs;

    input1.emit('noteon', makeNoteOn({ number: 60, timestamp: 30 }));
    input1.emit('noteon', makeNoteOn({ number: 64, timestamp: 40 }));
    input1.emit('noteoff', makeNoteOff(90, 60));
    input1.emit('controlchange', makeControlChange(50, 64, 127));
    let r = useRenderHook();
    expect(r.recording.length).toBe(4);
    expect(r.events.length).toBe(4);
    expect(r.activeNotes.size).toBe(1); // note 64 is still held

    r.clearRecording();
    r = useRenderHook();
    expect(r.recording).toEqual([]);
    expect(r.events).toEqual([]);
// Una nota tenuta nel countdown chiuderebbe un attacco inesistente.
    expect(r.activeNotes.size).toBe(0);

    // Still listening: clearing must not detach anything.
    expect(r.isEnabled).toBe(true);
    expect(input1.listenerCount('noteon')).toBeGreaterThan(0);
    input1.emit('noteon', makeNoteOn({ number: 67, timestamp: 200 }));
    r = useRenderHook();
    expect(r.recording.length).toBe(1);
  });

  test('disable() clears the stream, note state, selection, and this instance\'s global listeners', async () => {
    const { inputs } = await useCreateHookWithInputs(['input-1']);
    const [input1] = inputs;

    input1.emit('noteon', makeNoteOn({ timestamp: 30 }));
    input1.emit('controlchange', makeControlChange(31, 64, 127));
    let r = useRenderHook();
    expect(r.events.length).toBe(2); // BEFORE disable

    r.disable();
    r = useRenderHook();
    expect(r.isEnabled).toBe(false);
    expect(r.events).toEqual([]); // AFTER disable
    expect(r.lastEvent).toBeNull();
    expect(r.lastNote).toBeNull();
    expect(r.activeNotes.size).toBe(0);
    expect(r.inputs).toEqual([]);
    expect(r.selectedInput).toBeNull();
    expect(r.error).toBeNull();
    expect(webMidiState.enabled).toBe(false);
    expect(webMidiMock.disable.mock.calls.length).toBe(1);
    expect(input1.listenerCount('noteon')).toBe(0);
    expect(
      webMidiMock.removeListener.mock.calls.map((call: unknown[]) => call[0]),
    ).toEqual(['connected', 'disconnected']);
  });

  test('enable() rejection surfaces err.message and keeps isEnabled false', async () => {
    webMidiState.failEnableWith = new Error('Permission denied');
    const first = useRenderHook();
    await withSuppressedConsoleError(() => first.enable());
    const r = useRenderHook();
    expect(r.error).toBe('Permission denied');
    expect(r.isEnabled).toBe(false);
    expect(r.events).toEqual([]);
  });

  test('enable() rejection with an empty message falls back to the default guidance', async () => {
    webMidiState.failEnableWith = new Error('');
    const first = useRenderHook();
    await withSuppressedConsoleError(() => first.enable());
    const r = useRenderHook();
    expect(r.error).toBe('Failed to enable MIDI. Ensure your browser supports Web MIDI.');
    expect(r.isEnabled).toBe(false);
  });

  test('hot-plug connected: auto-selects the newly attached input and the stream keeps working', async () => {
    webMidiState.inputs = [];
    const first = useRenderHook();
    await first.enable();
    let r = useRenderHook();
    expect(r.inputs.length).toBe(0);
    expect(r.selectedInput).toBeNull();
    expect(r.events).toEqual([]);

    const hotInput = new FakeMidiInput('input-hot');
    webMidiState.inputs = [hotInput];
    const onConnected = globalListener('connected');
    onConnected();
    r = useRenderHook();
    expect(r.selectedInput).toBe(hotInput);
    expect(r.inputs.length).toBe(1);
    expect(hotInput.listenerCount('noteon')).toBe(1);

    hotInput.emit('noteon', makeNoteOn({ timestamp: 70, rawAttack: 127 }));
    r = useRenderHook();
    expect(r.events.length).toBe(1);
    expect(r.events[0].rawAttack).toBe(127);
  });

  test('hot-plug disconnected: clears selection and active notes but retains event history', async () => {
    const { inputs } = await useCreateHookWithInputs(['input-1']);
    const [input1] = inputs;

    input1.emit('noteon', makeNoteOn({ timestamp: 80 }));
    let r = useRenderHook();
    expect(r.events.length).toBe(1);
    expect(r.activeNotes.size).toBe(1); // BEFORE disconnect
    expect(r.selectedInput).toBe(input1);

    webMidiState.inputs = [];
    const onDisconnected = globalListener('disconnected');
    onDisconnected();
    r = useRenderHook();
    expect(r.selectedInput).toBeNull();
    expect(r.activeNotes.size).toBe(0); // AFTER disconnect
    expect(r.inputs.length).toBe(0);
    expect(r.events.length).toBe(1); // history retained — only disable() clears it
    expect(r.events[0].timestamp).toBe(80);
  });
});

// Regressione 3.1: questi test devono FALLIRE sul useMidi.ts pre-fix.

describe('useMidi — task 3.2: 3.1 fix regression (effect remount)', () => {
  test('remount re-attaches the live input listeners to the selected input', async () => {
    const { inputs } = await useCreateHookWithInputs(['input-1']);
    const [input1] = inputs;
    expect(input1).toBeDefined();

// Il fix 3.1 rilancia il setup: i listener tornano sulla porta scelta.
    remount();

    expect(input1.listenerCount('noteon')).toBeGreaterThanOrEqual(1);
// emit() lancia senza listener: il run pre-fix fallisce rumorosamente.
    input1.emit('noteon', makeNoteOn({ timestamp: 90, rawAttack: 111 }));

    const r = useRenderHook();
    expect(r.events.length).toBe(1);
    expect(r.events[0].rawAttack).toBe(111);
  });

  test('remount re-registers the global hot-plug handlers with fresh identities', async () => {
// Discrimina su REGISTRAZIONI: removeListener è no-op, globalListener dà la prima.
    webMidiState.inputs = [];
    const first = useRenderHook();
    await first.enable();
// Il listener hot-plug vive nell'effetto sotto isEnabled: serve un render in più.
    useRenderHook();

    const beforeRegs = globalRegistrations('connected');
    const beforeDisRegs = globalRegistrations('disconnected');
    expect(beforeRegs.length).toBeGreaterThan(0);
    expect(beforeDisRegs.length).toBeGreaterThan(0);
    const beforeConnected = beforeRegs[beforeRegs.length - 1];
    const beforeDisconnected = beforeDisRegs[beforeDisRegs.length - 1];

    remount();

    // (a) the number of "connected" registrations INCREASED across the remount
    expect(globalRegistrations('connected').length).toBeGreaterThan(beforeRegs.length);
    // (b) the identity registered after the remount differs from the pre-remount one
    const afterRegs = globalRegistrations('connected');
    expect(afterRegs[afterRegs.length - 1]).not.toBe(beforeConnected);
// (c) rimozione ref-scoped con l'handler esatto pre-remount.
    expect(globalRemovals('connected')).toContain(beforeConnected);
    expect(globalRemovals('disconnected')).toContain(beforeDisconnected);
    // (d) firing the LAST registered "connected" handler still drives state
    const hotInput = new FakeMidiInput('input-hot');
    webMidiState.inputs = [hotInput];
    afterRegs[afterRegs.length - 1]();
    const r = useRenderHook();
    expect(r.selectedInput).toBe(hotInput);
    expect(r.inputs.length).toBe(1);
  });

  test('selectInput("") leaves the selection and listeners intact while MIDI is enabled', async () => {
    const { inputs, result } = await useCreateHookWithInputs(['input-1']);
    const [input1] = inputs;
    expect(input1).toBeDefined();

    const before = input1.listenerCount('noteon');
    expect(before).toBeGreaterThanOrEqual(1);

// Id falsy con MIDI attivo: selectInput esce prima di ogni removeListener.
    result.selectInput('');

    const r = useRenderHook();
    expect(r.selectedInput).toBe(input1);
    expect(r.selectedInput).not.toBeNull();
    expect(input1.listenerCount('noteon')).toBe(before);
    expect(globalRemovals('noteon')).toHaveLength(0);
  });
});
