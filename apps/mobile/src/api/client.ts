import createClient, { type Middleware } from 'openapi-fetch';

import { useAuthStore } from '@/store/auth';

import type { paths } from './types.gen';

export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

export const DEV_USER_HEADER = 'X-Dev-User';

/**
 * Injects auth: a Bearer JWT when we have one; otherwise, in dev builds only,
 * the `X-Dev-User: <handle>` header the FastAPI service accepts.
 */
const authMiddleware: Middleware = {
  onRequest({ request }) {
    const { token, devUser } = useAuthStore.getState();
    if (token) {
      request.headers.set('Authorization', `Bearer ${token}`);
    } else if (__DEV__ && devUser) {
      request.headers.set(DEV_USER_HEADER, devUser);
    }
    return request;
  },
  async onResponse({ response }) {
    if (response.status === 401) {
      useAuthStore.getState().signOut();
    }
    return response;
  },
};

export const api = createClient<paths>({ baseUrl: API_URL });
api.use(authMiddleware);

export class ApiRequestError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: unknown,
  ) {
    super(typeof detail === 'string' ? detail : `Request failed with status ${status}`);
    this.name = 'ApiRequestError';
  }
}

/** Unwraps an openapi-fetch result into data or throws an ApiRequestError. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined || !result.response.ok) {
    const detail =
      result.error && typeof result.error === 'object' && 'detail' in result.error
        ? (result.error as { detail: unknown }).detail
        : result.error;
    throw new ApiRequestError(result.response.status, detail);
  }
  return result.data as T;
}
