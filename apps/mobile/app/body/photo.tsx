import { CameraView, useCameraPermissions } from 'expo-camera';
import { useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/Button';
import { ErrorNotice } from '@/components/Card';
import { Screen } from '@/components/Screen';
import { CmField, parseCm } from '@/components/TextField';
import { useBodyDraft } from '@/store/bodyDraft';
import { colors, spacing, typography } from '@/theme';

type Pose = 'front' | 'side';
const TIMER_SECONDS = 10;

export default function PhotoScanScreen() {
  const router = useRouter();
  const setDraft = useBodyDraft((s) => s.setDraft);
  const [permission, requestPermission] = useCameraPermissions();
  const [height, setHeight] = useState('');
  const [pose, setPose] = useState<Pose | null>(null);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [shots, setShots] = useState<Partial<Record<Pose, string>>>({});
  const [error, setError] = useState<unknown>(null);
  const camera = useRef<CameraView>(null);

  useEffect(() => {
    if (countdown === null) return;
    if (countdown === 0) {
      camera.current
        ?.takePictureAsync({ quality: 0.9 })
        .then((picture) => {
          if (pose) setShots((s) => ({ ...s, [pose]: picture.uri }));
          setPose(null);
        })
        .catch(setError)
        .finally(() => setCountdown(null));
      return;
    }
    const t = setTimeout(() => setCountdown(countdown - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown, pose]);

  const heightCm = parseCm(height);
  const front = shots.front;
  const side = shots.side;
  const ready = heightCm !== null && front !== undefined && side !== undefined;

  const finish = () => {
    if (heightCm === null || !front || !side) return;
    setDraft({
      source: 'photo',
      measurements: { height: { value_cm: heightCm, source: 'manual', confidence: 'high' } },
      localScan: { photos: [front, side], heightCm },
    });
    router.replace('/body/confirm');
  };

  if (!permission) {
    return (
      <Screen>
        <Text style={typography.caption}>Checking camera permission…</Text>
      </Screen>
    );
  }
  if (!permission.granted) {
    return (
      <Screen>
        <Text style={typography.heading}>Camera access</Text>
        <Text style={typography.body}>
          Two photos, front and side, are processed on our server into body measurements and then deleted.
        </Text>
        <Button title="Allow camera" onPress={() => void requestPermission()} />
      </Screen>
    );
  }

  if (pose) {
    return (
      <View style={styles.cameraRoot}>
        <CameraView ref={camera} style={StyleSheet.absoluteFill} facing="front" />
        <View style={styles.overlay}>
          <Text style={typography.heading}>
            {pose === 'front' ? 'Face the camera' : 'Turn to your side'} · {countdown ?? TIMER_SECONDS}
          </Text>
          <Text style={typography.caption}>Stand two metres away, arms slightly out, whole body in frame.</Text>
          {countdown === null ? (
            <Button title={`Start ${TIMER_SECONDS}-second timer`} onPress={() => setCountdown(TIMER_SECONDS)} />
          ) : null}
          <Button
            title="Cancel"
            variant="secondary"
            onPress={() => {
              setPose(null);
              setCountdown(null);
            }}
          />
        </View>
      </View>
    );
  }

  return (
    <Screen>
      <Text style={typography.heading}>Photo scan</Text>
      <Text style={typography.body}>
        Your height anchors the scale; then take a front and a side photo with the 10-second timer.
      </Text>
      <CmField label="Height" value={height} onChange={setHeight} hint="Barefoot, standing straight." />
      <Button
        title={front ? 'Retake front photo' : 'Take front photo'}
        variant={front ? 'secondary' : 'primary'}
        onPress={() => setPose('front')}
      />
      <Button
        title={side ? 'Retake side photo' : 'Take side photo'}
        variant={side ? 'secondary' : 'primary'}
        onPress={() => setPose('side')}
      />
      <ErrorNotice error={error} />
      <Button title="Continue" disabled={!ready} onPress={finish} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  cameraRoot: { flex: 1, backgroundColor: '#000' },
  overlay: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    padding: spacing.lg,
    gap: spacing.md,
    backgroundColor: colors.background,
  },
});
