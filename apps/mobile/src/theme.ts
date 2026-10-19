import type { Confidence, Label } from '@/api/schema';

export const colors = {
  background: '#F7F5F1',
  surface: '#FFFFFF',
  surfaceMuted: '#EFEBE4',
  border: '#DAD4CA',
  text: '#1C1A17',
  textMuted: '#6E675E',
  primary: '#1F4E5F',
  primaryText: '#FFFFFF',
  danger: '#B3261E',
  success: '#2E7D32',
  star: '#D99A1E',
  label: {
    tight: '#C62828',
    fitted: '#E09F1F',
    regular: '#2E7D32',
    relaxed: '#1E6FB3',
  } satisfies Record<Label, string>,
  labelSoft: {
    tight: '#FBE3E1',
    fitted: '#FCEFD3',
    regular: '#DFF0DF',
    relaxed: '#DCEBF8',
  } satisfies Record<Label, string>,
  confidence: {
    high: '#2E7D32',
    medium: '#E09F1F',
    low: '#9E9E9E',
  } satisfies Record<Confidence, string>,
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const radius = {
  sm: 6,
  md: 10,
  lg: 16,
  pill: 999,
} as const;

export const typography = {
  title: { fontSize: 28, fontWeight: '700' as const, color: colors.text },
  heading: { fontSize: 20, fontWeight: '600' as const, color: colors.text },
  body: { fontSize: 16, fontWeight: '400' as const, color: colors.text, lineHeight: 22 },
  caption: { fontSize: 13, fontWeight: '400' as const, color: colors.textMuted },
  mono: { fontSize: 15, fontVariant: ['tabular-nums'] as ('tabular-nums')[], color: colors.text },
} as const;

export const theme = { colors, spacing, radius, typography };
export type Theme = typeof theme;
