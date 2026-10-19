import { QueryClient } from '@tanstack/react-query';

/** The app's single React Query cache. Tests clear it between cases (jest.setup.ts). */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});
