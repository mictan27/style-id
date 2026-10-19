import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Text } from 'react-native';

import { useCreateOutcome, useFitReport } from '@/api/hooks';
import { ZONES, type Direction, type Zone } from '@/api/schema';
import { Button } from '@/components/Button';
import { ErrorNotice } from '@/components/Card';
import { Choice } from '@/components/Choice';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { zoneDisplayName } from '@/fit/format';
import { typography } from '@/theme';

const ZONE_OPTIONS = ZONES.map((z) => ({ value: z, label: zoneDisplayName(z) }));
const DIRECTION_OPTIONS = [
  { value: 'tight', label: 'Too tight' },
  { value: 'loose', label: 'Too loose' },
] as const;
const KEPT_OPTIONS = [
  { value: 'kept', label: 'Kept it' },
  { value: 'returned', label: 'Returned it' },
] as const;

export default function OutcomeScreen() {
  const { reportId } = useLocalSearchParams<{ reportId: string }>();
  const router = useRouter();
  const report = useFitReport(reportId);
  const create = useCreateOutcome();
  const [kept, setKept] = useState<'kept' | 'returned' | null>(null);
  const [zone, setZone] = useState<Zone | null>(null);
  const [direction, setDirection] = useState<Direction | null>(null);
  const [sizeBought, setSizeBought] = useState('');

  const sizeOptions = report.data?.report.sizes.map((s) => ({ value: s.size_label, label: s.size_label })) ?? [];
  const canSubmit = kept !== null && sizeBought.trim().length > 0 && (kept === 'kept' || (zone && direction));

  const submit = async () => {
    if (!reportId || !kept) return;
    await create.mutateAsync({
      fit_report_id: reportId,
      size_bought: sizeBought.trim(),
      kept: kept === 'kept',
      zone: kept === 'returned' ? zone : null,
      direction: kept === 'returned' ? direction : null,
    });
    router.back();
  };

  return (
    <Screen>
      <Text style={typography.heading}>How did it go?</Text>
      <Text style={typography.caption}>One answer makes the next report better for you and everyone else.</Text>
      {sizeOptions.length ? (
        <Choice label="Size you bought" options={sizeOptions} value={sizeBought} onChange={setSizeBought} />
      ) : (
        <TextField label="Size you bought" placeholder="M" autoCapitalize="characters" value={sizeBought} onChangeText={setSizeBought} />
      )}
      <Choice options={KEPT_OPTIONS} value={kept} onChange={setKept} />
      {kept === 'returned' ? (
        <>
          <Choice label="Where was the problem?" options={ZONE_OPTIONS} value={zone} onChange={setZone} />
          <Choice label="Which way?" options={DIRECTION_OPTIONS} value={direction} onChange={setDirection} />
        </>
      ) : null}
      <ErrorNotice error={create.error} />
      <Button title="Submit" disabled={!canSubmit} loading={create.isPending} onPress={submit} />
    </Screen>
  );
}
