/**
 * Jest harness for the mobile app's pure-logic unit tests.
 *
 * Scope (intentional): the API layer (`api/adapter.ts`, `api/client.ts`,
 * `api/config.ts`) and i18n locale parity — none of which import React Native,
 * React, or Expo runtime. Component/device rendering is out of scope and is not
 * runtime-verified here (documented, not faked). We use ts-jest rather than
 * jest-expo because jest-expo would require adding babel-preset-expo + a
 * babel.config.js that Metro would then also consume, i.e. a change to the app
 * build pipeline; ts-jest compiles the tested TypeScript directly and leaves the
 * Expo/Metro build untouched.
 */
/** @type {import('jest').Config} */
module.exports = {
  testEnvironment: 'node',
  roots: ['<rootDir>'],
  testMatch: ['**/__tests__/**/*.test.ts'],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'json'],
  transform: {
    '^.+\\.tsx?$': ['ts-jest', { tsconfig: '<rootDir>/tsconfig.jest.json' }],
  },
};
