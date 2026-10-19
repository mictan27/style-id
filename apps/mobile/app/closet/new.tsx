import { useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { useCreateGarment } from '@/api/hooks';
import type { Cut, GarmentCreate, GarmentField, GarmentKind, GarmentMeasurements, Label } from '@/api/schema';
import { Button } from '@/components/Button';
import { Card, ErrorNotice } from '@/components/Card';
import { Choice, Toggle } from '@/components/Choice';
import { FieldGuide } from '@/components/FieldGuide';
import { Screen } from '@/components/Screen';
import { CmField, parseCm, TextField } from '@/components/TextField';
import {
  CUT_OPTIONS,
  FABRIC_OPTIONS,
  FABRIC_TO_STRETCH,
  FIELDS_FOR_KIND,
  FIT_TAG_OPTIONS,
  KIND_OPTIONS,
  type Fabric,
} from '@/closet/options';
import { spacing, typography } from '@/theme';

type Method = 'choose' | 'manual';

export default function NewGarmentScreen() {
  const router = useRouter();
  const [method, setMethod] = useState<Method>('choose');

  if (method === 'choose') {
    return (
      <Screen>
        <Text style={typography.heading}>How do you want to add it?</Text>
        <Card onPress={() => router.replace('/closet/capture')}>
          <Text style={typography.heading}>Measure with camera</Text>
          <Text style={typography.caption}>
            Lay the top flat on the floor, point the camera at it, and drag the landmarks we propose. Needs an iPhone.
          </Text>
        </Card>
        <Card onPress={() => setMethod('manual')}>
          <Text style={typography.heading}>Type measurements</Text>
          <Text style={typography.caption}>Use a tape on the garment laid flat. Each field shows where to measure.</Text>
        </Card>
      </Screen>
    );
  }
  return <ManualEntryForm />;
}

function ManualEntryForm() {
  const router = useRouter();
  const create = useCreateGarment();
  const [name, setName] = useState('');
  const [kind, setKind] = useState<GarmentKind>('tee');
  const [fabric, setFabric] = useState<Fabric>('cotton_tee');
  const [cut, setCut] = useState<Cut>('set_in');
  const [sizeLabel, setSizeLabel] = useState('');
  const [fitTag, setFitTag] = useState<Label>('regular');
  const [isReference, setIsReference] = useState(true);
  const [values, setValues] = useState<Partial<Record<GarmentField, string>>>({});

  const fields = FIELDS_FOR_KIND[kind];
  const measurements: GarmentMeasurements = {};
  for (const field of fields) {
    const cm = parseCm(values[field] ?? '');
    if (cm !== null) measurements[field] = { value_cm: cm, source: 'manual', confidence: 'medium' };
  }
  const canSubmit = name.trim().length > 0 && measurements.chest_width !== undefined && measurements.length !== undefined;

  const submit = async () => {
    const body: GarmentCreate = {
      name: name.trim(),
      kind,
      stretch: FABRIC_TO_STRETCH[fabric],
      cut,
      size_label: sizeLabel.trim() || null,
      fit_tag: fitTag,
      is_reference: isReference,
      length_from_center_back: false,
      sleeve_from_center_back: false,
      measurements,
    };
    const garment = await create.mutateAsync(body);
    router.replace({ pathname: '/closet/[id]', params: { id: garment.id } });
  };

  return (
    <Screen>
      <TextField label="Name" placeholder="Grey tee" value={name} onChangeText={setName} />
      <Choice label="Kind" options={KIND_OPTIONS} value={kind} onChange={setKind} />
      <Choice label="Fabric" options={FABRIC_OPTIONS} value={fabric} onChange={setFabric} />
      <Choice label="Cut" options={CUT_OPTIONS} value={cut} onChange={setCut} />
      <TextField label="Size label" placeholder="M" autoCapitalize="characters" value={sizeLabel} onChangeText={setSizeLabel} />
      <Choice label="How does it fit you?" options={FIT_TAG_OPTIONS} value={fitTag} onChange={setFitTag} />

      <Text style={[typography.heading, { marginTop: spacing.md }]}>Measurements, laid flat</Text>
      <Text style={typography.caption}>Chest width and length are required; the rest sharpen the result.</Text>
      {fields.map((field) => (
        <View key={field} style={styles.fieldBlock}>
          <FieldGuide field={field} size={96} />
          <CmField label={''} value={values[field] ?? ''} onChange={(text) => setValues((v) => ({ ...v, [field]: text }))} />
        </View>
      ))}

      <Toggle
        label="Use as my reference"
        hint="Every product you check is compared against the reference garment."
        value={isReference}
        onChange={setIsReference}
      />
      <ErrorNotice error={create.error} />
      <Button title="Save garment" disabled={!canSubmit} loading={create.isPending} onPress={submit} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  fieldBlock: { gap: spacing.sm, paddingVertical: spacing.sm },
});
