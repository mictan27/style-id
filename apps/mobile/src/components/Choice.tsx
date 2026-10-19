import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/theme';

export interface ChoiceOption<T extends string> {
  value: T;
  label: string;
  hint?: string;
}

interface ChoiceProps<T extends string> {
  label?: string;
  options: readonly ChoiceOption<T>[];
  value: T | null | undefined;
  onChange: (value: T) => void;
}

/** Wrapping pill selector. Plain, no design polish. */
export function Choice<T extends string>({ label, options, value, onChange }: ChoiceProps<T>) {
  return (
    <View style={styles.wrap}>
      {label ? <Text style={styles.label}>{label}</Text> : null}
      <View style={styles.row}>
        {options.map((option) => {
          const selected = option.value === value;
          return (
            <Pressable
              key={option.value}
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              onPress={() => onChange(option.value)}
              style={[styles.pill, selected && styles.pillSelected]}>
              <Text style={[styles.pillText, selected && styles.pillTextSelected]}>{option.label}</Text>
            </Pressable>
          );
        })}
      </View>
      {value ? (
        <Text style={styles.hint}>{options.find((o) => o.value === value)?.hint ?? ''}</Text>
      ) : null}
    </View>
  );
}

export function Toggle({ label, value, onChange, hint }: { label: string; value: boolean; onChange: (v: boolean) => void; hint?: string }) {
  return (
    <Pressable
      accessibilityRole="checkbox"
      accessibilityState={{ checked: value }}
      onPress={() => onChange(!value)}
      style={styles.toggleRow}>
      <View style={[styles.box, value && styles.boxChecked]}>{value ? <Text style={styles.tick}>✓</Text> : null}</View>
      <View style={{ flex: 1 }}>
        <Text style={typography.body}>{label}</Text>
        {hint ? <Text style={styles.hint}>{hint}</Text> : null}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.xs },
  label: { ...typography.caption, color: colors.text, fontWeight: '600' },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  pill: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  pillSelected: { backgroundColor: colors.primary, borderColor: colors.primary },
  pillText: { fontSize: 15, color: colors.text },
  pillTextSelected: { color: colors.primaryText, fontWeight: '600' },
  hint: typography.caption,
  toggleRow: { flexDirection: 'row', gap: spacing.md, alignItems: 'center', paddingVertical: spacing.sm },
  box: {
    width: 24,
    height: 24,
    borderRadius: radius.sm,
    borderWidth: 1.5,
    borderColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  boxChecked: { backgroundColor: colors.primary },
  tick: { color: colors.primaryText, fontWeight: '700' },
});
