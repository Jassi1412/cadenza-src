/**
 * useMidi — Task 2.1 acceptance tests.
 *
 * Covers:
 *  1. Bounded MidiEvent[] stream (cap 500, oldest dropped first)
 *  2. Functional appendEvent (chord-speed batches are never dropped between renders)
 *  3. Integer rawAttack 0-127 on noteon (webmidi v3 e.note.rawAttack), with
 *     channel/rawBytes intentionally absent from MidiEvent (live adapter scope)
 *  4. Export stability: useMidi function + exact UseMidiReturn shape,
 *     MidiNote / MidiEvent / UseMidiReturn type surfaces
 *
 * React and webmidi are mocked at module level (mock.module BEFORE the
 * dynamic import of the hook) so the hook's state machine can be driven
 * deterministically without a DOM or a real MIDI device.
 */

// bun:test has no installed type declarations here: tsconfig.app.json pins
// `types: ["vite/client"]` and bun-types is not a dependency. Adding a
// devDependency is outside this task's declared write scope (this test file
// only), so the unresolved-module diagnostic is suppressed instead.
// @ts-expect-error bun:test has no installed type declarations — see the note above.
import { describe, test, expect, mock, beforeEach, afterEach, afterAll } from 'bun:test';
import type { MidiEvent, MidiNote, UseMidiReturn } from './useMidi';

// ---------------------------------------------------------------------------
// Real module references captured BEFORE mocking, so afterAll can restore the
// module registry for any test file that shares this bun process later.
// ---------------------------------------------------------------------------

const realReact = await import('react');
let realWebMidi: unknown = null;
try {
  realWebMidi = await import('webmidi');
} catch {
  realWebMidi = null;
}

// ---------------------------------------------------------------------------
// Minimal React hook runtime (replaces the 'react' module for this file).
// Slots persist across useRenderHook() calls to model a single component
// instance re-rendering; cursor resets per render to model hook call order.
// ---------------------------------------------------------------------------

interface Slot {
  value?: unknown;
  deps?: readonly unknown[];
}

let slots: Slot[] = [];
let cursor = 0;
// Latest effect body per hook-slot index, so remount() can re-run the effect
// SETUP after running its cleanup with the deps slot left untouched.
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

// ---------------------------------------------------------------------------
// webmidi mock: singleton WebMidi + a controllable FakeMidiInput.
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Module mocks — MUST be registered before the hook module is imported.
// ---------------------------------------------------------------------------

mock.module('react', () => reactModuleExports);
mock.module('webmidi', () => ({ WebMidi: webMidiMock }));

const { useMidi } = await import('./useMidi');

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

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

/**
 * Effect remount: run every stored cleanup, then re-run every stored effect
 * body. The deps slot is deliberately left untouched, so the effect is NOT
 * re-scheduled on the next render — React would compare identical deps, which
 * is exactly what a Fast Refresh / StrictMode remount of a component with
 * unchanged props produces.
 */
function remount(): void {
  for (const cleanup of cleanups) {
    try {
      cleanup();
    } catch {
      // Teardown may race disable(); the next test resets all state.
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

/**
 * Every handler passed to WebMidi.addListener for `type`, in registration
 * order. The webmidi mock is a no-op recorder, so its call list IS the
 * registration evidence — no real listener bookkeeping is introduced here.
 */
function globalRegistrations(type: string): Array<() => void> {
  return webMidiMock.addListener.mock.calls
    .filter((call: unknown[]) => call[0] === type)
    .map((call: unknown[]) => call[1] as () => void);
}

/** Every handler passed to WebMidi.removeListener for `type`, in removal order. */
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

// ---------------------------------------------------------------------------
// navigator control (support check reads globalThis.navigator.requestMIDIAccess)
// ---------------------------------------------------------------------------

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
      // Listener teardown may race disable(); ignore — state resets next test.
    }
  }
  cleanups = [];
  restoreNavigator();
  clearAllTestMocks();
});

afterAll(() => {
  // Un-mock so later test files in this bun process get the real modules.
  mock.module('react', () => realReact);
  if (realWebMidi) {
    mock.module('webmidi', () => realWebMidi);
  }
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

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

    // Every port carries the three listeners: a Bluetooth bridge enumerates as
    // two ports and only one of them delivers the keyboard's traffic, so
    // subscribing to a single port silently drops all events.
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

    // AFTER: exactly one event, exact shape — channel/rawBytes are NOT present.
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
    // rawAttack is the raw 0-127 integer, independent of the float velocity.
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

    // PROPERTY: after N > cap fires in one batch, the stream equals the LAST 500
    // fired timestamps, in order (lossless within the bound).
    for (let i = 0; i < 600; i++) {
      input1.emit('noteon', makeNoteOn({ timestamp: i }));
    }
    let r = useRenderHook();
    expect(r.events.length).toBe(500);
    expect(r.events.map((e) => e.timestamp)).toEqual(
      Array.from({ length: 500 }, (_, i) => i + 100),
    );
    expect(r.events.every((e) => (e.timestamp as number) >= 100)).toBe(true);

    // PROPERTY: the cap is stable — one more event pushes one old event out.
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
    // enable() subscribes to EVERY port (a Bluetooth bridge enumerates as A/B
    // and only one carries traffic), so the last port is the reported selection.
    expect(result.selectedInput).toBe(input2);

    input1.emit('noteon', makeNoteOn({ timestamp: 50 }));
    let r = useRenderHook();
    expect(r.activeNotes.size).toBe(1); // BEFORE switch — any port can deliver
    expect(r.events.length).toBe(1);

    r.selectInput('input-1');
    r = useRenderHook();
    expect(r.selectedInput).toBe(input1);
    // selectInput re-subscribes the chosen port; it never silences the others,
    // so a keyboard on a different port keeps delivering.
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
    // ScorePage calls this when a take starts. Without it a second take would
    // be appended to the first and the aligner would read both as one piece.
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
    // A note held across the countdown would otherwise stay held for the whole
    // take, and its note-off would close an attack that no longer exists.
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

// ---------------------------------------------------------------------------
// Task 3.2 — regression tests for the 3.1 fix (listener lifecycle on remount).
//
// Every test below must FAIL against the pre-3.1 useMidi.ts, otherwise it is
// not a regression test: the 3.1 fix would be unprotected. See the neutralize
// procedure in the task report for the observed RED runs.
// ---------------------------------------------------------------------------

describe('useMidi — task 3.2: 3.1 fix regression (effect remount)', () => {
  test('remount re-attaches the live input listeners to the selected input', async () => {
    const { inputs } = await useCreateHookWithInputs(['input-1']);
    const [input1] = inputs;
    expect(input1).toBeDefined();

    // The 3.1 fix re-runs the effect setup on remount, so the selected input
    // must carry its listeners again with the selection UNCHANGED. No
    // selectInput() call, no deps change — only the effect re-running.
    remount();

    expect(input1.listenerCount('noteon')).toBeGreaterThanOrEqual(1);
    // FakeMidiInput.emit throws when its listener list is empty, so a pre-fix
    // run fails loudly here instead of silently recording nothing.
    input1.emit('noteon', makeNoteOn({ timestamp: 90, rawAttack: 111 }));

    const r = useRenderHook();
    expect(r.events.length).toBe(1);
    expect(r.events[0].rawAttack).toBe(111);
  });

  test('remount re-registers the global hot-plug handlers with fresh identities', async () => {
    // Discriminate on REGISTRATION evidence, never on firing a stored handler:
    // webMidiMock.removeListener is a no-op that deregisters nothing and
    // globalListener() resolves the FIRST-ever addListener("connected") call,
    // so a handler-firing assertion would stay green before the fix.
    webMidiState.inputs = [];
    const first = useRenderHook();
    await first.enable();
    // The global hot-plug registration lives in the effect, which is gated on
    // isEnabled — so the state update from enable() needs one more render to
    // schedule it (same sequence useCreateHookWithInputs relies on).
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
    // (c) ref-scoped removal passed the EXACT pre-remount handler — the pre-fix
    //     code registered inside enable() and could not remove by identity
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

    // Falsy id, with MIDI enabled: selectInput must early-return BEFORE any
    // removeListener, so the live input keeps its listeners and the selection
    // does not change. (With MIDI DISABLED and webmidi validation on,
    // getInputById throws before reaching this guard — see useMidi.ts.)
    result.selectInput('');

    const r = useRenderHook();
    expect(r.selectedInput).toBe(input1);
    expect(r.selectedInput).not.toBeNull();
    expect(input1.listenerCount('noteon')).toBe(before);
    expect(globalRemovals('noteon')).toHaveLength(0);
  });
});
