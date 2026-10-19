import { useLocalSearchParams, useRouter } from 'expo-router';
import { Alert, StyleSheet, Text, View } from 'react-native';

import { useDeleteGarment, useGarment, useUpdateGarment } from '@/api/hooks';
import { GARMENT_FIELDS, toGarmentUpdate } from '@/api/schema';
import { Button } from '@/components/Button';
import { Card, ErrorNotice, Row } from '@/components/Card';
import { LabelChip } from '@/components/Chips';
import { Screen } from '@/components/Screen';
import { CUT_OPTIONS, FIELD_NAMES, KIND_NAMES, STRETCH_NAMES } from '@/closet/options';
import { colors, spacing, typography } from '@/theme';

export default function GarmentDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const garment = useGarment(id);
  const update = useUpdateGarment(id ?? '');
  const remove = useDeleteGarment();

  if (garment.isPending) return <Screen><Text style={typography.caption}>Loading…</Text></Screen>;
  if (!garment.data) return <Screen><ErrorNotice error={garment.error ?? new Error('Garment not found')} /></Screen>;
  const g = garment.data;

  const confirmDelete = () =>
    Alert.alert('Delete garment?', `${g.name ?? 'This garment'} will be removed from your closet.`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: () => remove.mutateAsync(g.id).then(() => router.back()),
      },
    ]);

  return (
    <Screen>
      <View style={styles.titleRow}>
        <Text style={[typography.title, { flex: 1 }]}>{g.name ?? 'Untitled garment'}</Text>
        {g.is_reference ? <Text style={styles.star}>★</Text> : null}
      </View>
      <View style={styles.metaRow}>
        <Text style={typography.caption}>
          {KIND_NAMES[g.kind]}
          {g.size_label ? ` · ${g.size_label}` : ''} · {STRETCH_NAMES[g.stretch]} ·{' '}
          {CUT_OPTIONS.find((c) => c.value === g.cut)?.label}
        </Text>
        <LabelChip label={g.fit_tag} />
      </View>

      <Card>
        <Text style={typography.heading}>Measurements (flat, cm)</Text>
        {GARMENT_FIELDS.map((field) => {
          const m = g.measurements?.[field];
          if (!m) return null;
          return <Row key={field} label={FIELD_NAMES[field]} value={`${m.value_cm} cm · ${m.source}`} />;
        })}
        {!g.measurements || Object.keys(g.measurements).length === 0 ? (
          <Text style={typography.caption}>No measurements yet.</Text>
        ) : null}
      </Card>

      <ErrorNotice error={update.error ?? remove.error} />
      <Button
        title={g.is_reference ? 'This is your reference' : 'Use as reference'}
        variant="secondary"
        disabled={g.is_reference}
        loading={update.isPending}
        onPress={() => update.mutate(toGarmentUpdate(g, { is_reference: true }))}
      />
      <Button title="Delete" variant="danger" loading={remove.isPending} onPress={confirmDelete} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  metaRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: spacing.sm, flexWrap: 'wrap' },
  star: { color: colors.star, fontSize: 26 },
});
