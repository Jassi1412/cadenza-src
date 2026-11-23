// `defineConfig` from vitest/config, not vite: the `test` key below is vitest's,
// and vite's own UserConfigExport does not type it (tsc -b checks this file).
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    // Two runners, deliberately, and each file is explicit about which it uses.
    //
    //   vitest  → the canonical `npm test`, and every other test file in src.
    //   bun     → src/hooks/useMidi.test.ts only. It drives the WebMidi singleton
    //              and the React hook runtime through `mock.module`, which vitest
    //              cannot do (module registry mocking requires a live import cycle
    //              the hook file relies on). It declares its own runner in its
    //              header; `bun test src/hooks/useMidi.test.ts` is the gate.
    //
    // ponytail: the exclusion below is the ceiling — the real fix is migrating
    // useMidi.test.ts to vi.mock, tracked in hooks/AGENTS.md. Until then this file
    // has coverage in exactly one place, so a green `npm test` does not cover it.
    exclude: ['**/node_modules/**', '**/dist/**', 'src/hooks/useMidi.test.ts'],
  },
})
