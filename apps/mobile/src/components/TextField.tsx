import { StyleSheet, Text, TextInput, View, type TextInputProps } from 'react-native';

import { colors, radius, spacing, typography } from '@/theme';

interface TextFieldProps extends TextInputProps {
  label?: string;
  hint?: string;
  error?: string | null;
  suffix?: string;
}

export function TextField({ label, hint, error, suffix, style, ...rest }: TextFieldProps) {
  return (
    <View style={styles.wrap}>
      {label ? <Text style={styles.label}>{label}</Text> : null}
      <View style={[styles.inputRow, error ? styles.inputError : null]}>
        <TextInput
          style={[styles.input, style]}
          placeholderTextColor={colors.textMuted}
          accessibilityLabel={label}
          {...rest}
        />
        {suffix ? <Text style={styles.suffix}>{suffix}</Text> : null}
      </View>
      {error ? <Text style={styles.error}>{error}</Text> : hint ? <Text style={styles.hint}>{hint}</Text> : null}
    </View>
  );
}

/** Numeric cm input that keeps a string while typing and reports a parsed number. */
export function CmField({
  label,
  value,
  onChange,
  hint,
  accessibilityLabel,
}: {
  label: string;
  value: string;
  onChange: (text: string) => void;
  hint?: string;
  /** Spoken name when the visible label is elsewhere (e.g. a field guide drawing). */
  accessibilityLabel?: string;
}) {
  const parsed = value.trim() === '' ? null : Number(value.replace(',', '.'));
  const invalid = parsed !== null && (!Number.isFinite(parsed) || parsed <= 0 || parsed >= 400);
  return (
    <TextField
      label={label}
      accessibilityLabel={accessibilityLabel ?? label}
      value={value}
      onChangeText={onChange}
      keyboardType="decimal-pad"
      inputMode="decimal"
      suffix="cm"
      hint={hint}
      error={invalid ? 'Enter a value between 0 and 400 cm' : null}
    />
  );
}

export function parseCm(value: string): number | null {
  const n = Number(value.replace(',', '.'));
  return value.trim() !== '' && Number.isFinite(n) && n > 0 && n < 400 ? Math.round(n * 10) / 10 : null;
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.xs },
  label: { ...typography.caption, color: colors.text, fontWeight: '600' },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
  },
  inputError: { borderColor: colors.danger },
  input: { flex: 1, minHeight: 44, fontSize: 16, color: colors.text },
  suffix: { ...typography.caption, marginLeft: spacing.sm },
  hint: typography.caption,
  error: { ...typography.caption, color: colors.danger },
});
