import { useLocalSearchParams, useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { useFitReport, useGarments } from '@/api/hooks';
import { ZONES, type SizeResultModel } from '@/api/schema';
import { Button } from '@/components/Button';
import { Card, ErrorNotice } from '@/components/Card';
import { ConfidenceBadge } from '@/components/Chips';
import { Screen } from '@/components/Screen';
import { ZoneRow } from '@/components/ZoneRow';
import { formatDiff } from '@/fit/format';
import { colors, typography } from '@/theme';

export default function FitReportScreen() {
  const { reportId } = useLocalSearchParams<{ reportId: string }>();
  const router = useRouter();
  const query = useFitReport(reportId);
  const garments = useGarments();

  if (query.isPending) return <Screen><Text style={typography.caption}>Loading…</Text></Screen>;
  if (!query.data) return <Screen><ErrorNotice error={query.error ?? new Error('Report not found')} /></Screen>;
  const fit = query.data;
  const r = fit.report;
  const referenceGarment = garments.data?.find((g) => g.id === fit.reference_garment_id);
  const referenceName = referenceGarment?.name ?? (fit.reference_garment_id ? 'reference tee' : null);
  const excluded = r.sizes.filter((s) => s.excluded_reason);

  return (
    <Screen>
      <Text style={typography.title}>{fit.product.title ?? 'Fit report'}</Text>
      <Text style={typography.caption}>
        {fit.product.brand?.name ?? fit.product.url_canonical}
        {r.reference_size_label ? ` · you wear ${r.reference_size_label} in your reference` : ''}
      </Text>
      <ConfidenceBadge confidence={r.overall_confidence} showHint />

      <PickCard title="Our pick" size={r.pick} referenceName={referenceName} highlight />
      {r.runner_up ? <PickCard title="Runner-up" size={r.runner_up} referenceName={referenceName} /> : null}

      {r.diffs_cm && r.pick && r.runner_up ? (
        <Card>
          <Text style={typography.heading}>
            What would change: {r.pick.size_label} → {r.runner_up.size_label}
          </Text>
          {ZONES.filter((z) => r.diffs_cm?.[z] !== undefined).map((zone) => (
            <Text key={zone} style={typography.body}>
              {formatDiff(zone, r.diffs_cm?.[zone] ?? 0)}
            </Text>
          ))}
        </Card>
      ) : null}

      {excluded.length ? (
        <Card>
          <Text style={typography.heading}>Excluded sizes</Text>
          {excluded.map((s) => (
            <Text key={s.size_label} style={typography.body}>
              {s.size_label}: {s.excluded_reason}
            </Text>
          ))}
        </Card>
      ) : null}

      <Button
        title="See it on your avatar"
        variant="secondary"
        onPress={() => router.push({ pathname: '/avatar/[reportId]', params: { reportId: fit.id } })}
      />
      <Button
        title="Record what happened"
        onPress={() => router.push({ pathname: '/outcomes/[reportId]', params: { reportId: fit.id } })}
      />
      <Text style={typography.caption}>Engine {r.engine_version}{referenceName ? ` · compared with your ${referenceName}` : ''}</Text>
    </Screen>
  );
}

function PickCard({
  title,
  size,
  referenceName,
  highlight,
}: {
  title: string;
  size: SizeResultModel | null;
  referenceName: string | null;
  highlight?: boolean;
}) {
  if (!size) {
    return (
      <Card>
        <Text style={typography.heading}>{title}</Text>
        <Text style={typography.body}>No size of this product fits well enough to recommend.</Text>
      </Card>
    );
  }
  return (
    <Card style={highlight ? styles.highlight : undefined}>
      <View style={styles.pickRow}>
        <Text style={typography.caption}>{title}</Text>
        <Text style={typography.title}>{size.size_label}</Text>
      </View>
      {size.zones.map((z) => (
        <ZoneRow key={z.zone} zone={z} referenceName={referenceName} />
      ))}
    </Card>
  );
}


const styles = StyleSheet.create({
  highlight: { borderColor: colors.primary, borderWidth: 2 },
  pickRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
});
