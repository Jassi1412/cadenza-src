#!/usr/bin/env node
// Replay the application's exported conversion, without starting React or Vite.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const scriptPath = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(scriptPath), '../..');
const sourceRelativePath = 'web-app/src/hooks/useVerdict.ts';
const sourcePath = path.join(repoRoot, sourceRelativePath);
const require = createRequire(import.meta.url);
const sha256 = (value) => createHash('sha256').update(value).digest('hex');

export async function loadConverter() {
  let ts;
  try {
    ts = require(path.join(repoRoot, 'evaluation/.node/node_modules/typescript'));
  } catch (error) {
    throw new Error('Install the pinned TypeScript compiler in evaluation/.node before replaying.', { cause: error });
  }

  const source = await readFile(sourcePath, 'utf8');
  let environmentReplacements = 0;
  const compiled = ts.transpileModule(source, {
    fileName: sourcePath,
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.CommonJS,
      isolatedModules: true,
      sourceMap: false,
    },
    reportDiagnostics: true,
    transformers: {
      before: [(context) => {
        const visit = (node) => {
          // Vite supplies this object in the browser. The pure converter does not
          // read it; replacing the entire object keeps API_URL initialization local.
          if (ts.isPropertyAccessExpression(node)
              && node.name.text === 'env'
              && ts.isMetaProperty(node.expression)
              && node.expression.keywordToken === ts.SyntaxKind.ImportKeyword
              && node.expression.name.text === 'meta') {
            environmentReplacements += 1;
            return context.factory.createObjectLiteralExpression([], false);
          }
          return ts.visitEachChild(node, visit, context);
        };
        return (sourceFile) => ts.visitNode(sourceFile, visit);
      }],
    },
  });
  const errors = (compiled.diagnostics ?? []).filter((item) => item.category === ts.DiagnosticCategory.Error);
  if (errors.length) {
    throw new Error(ts.formatDiagnosticsWithColorAndContext(errors, {
      getCanonicalFileName: (filename) => filename,
      getCurrentDirectory: () => repoRoot,
      getNewLine: () => '\n',
    }));
  }

  const forbidden = () => { throw new Error('Replay must not invoke React hooks or network operations.'); };
  const module = { exports: {} };
  const sandbox = vm.createContext({
    module,
    exports: module.exports,
    require: (specifier) => {
      if (specifier !== 'react') throw new Error(`Replay refuses runtime import: ${specifier}`);
      return Object.freeze({ useCallback: forbidden, useRef: forbidden, useState: forbidden });
    },
    fetch: forbidden,
  });
  // Execute the entire transpiled application module. No function body is copied,
  // extracted, or independently implemented by this harness.
  new vm.Script(compiled.outputText, { filename: sourceRelativePath }).runInContext(sandbox, { timeout: 10_000 });
  if (typeof module.exports.toPerformance !== 'function') {
    throw new Error(`${sourceRelativePath} no longer exports toPerformance`);
  }
  return {
    toPerformance: module.exports.toPerformance,
    metadata: {
      source: sourceRelativePath,
      source_sha256: sha256(source),
      export: 'toPerformance',
      typescript_version: ts.version,
      node_version: process.version,
      environment_replacements: environmentReplacements,
      execution: 'full module transpile; React hooks and fetch disabled',
    },
  };
}

function readInput(input) {
  const events = Array.isArray(input) ? input : input?.events;
  const tempoFactor = Array.isArray(input) ? 1 : (input?.tempo_factor ?? 1);
  if (!Array.isArray(events)) throw new Error('Input must be a MidiEvent array or {events, tempo_factor}.');
  if (!Number.isFinite(tempoFactor) || tempoFactor <= 0) throw new Error('tempo_factor must be finite and positive.');
  for (const [index, event] of events.entries()) {
    if (!event || !['noteon', 'noteoff', 'controlchange'].includes(event.type)
        || !Number.isFinite(event.timestamp)) {
      throw new Error(`Event ${index} must have a supported type and a finite timestamp.`);
    }
    for (const field of ['note', 'velocity', 'rawAttack', 'controller', 'value']) {
      if (event[field] !== undefined && !Number.isFinite(event[field])) {
        throw new Error(`Event ${index}.${field} must be finite when present.`);
      }
    }
  }
  // Preserve the stream's order, timestamps, duplicate attacks, and missing releases.
  return { events, tempoFactor };
}

export async function replay(input) {
  const { events, tempoFactor } = readInput(input);
  const { toPerformance, metadata } = await loadConverter();
  return { ...toPerformance(events, tempoFactor), _replay: metadata };
}

async function selfTest() {
  const events = [
    { type: 'noteoff', timestamp: 0, note: 88 },
    { type: 'noteon', timestamp: 10, note: 60, rawAttack: 70 },
    { type: 'noteon', timestamp: 20, note: 60, rawAttack: 90 },
    { type: 'controlchange', timestamp: 25, controller: 64, value: 127 },
    { type: 'noteoff', timestamp: 50, note: 60 },
    { type: 'noteon', timestamp: 80, note: 60, rawAttack: 0 },
    { type: 'noteon', timestamp: 100, note: 64, rawAttack: 85 },
    { type: 'noteoff', timestamp: 105, note: 64 },
    { type: 'noteon', timestamp: 110, note: 67, rawAttack: 80 },
    { type: 'controlchange', timestamp: 140, controller: 64, value: 0 },
    { type: 'noteon', timestamp: 150, note: 69, rawAttack: 100 },
  ];
  const result = await replay({ events, tempo_factor: 1.5 });
  const { _replay, ...payload } = result;
  // JSON also removes cross-realm prototypes from the actual module's objects.
  assert.deepEqual(JSON.parse(JSON.stringify(payload)), {
    notes: [
      { time_ms: 10, dur_ms: 40, pitch: 60, velocity: 70 },
      { time_ms: 20, dur_ms: 60, pitch: 60, velocity: 90 },
      { time_ms: 100, dur_ms: 5, pitch: 64, velocity: 85 },
      { time_ms: 110, dur_ms: 40, pitch: 67, velocity: 80 },
      { time_ms: 150, dur_ms: 30, pitch: 69, velocity: 100 },
    ],
    control_changes: [
      { time_ms: 25, controller: 64, value: 127 },
      { time_ms: 140, controller: 64, value: 0 },
    ],
    tempo_factor: 1.5,
  });
  const empty = await replay([]);
  assert.equal(empty.notes.length, 0);
  assert.equal(empty.control_changes.length, 0);
  assert.equal(empty.tempo_factor, 1);
  process.stdout.write(`${JSON.stringify({ ok: true, checks: ['FIFO repeated pitch', 'zero-velocity release', 'short duration', 'unreleased notes', 'control changes', 'tempo factor', 'empty stream'], _replay }, null, 2)}\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === scriptPath) {
  try {
    if (process.argv.length === 3 && process.argv[2] === '--self-test') {
      await selfTest();
    } else {
      if (process.argv.length !== 4) throw new Error('Usage: node evaluation/scripts/replay.mjs input.json output.json\n       node evaluation/scripts/replay.mjs --self-test');
      const rawInput = await readFile(process.argv[2], 'utf8');
      const result = await replay(JSON.parse(rawInput));
      result._replay.input_sha256 = sha256(rawInput);
      await writeFile(process.argv[3], `${JSON.stringify(result, null, 2)}\n`);
    }
  } catch (error) {
    process.stderr.write(`Replay failed: ${error.message}\n`);
    process.exitCode = 1;
  }
}
