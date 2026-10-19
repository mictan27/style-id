import { renderRouter, screen } from 'expo-router/testing-library';

import type { FakeApi } from './fakeApi';

export const DEV_USER_KEY = 'styleid.dev_user';

/** The fake API instance installed by jest.setup.ts. */
export function fakeApi(): FakeApi {
  return (globalThis as unknown as { __fakeApi: FakeApi }).__fakeApi;
}

/**
 * Renders the real expo-router app (every file under app/) at `url`. Signed in as the
 * dev user `demo` unless `signedIn: false`; responses come from the fixture-backed fake API.
 */
export async function renderApp(url: string, { signedIn = true }: { signedIn?: boolean } = {}) {
  if (signedIn) {
    (globalThis as unknown as { __secureStore: Map<string, string> }).__secureStore.set(DEV_USER_KEY, 'demo');
  }
  // renderRouter calls jest.useFakeTimers(). Anything the first render schedules (React
  // Query retries, redirects) would then sit in a fake queue nobody advances, so keep
  // real timers for the whole test.
  const useFakeTimers = jest.useFakeTimers;
  jest.useFakeTimers = (() => jest) as typeof jest.useFakeTimers;
  try {
    const result = await renderRouter('./app', { initialUrl: url });
    return { ...result, screen };
  } finally {
    jest.useFakeTimers = useFakeTimers;
  }
}
