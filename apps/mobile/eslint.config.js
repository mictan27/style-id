const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');

module.exports = defineConfig([
  expoConfig,
  {
    ignores: ['dist/*', 'ios/*', 'android/*', '.expo/*', 'node_modules/*', 'src/api/types.gen.ts'],
  },
  {
    rules: {
      // Local Expo Modules import expo-modules-core directly; the three.js scene uses JSX intrinsics.
      'react/no-unknown-property': 'off',
    },
  },
]);
