import { StyleSheet, Text, View } from 'react-native';

import { LANDMARK_LABELS, type LandmarkName, type Landmarks, type Point } from '@/capture/geometry';
import { colors, spacing, typography } from '@/theme';

interface LandmarkOverlayProps {
  imageUri: string;
  imageWidth: number;
  imageHeight: number;
  displayWidth: number;
  landmarks: Landmarks;
  polygon?: Point[];
  onChange: (next: Landmarks) => void;
  onActiveChange?: (name: LandmarkName | null) => void;
}

/** Web build: flat-lay capture needs ARKit, so the drag overlay is iPhone-only. */
export function LandmarkOverlay({ displayWidth, landmarks }: LandmarkOverlayProps) {
  return (
    <View style={[styles.wrap, { width: displayWidth }]}>
      <Text style={typography.caption}>
        Landmark editing runs in the iPhone build. {Object.keys(landmarks).length} landmarks.
      </Text>
    </View>
  );
}

export function landmarkLabel(name: LandmarkName): string {
  return LANDMARK_LABELS[name];
}

const styles = StyleSheet.create({
  wrap: { padding: spacing.lg, borderWidth: 1, borderColor: colors.border, borderRadius: 10 },
});
