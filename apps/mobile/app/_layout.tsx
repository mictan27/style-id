import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack, useRouter } from 'expo-router';
import { ShareIntentProvider, useShareIntentContext } from 'expo-share-intent';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { selectIsSignedIn, useAuthStore } from '@/store/auth';
import { colors } from '@/theme';

SplashScreen.preventAutoHideAsync().catch(() => undefined);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1, backgroundColor: colors.background }}>
      <SafeAreaProvider>
        <ShareIntentProvider options={{ resetOnBackground: false }}>
          <QueryClientProvider client={queryClient}>
            <StatusBar style="dark" />
            <RootNavigator />
          </QueryClientProvider>
        </ShareIntentProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

function RootNavigator() {
  const hydrated = useAuthStore((s) => s.hydrated);
  const hydrate = useAuthStore((s) => s.hydrate);
  const signedIn = useAuthStore(selectIsSignedIn);

  useEffect(() => {
    hydrate().finally(() => SplashScreen.hideAsync().catch(() => undefined));
  }, [hydrate]);

  useIncomingShare(signedIn);

  if (!hydrated) return null;

  return (
    <Stack screenOptions={{ headerTintColor: colors.primary, contentStyle: { backgroundColor: colors.background } }}>
      <Stack.Protected guard={!signedIn}>
        <Stack.Screen name="(auth)" options={{ headerShown: false }} />
      </Stack.Protected>
      <Stack.Protected guard={signedIn}>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="closet/new" options={{ title: 'Add a garment', presentation: 'modal' }} />
        <Stack.Screen name="closet/capture" options={{ title: 'Measure with camera', presentation: 'fullScreenModal' }} />
        <Stack.Screen name="closet/[id]" options={{ title: 'Garment' }} />
        <Stack.Screen name="check/[reportId]" options={{ title: 'Fit report' }} />
        <Stack.Screen name="outcomes/[reportId]" options={{ title: 'What happened?', presentation: 'modal' }} />
        <Stack.Screen name="body/scan" options={{ title: 'LiDAR scan', presentation: 'fullScreenModal' }} />
        <Stack.Screen name="body/photo" options={{ title: 'Photo scan', presentation: 'fullScreenModal' }} />
        <Stack.Screen name="body/manual" options={{ title: 'Enter measurements' }} />
        <Stack.Screen name="body/confirm" options={{ title: 'Confirm your numbers' }} />
        <Stack.Screen name="avatar/[reportId]" options={{ title: 'Fit map' }} />
      </Stack.Protected>
    </Stack>
  );
}

/**
 * A product URL shared from Safari or a shop app arrives through expo-share-intent.
 * Hand it to the Check tab, which runs /products/check → /fit/reports.
 */
function useIncomingShare(signedIn: boolean) {
  const router = useRouter();
  const { hasShareIntent, shareIntent, resetShareIntent } = useShareIntentContext();

  useEffect(() => {
    if (!hasShareIntent || !signedIn) return;
    const url = shareIntent.webUrl ?? extractUrl(shareIntent.text);
    resetShareIntent();
    if (url) {
      router.push({ pathname: '/(tabs)/check', params: { url } });
    }
  }, [hasShareIntent, shareIntent, resetShareIntent, router, signedIn]);
}

function extractUrl(text: string | null | undefined): string | null {
  if (!text) return null;
  const match = text.match(/https?:\/\/\S+/);
  return match ? match[0] : null;
}
