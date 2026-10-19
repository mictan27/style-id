import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Text } from 'react-native';

import { BODY_FIELDS, type BodyField, type MeasurementModel } from '@/api/schema';
import { BODY_FIELD_GUIDE, BODY_FIELD_NAMES } from '@/body/fields';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { CmField, parseCm, TextField } from '@/components/TextField';
import { useBodyDraft } from '@/store/bodyDraft';
import { spacing, typography } from '@/theme';

export default function ManualBodyScreen() {
  const router = useRouter();
  const setDraft = useBodyDraft((s) => s.setDraft);
  const [values, setValues] = useState<Partial<Record<BodyField, string>>>({});
  const [brand, setBrand] = useState('');
  const [sizeLabel, setSizeLabel] = useState('');

  const measurements: Partial<Record<BodyField, MeasurementModel>> = {};
  for (const field of BODY_FIELDS) {
    const cm = parseCm(values[field] ?? '');
    if (cm !== null) measurements[field] = { value_cm: cm, source: 'manual', confidence: 'high' };
  }
  const anchor =
    brand.trim() && sizeLabel.trim() ? { brand: brand.trim(), size_label: sizeLabel.trim().toUpperCase() } : null;
  const canContinue = Object.keys(measurements).length > 0 || anchor !== null;

  const next = () => {
    setDraft({
      source: anchor && Object.keys(measurements).length === 0 ? 'size_anchor' : 'manual',
      measurements,
      size_anchor: anchor,
    });
    router.push('/body/confirm');
  };

  return (
    <Screen>
      <Text style={typography.heading}>Tape measurements</Text>
      <Text style={typography.caption}>Fill in what you know; chest is the most useful.</Text>
      {BODY_FIELDS.map((field) => (
        <CmField
          key={field}
          label={BODY_FIELD_NAMES[field]}
          hint={BODY_FIELD_GUIDE[field]}
          value={values[field] ?? ''}
          onChange={(text) => setValues((v) => ({ ...v, [field]: text }))}
        />
      ))}
      <Text style={[typography.heading, { marginTop: spacing.lg }]}>Or anchor on a size you own</Text>
      <Text style={typography.caption}>&ldquo;I&rsquo;m an M in brand X&rdquo; lets us estimate from that brand&rsquo;s chart.</Text>
      <TextField label="Brand" placeholder="Uniqlo" value={brand} onChangeText={setBrand} />
      <TextField label="Size" placeholder="M" autoCapitalize="characters" value={sizeLabel} onChangeText={setSizeLabel} />
      <Button title="Continue" disabled={!canContinue} onPress={next} />
    </Screen>
  );
}
