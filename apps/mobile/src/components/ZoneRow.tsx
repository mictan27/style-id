import { StyleSheet, Text, View } from 'react-native';

import type { ZoneResultModel } from '@/api/schema';
import { LabelChip } from '@/components/Chips';
import { formatEase, formatEaseShort, zoneDisplayName } from '@/fit/format';
import { colors, spacing, typography } from '@/theme';

/** One fit-report row: zone name, label chip (or position offset), and the plain-language sentence. */
export function ZoneRow({ zone, referenceName }: { zone: ZoneResultModel; referenceName: string | null }) {
  return (
    <View style={styles.zoneRow}>
      <View style={styles.zoneHead}>
        <Text style={[typography.body, { fontWeight: '600' }]}>{zoneDisplayName(zone.zone)}</Text>
        {zone.position ? (
          <Text style={typography.caption}>{formatEaseShort(zone, referenceName)}</Text>
        ) : (
          <LabelChip label={zone.label} />
        )}
      </View>
      <Text style={typography.caption}>{formatEase(zone, referenceName)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  zoneRow: {
    paddingVertical: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
    gap: 2,
  },
  zoneHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
});
