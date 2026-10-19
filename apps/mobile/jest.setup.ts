/**
 * Screen-test environment. Runs before each test file, before any app module loads,
 * so the openapi-fetch client (which captures `globalThis.fetch` on creation) talks to
 * the fake API.
 */
import { notifyManager } from '@tanstack/react-query';
import { cleanup } from '@testing-library/react-native';

import { FakeApi } from '@/test/fakeApi';

// React Query batches notifications with setTimeout; microtasks keep screen updates
// deterministic and fast under Jest.
notifyManager.setScheduler(queueMicrotask);

export const fakeApi = new FakeApi();
(globalThis as { __fakeApi?: FakeApi }).__fakeApi = fakeApi;

globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
  const request = input instanceof Request ? input : new Request(String(input), init);
  const url = new URL(request.url);
  const text = await request.text();
  const headers: Record<string, string> = {};
  request.headers.forEach((value, name) => {
    headers[name.toLowerCase()] = value;
  });
  const { status, body } = fakeApi.handle({
    method: request.method,
    path: url.pathname,
    headers,
    body: text ? JSON.parse(text) : undefined,
  });
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  });
};

// In-memory Keychain. Tests sign in by writing the dev handle before rendering.
const secureStore = new Map<string, string>();
(globalThis as { __secureStore?: Map<string, string> }).__secureStore = secureStore;
jest.mock('expo-secure-store', () => {
  const store = (globalThis as unknown as { __secureStore: Map<string, string> }).__secureStore;
  return {
    getItemAsync: jest.fn(async (k: string) => store.get(k) ?? null),
    setItemAsync: jest.fn(async (k: string, v: string) => void store.set(k, v)),
    deleteItemAsync: jest.fn(async (k: string) => void store.delete(k)),
  };
});

// The share extension is native-only; screens see "nothing shared".
jest.mock('expo-share-intent', () => ({
  ShareIntentProvider: ({ children }: { children: unknown }) => children,
  useShareIntentContext: () => ({
    hasShareIntent: false,
    shareIntent: { text: null, webUrl: null },
    resetShareIntent: () => undefined,
  }),
}));

// Skia needs native JSI bindings. Its drawings (field guides, landmark overlay) are not
// what screen tests check, so every Skia component renders nothing.
jest.mock('@shopify/react-native-skia', () => {
  const component = () => null;
  return new Proxy(
    { vec: (x: number, y: number) => ({ x, y }) },
    { get: (target: Record<string, unknown>, name: string) => (name in target ? target[name] : component) },
  );
});

afterEach(() => {
  fakeApi.reset();
});

beforeEach(async () => {
  // App-wide singletons outlive a rendered tree: unmount whatever the previous test left,
  // then empty the query cache and the auth store. Required lazily so app modules load
  // after the fetch replacement above.
  /* eslint-disable @typescript-eslint/no-require-imports */
  await cleanup();
  const { queryClient } = require('@/api/queryClient');
  queryClient.clear();
  // Errors should surface at once; retry timing is React Query's concern, not ours.
  queryClient.setDefaultOptions({ queries: { ...queryClient.getDefaultOptions().queries, retry: false } });
  require('@/store/auth').useAuthStore.setState({ token: null, devUser: null, hydrated: false });
  /* eslint-enable @typescript-eslint/no-require-imports */
  secureStore.clear();
});
