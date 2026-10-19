import type { GarmentField } from '@/api/schema';

/** Shared tee drawing used by the native (Skia) and web (SVG) field guides. */
export type P = [number, number];

/** Tee silhouette in a 100 x 110 box. */
export const TEE: Record<string, P> = {
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

export const OUTLINE: P[] = [
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

export const SPAN: Record<GarmentField, [P, P]> = {
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
