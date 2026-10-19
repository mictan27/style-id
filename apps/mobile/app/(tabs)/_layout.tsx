import { Tabs } from 'expo-router/js-tabs';
import { Text, type ColorValue } from 'react-native';

import { colors } from '@/theme';

function icon(glyph: string) {
  return function TabIcon({ color }: { color: ColorValue }) {
    return <Text style={{ color, fontSize: 18 }}>{glyph}</Text>;
  };
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
      }}>
      <Tabs.Screen name="closet" options={{ title: 'Closet', tabBarIcon: icon('▣') }} />
      <Tabs.Screen name="check" options={{ title: 'Check', tabBarIcon: icon('✓') }} />
      <Tabs.Screen name="body" options={{ title: 'Body', tabBarIcon: icon('◯') }} />
    </Tabs>
  );
}
