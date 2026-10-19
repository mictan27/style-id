import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { useGarments } from '@/api/hooks';
import type { Garment } from '@/api/schema';
import { Button } from '@/components/Button';
import { Card, EmptyState, ErrorNotice } from '@/components/Card';
import { LabelChip } from '@/components/Chips';
import { Screen } from '@/components/Screen';
import { KIND_NAMES } from '@/closet/options';
import { colors, spacing, typography } from '@/theme';

export default function ClosetScreen() {
  const router = useRouter();
  const garments = useGarments();

  return (
    <Screen>
      <Button title="Add a garment" onPress={() => router.push('/closet/new')} />
      <ErrorNotice error={garments.error} />
      {garments.data && garments.data.length === 0 ? (
        <EmptyState
          title="Measure one tee you love"
          body="Lay your favourite top flat, photograph it, and every product you check gets compared against it: more room here, less there, in centimetres.">
          <Button title="Measure with camera" variant="secondary" onPress={() => router.push('/closet/capture')} />
        </EmptyState>
      ) : null}
      {garments.data?.map((g) => (
        <GarmentCard key={g.id} garment={g} onPress={() => router.push({ pathname: '/closet/[id]', params: { id: g.id } })} />
      ))}
    </Screen>
  );
}

function GarmentCard({ garment, onPress }: { garment: Garment; onPress: () => void }) {
  const chest = garment.measurements?.chest_width?.value_cm;
  return (
    <Card onPress={onPress}>
      <View style={styles.titleRow}>
        <Text style={[typography.heading, { flex: 1 }]} numberOfLines={1}>
          {garment.name ?? 'Untitled garment'}
        </Text>
        {garment.is_reference ? (
          <Text accessibilityLabel="Reference garment" style={styles.star}>
            ★
          </Text>
        ) : null}
      </View>
      <View style={styles.metaRow}>
        <Text style={typography.caption}>
          {KIND_NAMES[garment.kind]}
          {garment.size_label ? ` · ${garment.size_label}` : ''}
          {chest ? ` · chest ${chest} cm` : ''}
        </Text>
        <LabelChip label={garment.fit_tag} />
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  metaRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: spacing.sm },
  star: { color: colors.star, fontSize: 22 },
});
