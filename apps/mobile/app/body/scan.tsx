import { useRouter } from 'expo-router';
import * as Speech from 'expo-speech';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Platform, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/Button';
import { ErrorNotice } from '@/components/Card';
import { Screen } from '@/components/Screen';
import { useBodyDraft } from '@/store/bodyDraft';
import { colors, spacing, typography } from '@/theme';
import * as ArCapture from '@modules/ar-capture';

type Phase = 'intro' | 'scanning' | 'done';

const PROMPTS = {
  start: 'Stand about two metres from the phone, arms slightly away from your body. Turn slowly on the spot.',
  quarter: 'Keep turning. A quarter of the way.',
  half: 'Half way. Keep the same pace.',
  threeQuarter: 'Nearly there.',
  done: 'Done. You can relax.',
};

function say(text: string) {
  if (Platform.OS === 'ios') Speech.speak(text, { rate: 0.95 });
}

export default function BodyScanScreen() {
  const router = useRouter();
  const setDraft = useBodyDraft((s) => s.setDraft);
  const [phase, setPhase] = useState<Phase>('intro');
  const [progress, setProgress] = useState<ArCapture.KeyframeEvent | null>(null);
  const [tracking, setTracking] = useState<ArCapture.TrackingState>('notAvailable');
  const [error, setError] = useState<unknown>(null);
  const spoken = useRef(new Set<string>());

  useEffect(() => {
    return () => {
      void Speech.stop();
    };
  }, []);

  const start = useCallback(async () => {
    setError(null);
    try {
      await ArCapture.startBodyScan({ keyframes: 40 });
      setPhase('scanning');
      say(PROMPTS.start);
    } catch (e) {
      setError(e);
    }
  }, []);

  const finish = useCallback(
    async (result: ArCapture.BodyScanResult | null) => {
      if (!result || result.keyframeCount < 8) {
        setError(new Error('Not enough keyframes were captured. Try again in better light.'));
        setPhase('intro');
        return;
      }
      say(PROMPTS.done);
      setDraft({
        source: 'lidar',
        measurements: {},
        localScan: { directoryPath: result.directoryPath },
      });
      setPhase('done');
      router.replace('/body/confirm');
    },
    [router, setDraft],
  );

  const stop = useCallback(async () => {
    try {
      const result = await ArCapture.stopScan();
      await finish(result);
    } catch (e) {
      setError(e);
    }
  }, [finish]);

  const onKeyframe = (e: ArCapture.KeyframeEvent) => {
    setProgress(e);
    const fraction = e.count / e.target;
    const milestones: [number, string][] = [
      [0.25, PROMPTS.quarter],
      [0.5, PROMPTS.half],
      [0.75, PROMPTS.threeQuarter],
    ];
    for (const [at, text] of milestones) {
      if (fraction >= at && !spoken.current.has(text)) {
        spoken.current.add(text);
        say(text);
      }
    }
  };

  if (Platform.OS !== 'ios' || !ArCapture.isAvailable() || !ArCapture.isLidarAvailable()) {
    return (
      <Screen>
        <Text style={typography.heading}>Needs an iPhone Pro build</Text>
        <Text style={typography.body}>
          LiDAR scanning uses ARKit scene depth, available on iPhone Pro models in the iOS development build.
        </Text>
        <Button title="Use the photo scan instead" onPress={() => router.replace('/body/photo')} />
      </Screen>
    );
  }

  return (
    <View style={styles.root}>
      <ArCapture.ArCaptureView
        mode="body"
        style={StyleSheet.absoluteFill}
        onFrame={(e) => setTracking(e.nativeEvent.trackingState)}
        onKeyframe={(e) => onKeyframe(e.nativeEvent)}
        onScanComplete={(e) => void finish(e.nativeEvent)}
        onError={(e) => setError(new Error(e.nativeEvent.message))}
      />
      <View style={styles.overlay}>
        {phase === 'intro' ? (
          <>
            <Text style={typography.heading}>LiDAR body scan</Text>
            <Text style={typography.body}>
              Prop the phone up at waist height, step back about two metres, and turn slowly once around. Voice prompts
              guide you; close-fitting clothes give the best numbers.
            </Text>
            <Button title="Start" disabled={tracking !== 'normal'} onPress={start} />
          </>
        ) : (
          <>
            <Text style={typography.heading}>
              {progress ? `${progress.count} / ${progress.target} keyframes` : 'Turn slowly…'}
            </Text>
            <Text style={typography.caption}>{progress ? `${Math.round(progress.yawDeg)}° turned` : ''}</Text>
            <Button title="Finish early" variant="secondary" onPress={stop} />
          </>
        )}
        <ErrorNotice error={error} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#000' },
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
