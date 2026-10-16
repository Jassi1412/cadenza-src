// defineConfig da vitest/config: la chiave `test` è di vitest.
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    // Due runner: vitest = npm test; bun = solo useMidi.test.ts (serve mock.module). ponytail: migrare a vi.mock.
    exclude: ['**/node_modules/**', '**/dist/**', 'src/hooks/useMidi.test.ts'],
  },
})
