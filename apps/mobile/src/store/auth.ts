import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import { create } from 'zustand';

const TOKEN_KEY = 'styleid.access_token';
const DEV_USER_KEY = 'styleid.dev_user';

/**
 * Keychain on iOS. The web build is a development preview only (screenshots, layout
 * checks), so it keeps the session in localStorage; a reload must not sign you out.
 */
const webStorage = {
  get(key: string): string | null {
    try {
      return globalThis.localStorage?.getItem(key) ?? null;
    } catch {
      return null;
    }
  },
  set(key: string, value: string | null): void {
    try {
      if (value === null) globalThis.localStorage?.removeItem(key);
      else globalThis.localStorage?.setItem(key, value);
    } catch {
      // Storage blocked (private mode); keep in memory only.
    }
  },
};

const secure = {
  async get(key: string): Promise<string | null> {
    if (Platform.OS === 'web') return webStorage.get(key);
    try {
      return await SecureStore.getItemAsync(key);
    } catch {
      return null;
    }
  },
  async set(key: string, value: string | null): Promise<void> {
    if (Platform.OS === 'web') return webStorage.set(key, value);
    try {
      if (value === null) await SecureStore.deleteItemAsync(key);
      else await SecureStore.setItemAsync(key, value);
    } catch {
      // Keychain unavailable (e.g. simulator without entitlement); keep in memory only.
    }
  },
};

export interface AuthState {
  /** JWT from POST /auth/apple. */
  token: string | null;
  /** `X-Dev-User` handle; only honoured in __DEV__ builds. */
  devUser: string | null;
  /** True once SecureStore has been read on launch. */
  hydrated: boolean;
  hydrate: () => Promise<void>;
  setToken: (token: string) => Promise<void>;
  setDevUser: (handle: string) => Promise<void>;
  signOut: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  devUser: null,
  hydrated: false,
  async hydrate() {
    const [token, devUser] = await Promise.all([secure.get(TOKEN_KEY), secure.get(DEV_USER_KEY)]);
    set({ token, devUser: __DEV__ ? devUser : null, hydrated: true });
  },
  async setToken(token) {
    set({ token, devUser: null });
    await Promise.all([secure.set(TOKEN_KEY, token), secure.set(DEV_USER_KEY, null)]);
  },
  async setDevUser(handle) {
    const trimmed = handle.trim();
    set({ devUser: trimmed, token: null });
    await Promise.all([secure.set(DEV_USER_KEY, trimmed), secure.set(TOKEN_KEY, null)]);
  },
  async signOut() {
    set({ token: null, devUser: null });
    await Promise.all([secure.set(TOKEN_KEY, null), secure.set(DEV_USER_KEY, null)]);
  },
}));

export function selectIsSignedIn(state: AuthState): boolean {
  return Boolean(state.token || (__DEV__ && state.devUser));
}
