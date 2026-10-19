import { useLocalSearchParams } from 'expo-router';
import { useMemo, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { useFitReport, useGarments } from '@/api/hooks';
import type { Label, Zone } from '@/api/schema';
import { ErrorNotice } from '@/components/Card';
import { Toggle } from '@/components/Choice';
import { LabelChip } from '@/components/Chips';
import { BodyAvatar, type ZoneLabels } from '@/components/BodyAvatar';
import { Screen } from '@/components/Screen';
import { zoneDisplayName } from '@/fit/format';
import { spacing, typography } from '@/theme';

export default function AvatarScreen() {
  const { reportId } = useLocalSearchParams<{ reportId: string }>();
  const report = useFitReport(reportId);
  const garments = useGarments();
  const [showReference, setShowReference] = useState(false);
  const [size, setSize] = useState<string | null>(null);

  const sizes = report.data?.report.sizes ?? [];
  const selected = sizes.find((s) => s.size_label === (size ?? report.data?.report.pick?.size_label)) ?? report.data?.report.pick ?? null;

  const zones = useMemo<ZoneLabels>(() => {
    const out: ZoneLabels = {};
    for (const z of selected?.zones ?? []) out[z.zone] = z.label;
    return out;
  }, [selected]);

  const reference = useMemo(() => {
    const ref = garments.data?.find((g) => g.id === report.data?.reference_garment_id) ?? garments.data?.find((g) => g.is_reference);
    return ref
      ? { chestWidthCm: ref.measurements?.chest_width?.value_cm, lengthCm: ref.measurements?.length?.value_cm }
      : null;
  }, [garments.data, report.data]);

  if (report.isPending) return <Screen><Text style={typography.caption}>Loading…</Text></Screen>;
  if (!report.data) return <Screen><ErrorNotice error={report.error ?? new Error('Report not found')} /></Screen>;

  return (
    <Screen scroll={false}>
      <View style={styles.sizes}>
        {sizes.map((s) => (
          <Text
            key={s.size_label}
            onPress={() => setSize(s.size_label)}
            style={[styles.size, s.size_label === selected?.size_label && styles.sizeSelected]}>
            {s.size_label}
          </Text>
        ))}
      </View>
      <BodyAvatar zones={zones} showReference={showReference} reference={reference} />
      <Toggle label="Show reference outline" value={showReference} onChange={setShowReference} />
      <View style={styles.legend}>
        {(Object.entries(zones) as [Zone, Label | null][]).map(([zone, label]) => (
          <View key={zone} style={styles.legendItem}>
            <Text style={typography.caption}>{zoneDisplayName(zone)}</Text>
            <LabelChip label={label} />
          </View>
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  sizes: { flexDirection: 'row', gap: spacing.sm, flexWrap: 'wrap' },
  size: { ...typography.body, paddingHorizontal: spacing.md, paddingVertical: spacing.xs, borderRadius: 999, borderWidth: 1, borderColor: '#DAD4CA' },
  sizeSelected: { backgroundColor: '#1F4E5F', color: '#fff', borderColor: '#1F4E5F' },
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs },
});
