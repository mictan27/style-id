import { ActivityIndicator, Pressable, StyleSheet, Text, type ViewStyle } from 'react-native';

import { colors, radius, spacing } from '@/theme';

interface ButtonProps {
  title: string;
  onPress?: () => void;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
  testID?: string;
}

export function Button({ title, onPress, variant = 'primary', disabled, loading, style, testID }: ButtonProps) {
  const inactive = disabled || loading;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityState={{ disabled: inactive }}
      onPress={inactive ? undefined : onPress}
      style={({ pressed }) => [styles.base, styles[variant], inactive && styles.disabled, pressed && styles.pressed, style]}>
      {loading ? (
        <ActivityIndicator color={variant === 'primary' || variant === 'danger' ? colors.primaryText : colors.primary} />
      ) : (
        <Text style={[styles.text, variant === 'primary' || variant === 'danger' ? styles.textOnDark : styles.textOnLight]}>
          {title}
        </Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: 48,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primary: { backgroundColor: colors.primary },
  secondary: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  danger: { backgroundColor: colors.danger },
  ghost: { backgroundColor: 'transparent' },
  disabled: { opacity: 0.5 },
  pressed: { opacity: 0.85 },
  text: { fontSize: 16, fontWeight: '600' },
  textOnDark: { color: colors.primaryText },
  textOnLight: { color: colors.primary },
});
