import { StyleSheet, Text, View } from 'react-native';

import type { Confidence, Label } from '@/api/schema';
import { confidenceBadge, LABEL_NAMES, labelColor, labelSoftColor } from '@/fit/format';
import { radius, spacing } from '@/theme';

export function LabelChip({ label }: { label: Label | null | undefined }) {
  return (
    <View style={[styles.chip, { backgroundColor: labelSoftColor(label) }]}>
      <Text style={[styles.chipText, { color: labelColor(label) }]}>{label ? LABEL_NAMES[label] : 'n/a'}</Text>
    </View>
  );
}

export function ConfidenceBadge({ confidence, showHint }: { confidence: Confidence; showHint?: boolean }) {
  const badge = confidenceBadge(confidence);
  return (
    <View style={styles.badgeWrap}>
      <View style={[styles.chip, styles.outlined, { borderColor: badge.color }]}>
        <View style={[styles.dot, { backgroundColor: badge.color }]} />
        <Text style={[styles.chipText, { color: badge.color }]}>{badge.text}</Text>
      </View>
      {showHint ? <Text style={styles.hint}>{badge.hint}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    alignSelf: 'flex-start',
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
    borderRadius: radius.pill,
  },
  outlined: { borderWidth: 1, backgroundColor: 'transparent' },
  chipText: { fontSize: 13, fontWeight: '600' },
  dot: { width: 8, height: 8, borderRadius: 4 },
  badgeWrap: { gap: spacing.xs },
  hint: { fontSize: 13, color: '#6E675E' },
});
