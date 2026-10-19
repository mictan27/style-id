import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Text } from 'react-native';

import { useConfirmBodyRecord, useCreateBodyRecord } from '@/api/hooks';
import { BODY_FIELDS, type BodyField } from '@/api/schema';
import { BODY_FIELD_NAMES } from '@/body/fields';
import { Button } from '@/components/Button';
import { ErrorNotice } from '@/components/Card';
import { Screen } from '@/components/Screen';
import { CmField, parseCm } from '@/components/TextField';
import { toBodyRecordCreate, useBodyDraft } from '@/store/bodyDraft';
import { typography } from '@/theme';

/** Every number is editable before it is saved; edited values become `manual`. */
export default function ConfirmBodyScreen() {
  const router = useRouter();
  const draft = useBodyDraft((s) => s.draft);
  const updateMeasurement = useBodyDraft((s) => s.updateMeasurement);
  const clear = useBodyDraft((s) => s.clear);
  const create = useCreateBodyRecord();
  const confirm = useConfirmBodyRecord();
  const [text, setText] = useState<Partial<Record<BodyField, string>>>(() => {
    const out: Partial<Record<BodyField, string>> = {};
    for (const field of BODY_FIELDS) {
      const v = draft?.measurements[field]?.value_cm;
      if (v !== undefined) out[field] = String(v);
    }
    return out;
  });

  if (!draft) {
    return (
      <Screen>
        <Text style={typography.body}>Nothing to confirm yet.</Text>
        <Button title="Back" onPress={() => router.back()} />
      </Screen>
    );
  }

  const pendingScan = Boolean(draft.localScan) && Object.keys(draft.measurements).length <= 1;

  const save = async () => {
    const record = await create.mutateAsync(toBodyRecordCreate(draft));
    if (!pendingScan) {
      // Every value on this screen was seen by the user: send them all as overrides (stored as manual/high).
      const overrides: Record<string, number> = {};
      for (const [field, m] of Object.entries(draft.measurements)) {
        if (m) overrides[field] = m.value_cm;
      }
      await confirm.mutateAsync({ id: record.id, body: { overrides } });
    }
    clear();
    router.dismissTo('/(tabs)/body');
  };

  return (
    <Screen>
      <Text style={typography.heading}>Check your numbers</Text>
      <Text style={typography.caption}>
        Source: {draft.source}.{' '}
        {pendingScan
          ? 'Scan data uploads with this record; measurements fill in when the fit server has processed it, and you can confirm them then.'
          : 'Edit anything that looks off before saving.'}
      </Text>
      {BODY_FIELDS.map((field) => (
        <CmField
          key={field}
          label={BODY_FIELD_NAMES[field]}
          value={text[field] ?? ''}
          onChange={(t) => {
            setText((v) => ({ ...v, [field]: t }));
            updateMeasurement(field, parseCm(t));
          }}
        />
      ))}
      <ErrorNotice error={create.error ?? confirm.error} />
      <Button title="Save body record" loading={create.isPending || confirm.isPending} onPress={save} />
    </Screen>
  );
}
