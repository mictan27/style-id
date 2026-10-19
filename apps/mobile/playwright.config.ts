import { defineConfig } from '@playwright/test';

/**
 * Web screenshots of the app (pnpm screenshots). Runs Expo's web dev server (dev mode, so
 * the developer sign-in works) against the fixture-backed fake API and writes one PNG per
 * screen to screenshots/. The first run bundles for about a minute; set
 * reuseExistingServer by leaving `pnpm web` running to make reruns fast.
 */
export default defineConfig({
  testDir: 'e2e',
  outputDir: 'test-results',
  fullyParallel: true,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:8099',
    viewport: { width: 393, height: 852 }, // iPhone 15/16 points
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    colorScheme: 'light',
  },
  // Metro bundles each route on first request; the first screenshot run is slow.
  timeout: 120_000,
  expect: { timeout: 30_000 },
  webServer: {
    command: 'npx expo start --web --port 8099',
    url: 'http://localhost:8099',
    env: { CI: '1', BROWSER: 'none' },
    reuseExistingServer: true,
    timeout: 240_000,
  },
});
