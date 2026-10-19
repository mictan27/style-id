import type { PropsWithChildren } from 'react';
import { Pressable, StyleSheet, Text, View, type ViewStyle } from 'react-native';

import { colors, radius, spacing, typography } from '@/theme';

export function Card({ children, onPress, style }: PropsWithChildren<{ onPress?: () => void; style?: ViewStyle }>) {
  if (onPress) {
    return (
      <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.card, pressed && styles.pressed, style]}>
        {children}
      </Pressable>
    );
  }
  return <View style={[styles.card, style]}>{children}</View>;
}

export function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

export function EmptyState({ title, body, children }: PropsWithChildren<{ title: string; body: string }>) {
  return (
    <View style={styles.empty}>
      <Text style={typography.heading}>{title}</Text>
      <Text style={[typography.body, { textAlign: 'center', color: colors.textMuted }]}>{body}</Text>
      {children}
    </View>
  );
}

export function ErrorNotice({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : String(error);
  return (
    <View style={styles.error}>
      <Text style={{ color: colors.danger }}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    gap: spacing.sm,
  },
  pressed: { opacity: 0.85 },
  row: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: spacing.xs },
  rowLabel: { ...typography.body, color: colors.textMuted },
  rowValue: { ...typography.body, fontWeight: '600' },
  empty: { alignItems: 'center', gap: spacing.md, padding: spacing.xl, marginTop: spacing.xxl },
  error: {
    backgroundColor: colors.labelSoft.tight,
    borderRadius: radius.md,
    padding: spacing.md,
  },
});
