import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  // temp-osmd: build vendored di OSMD, non va lintato.
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
    // useMidi.test.ts gira fuori dal render tree: react-hooks off.
    files: ['src/hooks/useMidi.test.ts'],
    rules: {
      'react-hooks/globals': 'off',
      'react-hooks/immutability': 'off',
      'react-hooks/rules-of-hooks': 'off',
    },
  },
  {
    // OSMD e musicxml-player senza tipi: `any` forzato. ponytail: wrappatori tipizzati.
    files: ['src/pages/ScorePage.tsx'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
])
