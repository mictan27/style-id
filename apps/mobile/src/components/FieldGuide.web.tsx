import { createElement as h, useMemo } from 'react';
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

/** Web build: the same tee drawing as plain SVG (Skia needs native bindings). */
export function FieldGuide({ field, size = 120, showText = true }: FieldGuideProps) {
  const scale = size / 110;
  const path = useMemo(() => svgPolygon(OUTLINE.map(([x, y]) => ({ x: x * scale, y: y * scale }))), [scale]);
  const [a, b] = SPAN[field];
  const pa = { x: a[0] * scale, y: a[1] * scale };
  const pb = { x: b[0] * scale, y: b[1] * scale };

  return (
    <View style={styles.wrap}>
      {h(
        'svg',
        { width: size * (100 / 110), height: size, role: 'img', 'aria-label': `Where to measure: ${FIELD_NAMES[field]}` },
        h('path', { d: path, fill: 'none', stroke: colors.border, strokeWidth: 2, strokeLinejoin: 'round' }),
        h('line', { x1: pa.x, y1: pa.y, x2: pb.x, y2: pb.y, stroke: colors.primary, strokeWidth: 3 }),
        h('circle', { cx: pa.x, cy: pa.y, r: 4, fill: colors.primary }),
        h('circle', { cx: pb.x, cy: pb.y, r: 4, fill: colors.primary }),
      )}
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
