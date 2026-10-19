import { Canvas, Circle, Line, Path, vec } from '@shopify/react-native-skia';
import { useMemo } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { GarmentField } from '@/api/schema';
import { FIELD_GUIDE, FIELD_NAMES } from '@/closet/options';
import { colors, spacing, typography } from '@/theme';

import { OUTLINE, SPAN, svgPolygon } from './fieldGuideGeometry';

export { svgPolygon };

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
