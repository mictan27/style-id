import { useRouter } from 'expo-router';
import { Platform, Text } from 'react-native';

import { useCurrentBodyRecord, useMe } from '@/api/hooks';
import { BODY_FIELDS } from '@/api/schema';
import { BODY_FIELD_NAMES } from '@/body/fields';
import { Button } from '@/components/Button';
import { Card, EmptyState, ErrorNotice, Row } from '@/components/Card';
import { Screen } from '@/components/Screen';
import { typography } from '@/theme';
import * as ArCapture from '@modules/ar-capture';

export default function BodyScreen() {
  const router = useRouter();
  const me = useMe();
  const record = useCurrentBodyRecord();
  const lidar = Platform.OS === 'ios' && ArCapture.isLidarAvailable();
  const adult = me.data?.dob_verified_18 ?? false;

  return (
    <Screen>
      <ErrorNotice error={record.error} />
      {record.data ? (
        <Card>
          <Text style={typography.heading}>Your body record</Text>
          <Text style={typography.caption}>
            Source: {record.data.source} · {record.data.confirmed_at ? 'confirmed' : 'not confirmed yet'}
          </Text>
          {BODY_FIELDS.map((field) => {
            const m = record.data?.measurements?.[field];
            return m ? <Row key={field} label={BODY_FIELD_NAMES[field]} value={`${m.value_cm} cm`} /> : null;
          })}
        </Card>
      ) : record.isPending ? (
        <Text style={typography.caption}>Loading…</Text>
      ) : (
        <EmptyState
          title="Optional, but sharper"
          body="A body record turns 'more room than your grey tee' into actual ease against you. Scan with LiDAR, take two photos, or type a few numbers."
        />
      )}

      <Text style={typography.heading}>Update</Text>
      {!adult ? (
        <Text style={typography.caption}>Body scanning is adults-only. Confirm your age at sign-in to enable it.</Text>
      ) : null}
      <Button
        title={lidar ? 'LiDAR scan (recommended)' : 'LiDAR scan (needs an iPhone Pro)'}
        disabled={!lidar || !adult}
        onPress={() => router.push('/body/scan')}
      />
      <Button title="Photo scan (front + side)" variant="secondary" disabled={!adult} onPress={() => router.push('/body/photo')} />
      <Button title={'Enter manually / "I\'m an M in brand X"'} variant="secondary" onPress={() => router.push('/body/manual')} />
    </Screen>
  );
}
