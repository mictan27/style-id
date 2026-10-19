import type { PropsWithChildren } from 'react';
import { ScrollView, StyleSheet, View, type ViewStyle } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors, spacing } from '@/theme';

interface ScreenProps extends PropsWithChildren {
  /** Scrollable by default; set false for canvases and camera views. */
  scroll?: boolean;
  padded?: boolean;
  style?: ViewStyle;
}

export function Screen({ children, scroll = true, padded = true, style }: ScreenProps) {
  const insets = useSafeAreaInsets();
  const padding = padded ? styles.padded : undefined;
  if (!scroll) {
    return <View style={[styles.root, padding, { paddingBottom: insets.bottom }, style]}>{children}</View>;
  }
  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={[padding, { paddingBottom: insets.bottom + spacing.xl }, style]}
      keyboardShouldPersistTaps="handled">
      {children}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.background },
  padded: { padding: spacing.lg, gap: spacing.md },
});
