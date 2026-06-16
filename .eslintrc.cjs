/** @type {import('eslint').Linter.Config} */
module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
    'prettier',
  ],
  plugins: ['@typescript-eslint', 'react-hooks'],
  rules: {
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/consistent-type-imports': ['error', { prefer: 'type-imports' }],
  },
  ignorePatterns: ['dist', 'node_modules', '*.cjs', 'vite.config.ts', 'tailwind.config.ts', 'postcss.config.cjs'],
  overrides: [
    {
      files: ['apps/web/src/**/*.{ts,tsx}'],
      plugins: ['tailwindcss'],
      extends: ['plugin:tailwindcss/recommended'],
    },
  ],
};
