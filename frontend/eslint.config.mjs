import js from '@eslint/js';
import { defineConfig } from 'eslint/config';
import tseslint from 'typescript-eslint';
import globals from 'globals';
export default defineConfig(
 {ignores:['dist/**','.astro/**','node_modules/**','playwright-report/**','test-results/**','.lighthouseci/**']},
 js.configs.recommended,
 ...tseslint.configs.recommended,
 {files:['**/*.{js,mjs,cjs,ts,tsx}'],languageOptions:{globals:{...globals.browser,...globals.node}},rules:{'@typescript-eslint/no-explicit-any':'off','no-undef':'off'}}
);
