import { Stack } from 'expo-router';

import { colors } from '@/theme';

export default function ClosetStackLayout() {
  return (
    <Stack screenOptions={{ headerTintColor: colors.primary, contentStyle: { backgroundColor: colors.background } }}>
      <Stack.Screen name="index" options={{ title: 'Closet' }} />
    </Stack>
  );
}
