import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  // temp-osmd is a vendored build of opensheetmusicdisplay, tracked in git but
  // not ours: it ships no types, no test contract and must not be linted.
  globalIgnores(['dist', 'temp-osmd']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
  {
    // useMidi.test.ts is a hand-rolled hook harness (own useEffect stub, own
    // module-registry mocking) that runs OUTSIDE a React render tree on
    // purpose. The react-hooks rules assume a real component and report
    // module-level state + direct harness calls as violations.
    files: ['src/hooks/useMidi.test.ts'],
    rules: {
      'react-hooks/globals': 'off',
      'react-hooks/immutability': 'off',
      'react-hooks/rules-of-hooks': 'off',
    },
  },
  {
    // OSMD (OpenSheetMusicDisplay) and musicxml-player ship no usable type
    // definitions, so every cursor/renderer/player call in these files is
    // `any` by necessity, not by laziness. Typing the boundary is the real fix.
    // ponytail: re-enable once opensheetmusicdisplay is migrated to
    // vi.mock/typed wrappers; tracked in pages/AGENTS.md.
    files: ['src/pages/ScorePage.tsx'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
])
