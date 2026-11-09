// Cấu hình ESLint (flat config). Chạy: npm run lint   Tự sửa được thì sửa: npm run lint:fix
// Kiểm tra kiểu do tsc lo (npm run typecheck); định dạng do Prettier lo (npm run format).
import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';
import { defineConfig, globalIgnores } from 'eslint/config';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default defineConfig([
  globalIgnores(['dist', 'node_modules']),
  {
    // Mã giao diện chạy trên trình duyệt
    files: ['src/**/*.{ts,tsx}'],
    extends: [js.configs.recommended, tseslint.configs.recommended, reactHooks.configs.flat.recommended],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
  },
  {
    // Script và cấu hình chạy bằng Node
    files: ['scripts/**/*.{js,mjs}', 'vite.config.ts', 'eslint.config.js'],
    extends: [js.configs.recommended, tseslint.configs.recommended],
    languageOptions: {
      globals: globals.node,
    },
  },
]);
