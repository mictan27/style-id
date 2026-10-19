import { Canvas, Circle, Image, Line, Path, useImage, vec } from '@shopify/react-native-skia';
import { useCallback, useEffect, useMemo, useRef } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { GestureDetector, usePanGesture } from 'react-native-gesture-handler';

import { LANDMARK_LABELS, type LandmarkName, type Landmarks, type Point } from '@/capture/geometry';
import { colors, spacing, typography } from '@/theme';

import { svgPolygon } from './FieldGuide';

/** Landmark pairs drawn as measurement lines. */
const LINES: [LandmarkName, LandmarkName][] = [
  ['armpit_left', 'armpit_right'],
  ['shoulder_left', 'shoulder_right'],
  ['hem_left', 'hem_right'],
  ['collar_left', 'collar_right'],
  ['hps', 'hem_center'],
  ['shoulder_left', 'cuff_left'],
  ['shoulder_right', 'cuff_right'],
];

const GRAB_RADIUS_PT = 28;

interface LandmarkOverlayProps {
  imageUri: string;
  imageWidth: number;
  imageHeight: number;
  /** Display width in points; height follows the image aspect ratio. */
  displayWidth: number;
  landmarks: Landmarks;
  /** Optional silhouette polygon in image pixels. */
  polygon?: Point[];
  onChange: (next: Landmarks) => void;
  onActiveChange?: (name: LandmarkName | null) => void;
}

/**
 * Photo + draggable landmarks on a Skia canvas. One pan gesture over the whole
 * canvas: the landmark nearest the touch (within GRAB_RADIUS_PT) follows the finger.
 */
export function LandmarkOverlay({
  imageUri,
  imageWidth,
  imageHeight,
  displayWidth,
  landmarks,
  polygon,
  onChange,
  onActiveChange,
}: LandmarkOverlayProps) {
  const scale = displayWidth / imageWidth;
  const displayHeight = imageHeight * scale;
  const image = useImage(imageUri);
  const active = useRef<LandmarkName | null>(null);
  const latest = useRef(landmarks);
  useEffect(() => {
    latest.current = landmarks;
  }, [landmarks]);

  const polygonPath = useMemo(() => {
    if (!polygon || polygon.length < 3) return null;
    return svgPolygon(polygon.map((pt) => ({ x: pt.x * scale, y: pt.y * scale })));
  }, [polygon, scale]);

  const nearest = useCallback(
    (x: number, y: number): LandmarkName | null => {
      let best: LandmarkName | null = null;
      let bestD = GRAB_RADIUS_PT;
      for (const [name, pt] of Object.entries(latest.current) as [LandmarkName, Point][]) {
        const d = Math.hypot(pt.x * scale - x, pt.y * scale - y);
        if (d < bestD) {
          bestD = d;
          best = name;
        }
      }
      return best;
    },
    [scale],
  );

  const moveActive = useCallback(
    (x: number, y: number) => {
      const name = active.current;
      if (!name) return;
      const clamped = {
        x: Math.min(imageWidth, Math.max(0, x / scale)),
        y: Math.min(imageHeight, Math.max(0, y / scale)),
      };
      onChange({ ...latest.current, [name]: clamped });
    },
    [imageHeight, imageWidth, onChange, scale],
  );

  const pan = usePanGesture({
    runOnJS: true,
    minDistance: 0,
    onBegin: (e) => {
      active.current = nearest(e.x, e.y);
      onActiveChange?.(active.current);
    },
    onUpdate: (e) => moveActive(e.x, e.y),
    onFinalize: () => {
      active.current = null;
      onActiveChange?.(null);
    },
  });

  return (
    <View style={styles.wrap}>
      <GestureDetector gesture={pan}>
        <Canvas style={{ width: displayWidth, height: displayHeight }}>
          {image ? <Image image={image} x={0} y={0} width={displayWidth} height={displayHeight} fit="fill" /> : null}
          {polygonPath ? <Path path={polygonPath} color="rgba(31,78,95,0.6)" style="stroke" strokeWidth={2} /> : null}
          {LINES.map(([a, b]) => {
            const pa = landmarks[a];
            const pb = landmarks[b];
            if (!pa || !pb) return null;
            return (
              <Line
                key={`${a}-${b}`}
                p1={vec(pa.x * scale, pa.y * scale)}
                p2={vec(pb.x * scale, pb.y * scale)}
                color={colors.primary}
                strokeWidth={2}
              />
            );
          })}
          {(Object.entries(landmarks) as [LandmarkName, Point][]).map(([name, pt]) => (
            <Circle key={name} cx={pt.x * scale} cy={pt.y * scale} r={9} color="rgba(255,255,255,0.9)">
              <Circle cx={pt.x * scale} cy={pt.y * scale} r={6} color={colors.primary} />
            </Circle>
          ))}
        </Canvas>
      </GestureDetector>
      <Text style={styles.hint}>Drag a dot to correct it. {Object.keys(landmarks).length} landmarks.</Text>
    </View>
  );
}

export function landmarkLabel(name: LandmarkName): string {
  return LANDMARK_LABELS[name];
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.sm },
  hint: typography.caption,
});
