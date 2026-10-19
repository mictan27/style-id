import { useRouter } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import { Platform, StyleSheet, Text, useWindowDimensions, View } from 'react-native';

import { useCreateGarment, useSubmitLandmarkCorrection } from '@/api/hooks';
import type { GarmentField, GarmentMeasurements, Label, LandmarkPoint } from '@/api/schema';
import {
  measurementsFromLandmarks,
  proposeLandmarks,
  scalePolygon,
  type LandmarkName,
  type Landmarks,
  type Point,
} from '@/capture/geometry';
import { Button } from '@/components/Button';
import { Card, ErrorNotice, Row } from '@/components/Card';
import { Choice, Toggle } from '@/components/Choice';
import { LandmarkOverlay, landmarkLabel } from '@/components/LandmarkOverlay';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { FABRIC_OPTIONS, FABRIC_TO_STRETCH, FIELD_NAMES, FIT_TAG_OPTIONS, type Fabric } from '@/closet/options';
import * as ArCapture from '@modules/ar-capture';
import * as VisionMasks from '@modules/vision-masks';
import { colors, spacing, typography } from '@/theme';

type Step = 'intro' | 'capture' | 'landmarks' | 'save';

interface Captured extends ArCapture.FlatLayCapture {
  polygon: Point[];
}

export default function CaptureScreen() {
  const [step, setStep] = useState<Step>('intro');
  const [captured, setCaptured] = useState<Captured | null>(null);
  const [proposed, setProposed] = useState<Landmarks>({});
  const [landmarks, setLandmarks] = useState<Landmarks>({});
  const [error, setError] = useState<unknown>(null);

  if (Platform.OS !== 'ios' || !ArCapture.isAvailable()) {
    return <NeedsIphone />;
  }

  if (step === 'intro') {
    return (
      <Screen>
        <Text style={typography.heading}>Lay it flat</Text>
        <Text style={typography.body}>1. Put the top on a plain floor, front up, sleeves straight out.</Text>
        <Text style={typography.body}>2. Smooth out wrinkles; the hem and cuffs should be visible.</Text>
        <Text style={typography.body}>3. Hold the phone level about a metre above it and wait for the scale to lock.</Text>
        <Button title="Open camera" onPress={() => setStep('capture')} />
      </Screen>
    );
  }

  if (step === 'capture') {
    return (
      <CaptureStep
        onCaptured={(c, initial) => {
          setCaptured(c);
          setProposed(initial);
          setLandmarks(initial);
          setStep('landmarks');
        }}
        onError={setError}
        error={error}
      />
    );
  }

  if (step === 'landmarks' && captured) {
    return (
      <LandmarksStep
        captured={captured}
        landmarks={landmarks}
        onChange={setLandmarks}
        onBack={() => setStep('capture')}
        onNext={() => setStep('save')}
      />
    );
  }

  if (step === 'save' && captured) {
    return <SaveStep captured={captured} proposed={proposed} landmarks={landmarks} onBack={() => setStep('landmarks')} />;
  }
  return null;
}

function NeedsIphone() {
  const router = useRouter();
  return (
    <Screen>
      <Text style={typography.heading}>Needs an iPhone build</Text>
      <Text style={typography.body}>
        Camera measuring uses ARKit (for metric scale) and Apple Vision (to cut the garment out of the photo). It runs
        in the iOS development build, not in Expo Go, the simulator or on Android.
      </Text>
      <Button title="Type measurements instead" onPress={() => router.replace('/closet/new')} />
    </Screen>
  );
}

function CaptureStep({
  onCaptured,
  onError,
  error,
}: {
  onCaptured: (c: Captured, proposed: Landmarks) => void;
  onError: (e: unknown) => void;
  error: unknown;
}) {
  const [plane, setPlane] = useState<ArCapture.PlaneDetectedEvent | null>(null);
  const [tracking, setTracking] = useState<ArCapture.TrackingState>('notAvailable');
  const [busy, setBusy] = useState(false);

  const capture = useCallback(async () => {
    setBusy(true);
    onError(null);
    try {
      const shot = await ArCapture.captureFlatLay();
      let polygon: Point[] = [];
      if (VisionMasks.supportsForegroundMask()) {
        const mask = await VisionMasks.foregroundMask(shot.imageUri);
        polygon = scalePolygon(mask.polygon, shot.imageWidth, shot.imageHeight);
      }
      const proposed = polygon.length ? proposeLandmarks(polygon) : fallbackLandmarks(shot.imageWidth, shot.imageHeight);
      onCaptured({ ...shot, polygon }, proposed);
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  }, [onCaptured, onError]);

  const ready = plane !== null && tracking === 'normal';
  return (
    <View style={styles.cameraRoot}>
      <ArCapture.ArCaptureView
        mode="flatlay"
        style={StyleSheet.absoluteFill}
        onPlaneDetected={(e) => setPlane(e.nativeEvent)}
        onFrame={(e) => setTracking(e.nativeEvent.trackingState)}
        onError={(e) => onError(new Error(e.nativeEvent.message))}
      />
      <View style={styles.cameraOverlay}>
        <Text style={styles.cameraText}>
          {ready
            ? `Scale locked: ${plane.cmPerPixel.toFixed(3)} cm/px at ${plane.distanceM.toFixed(2)} m`
            : tracking === 'normal'
              ? 'Looking for the floor… move the phone slowly.'
              : 'Hold still while tracking starts.'}
        </Text>
        <ErrorNotice error={error} />
        <Button title="Capture" disabled={!ready} loading={busy} onPress={capture} />
      </View>
    </View>
  );
}

/** When the mask fails we still let the user place landmarks by hand, starting from a centred template. */
function fallbackLandmarks(w: number, h: number): Landmarks {
  const t: Record<LandmarkName, [number, number]> = {
    hps: [0.5, 0.12],
    collar_left: [0.42, 0.12],
    collar_right: [0.58, 0.12],
    shoulder_left: [0.3, 0.15],
    shoulder_right: [0.7, 0.15],
    armpit_left: [0.28, 0.38],
    armpit_right: [0.72, 0.38],
    cuff_left: [0.12, 0.36],
    cuff_right: [0.88, 0.36],
    hem_left: [0.27, 0.88],
    hem_right: [0.73, 0.88],
    hem_center: [0.5, 0.88],
    waist_left: [0.3, 0.65],
    waist_right: [0.7, 0.65],
  };
  const out: Landmarks = {};
  for (const [name, [x, y]] of Object.entries(t) as [LandmarkName, [number, number]][]) {
    out[name] = { x: x * w, y: y * h };
  }
  return out;
}

function LandmarksStep({
  captured,
  landmarks,
  onChange,
  onBack,
  onNext,
}: {
  captured: Captured;
  landmarks: Landmarks;
  onChange: (l: Landmarks) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const { width } = useWindowDimensions();
  const [active, setActive] = useState<LandmarkName | null>(null);
  const derived = useMemo(() => measurementsFromLandmarks(landmarks, captured.cmPerPixel), [landmarks, captured.cmPerPixel]);
  const displayWidth = width - spacing.lg * 2;

  return (
    <Screen>
      <LandmarkOverlay
        imageUri={captured.imageUri}
        imageWidth={captured.imageWidth}
        imageHeight={captured.imageHeight}
        displayWidth={displayWidth}
        landmarks={landmarks}
        polygon={captured.polygon}
        onChange={onChange}
        onActiveChange={setActive}
      />
      <Text style={typography.caption}>{active ? `Moving: ${landmarkLabel(active)}` : 'Live readout'}</Text>
      <Card>
        {(Object.keys(derived) as GarmentField[]).map((field) => (
          <Row key={field} label={FIELD_NAMES[field]} value={`${derived[field]} cm`} />
        ))}
      </Card>
      <View style={styles.actions}>
        <Button title="Retake" variant="secondary" onPress={onBack} style={{ flex: 1 }} />
        <Button title="Looks right" onPress={onNext} style={{ flex: 1 }} disabled={derived.chest_width === undefined} />
      </View>
    </Screen>
  );
}

function SaveStep({
  captured,
  proposed,
  landmarks,
  onBack,
}: {
  captured: Captured;
  proposed: Landmarks;
  landmarks: Landmarks;
  onBack: () => void;
}) {
  const router = useRouter();
  const create = useCreateGarment();
  const correct = useSubmitLandmarkCorrection();
  const [name, setName] = useState('');
  const [fabric, setFabric] = useState<Fabric>('cotton_tee');
  const [fitTag, setFitTag] = useState<Label>('regular');
  const [sizeLabel, setSizeLabel] = useState('');
  const [isReference, setIsReference] = useState(true);
  const derived = useMemo(() => measurementsFromLandmarks(landmarks, captured.cmPerPixel), [landmarks, captured.cmPerPixel]);

  const save = async () => {
    const measurements: GarmentMeasurements = {};
    for (const [field, value] of Object.entries(derived) as [GarmentField, number][]) {
      measurements[field] = { value_cm: value, source: 'flatlay', confidence: 'high' };
    }
    const garment = await create.mutateAsync({
      name: name.trim() || 'My tee',
      kind: 'tee',
      cut: 'set_in',
      stretch: FABRIC_TO_STRETCH[fabric],
      fit_tag: fitTag,
      size_label: sizeLabel.trim() || null,
      is_reference: isReference,
      length_from_center_back: false,
      sleeve_from_center_back: false,
      measurements,
    });
    await correct.mutateAsync({
      garmentId: garment.id,
      correction: {
        // TODO: upload the JPEG to blob storage and send its key; until then the local URI identifies the image.
        image_blob_key: captured.imageUri,
        proposed: toLandmarkPoints(proposed),
        corrected: toLandmarkPoints(landmarks),
        scale_cm_per_px: captured.cmPerPixel,
      },
    });
    router.replace({ pathname: '/closet/[id]', params: { id: garment.id } });
  };

  return (
    <Screen>
      <TextField label="Name" placeholder="Grey tee" value={name} onChangeText={setName} />
      <TextField label="Size label" placeholder="M" autoCapitalize="characters" value={sizeLabel} onChangeText={setSizeLabel} />
      <Choice label="Fabric" options={FABRIC_OPTIONS} value={fabric} onChange={setFabric} />
      <Choice label="How does it fit you?" options={FIT_TAG_OPTIONS} value={fitTag} onChange={setFitTag} />
      <Toggle label="Use as my reference" value={isReference} onChange={setIsReference} />
      <ErrorNotice error={create.error ?? correct.error} />
      <View style={styles.actions}>
        <Button title="Back" variant="secondary" onPress={onBack} style={{ flex: 1 }} />
        <Button title="Save" loading={create.isPending || correct.isPending} onPress={save} style={{ flex: 1 }} />
      </View>
    </Screen>
  );
}

/** Landmarks in image pixels, keyed by name, as the API stores them. */
function toLandmarkPoints(landmarks: Landmarks): Record<string, LandmarkPoint> {
  const out: Record<string, LandmarkPoint> = {};
  for (const [name, pt] of Object.entries(landmarks) as [LandmarkName, Point][]) {
    out[name] = { x: Math.round(pt.x), y: Math.round(pt.y) };
  }
  return out;
}

const styles = StyleSheet.create({
  cameraRoot: { flex: 1, backgroundColor: '#000' },
  cameraOverlay: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    padding: spacing.lg,
    gap: spacing.md,
    backgroundColor: 'rgba(247,245,241,0.92)',
  },
  cameraText: { ...typography.body, color: colors.text },
  actions: { flexDirection: 'row', gap: spacing.md },
});
