import { Canvas, Circle, Line, Path, vec } from '@shopify/react-native-skia';
import { useMemo } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { GarmentField } from '@/api/schema';
import { FIELD_GUIDE, FIELD_NAMES } from '@/closet/options';
import { colors, spacing, typography } from '@/theme';

type P = [number, number];

/** Tee silhouette in a 100 x 110 box. */
const TEE: Record<string, P> = {
  shoulderL: [30, 15],
  hpsL: [42, 10],
  collarDip: [50, 17],
  hpsR: [58, 10],
  shoulderR: [70, 15],
  cuffRTop: [92, 38],
  cuffRBottom: [86, 50],
  armpitR: [72, 44],
  waistR: [71, 75],
  hemR: [74, 105],
  hemL: [26, 105],
  waistL: [29, 75],
  armpitL: [28, 44],
  cuffLBottom: [14, 50],
  cuffLTop: [8, 38],
};

const OUTLINE: P[] = [
  TEE.shoulderL!,
  TEE.hpsL!,
  TEE.collarDip!,
  TEE.hpsR!,
  TEE.shoulderR!,
  TEE.cuffRTop!,
  TEE.cuffRBottom!,
  TEE.armpitR!,
  TEE.hemR!,
  TEE.hemL!,
  TEE.armpitL!,
  TEE.cuffLBottom!,
  TEE.cuffLTop!,
];

const SPAN: Record<GarmentField, [P, P]> = {
  chest_width: [[28, 47], [72, 47]],
  waist_width: [TEE.waistL!, TEE.waistR!],
  hem_width: [TEE.hemL!, TEE.hemR!],
  bicep_width: [[24, 50], [19, 36]],
  shoulder_width: [TEE.shoulderL!, TEE.shoulderR!],
  sleeve_length: [TEE.shoulderR!, [89, 44]],
  length: [[50, 10], [50, 105]],
  collar: [TEE.hpsL!, TEE.hpsR!],
};

/** SVG path string for a closed polygon; Skia's Path accepts SVG path data. */
export function svgPolygon(points: readonly { x: number; y: number }[]): string {
  if (points.length === 0) return '';
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(' ') + ' Z';
}

interface FieldGuideProps {
  field: GarmentField;
  size?: number;
  showText?: boolean;
}

/** Line drawing of a tee with the measured span highlighted. */
export function FieldGuide({ field, size = 120, showText = true }: FieldGuideProps) {
  const scale = size / 110;
  const path = useMemo(() => svgPolygon(OUTLINE.map(([x, y]) => ({ x: x * scale, y: y * scale }))), [scale]);
  const [a, b] = SPAN[field];
  const pa = vec(a[0] * scale, a[1] * scale);
  const pb = vec(b[0] * scale, b[1] * scale);

  return (
    <View style={styles.wrap}>
      <Canvas style={{ width: size * (100 / 110), height: size }}>
        <Path path={path} color={colors.border} style="stroke" strokeWidth={2} strokeJoin="round" />
        <Line p1={pa} p2={pb} color={colors.primary} strokeWidth={3} />
        <Circle c={pa} r={4} color={colors.primary} />
        <Circle c={pb} r={4} color={colors.primary} />
      </Canvas>
      {showText ? (
        <View style={styles.text}>
          <Text style={styles.title}>{FIELD_NAMES[field]}</Text>
          <Text style={typography.caption}>{FIELD_GUIDE[field]}</Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flexDirection: 'row', gap: spacing.md, alignItems: 'center' },
  text: { flex: 1, gap: spacing.xs },
  title: { ...typography.body, fontWeight: '600' },
});
