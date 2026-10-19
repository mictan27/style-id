/**
 * Pure geometry for the flat-lay capture flow. Everything here is unit-tested
 * and runs on any platform; the native module only supplies pixels and scale.
 */
import type { GarmentField } from '@/api/schema';

export interface Point {
  x: number;
  y: number;
}

/** Camera intrinsics in pixels: [fx, fy, cx, cy]. */
export type Intrinsics = [number, number, number, number];

export const LANDMARK_NAMES = [
  'hps',
  'collar_left',
  'collar_right',
  'shoulder_left',
  'shoulder_right',
  'armpit_left',
  'armpit_right',
  'cuff_left',
  'cuff_right',
  'hem_left',
  'hem_right',
  'hem_center',
  'waist_left',
  'waist_right',
] as const;
export type LandmarkName = (typeof LANDMARK_NAMES)[number];
export type Landmarks = Partial<Record<LandmarkName, Point>>;

export const LANDMARK_LABELS: Record<LandmarkName, string> = {
  hps: 'High point of shoulder',
  collar_left: 'Collar left',
  collar_right: 'Collar right',
  shoulder_left: 'Shoulder left',
  shoulder_right: 'Shoulder right',
  armpit_left: 'Armpit left',
  armpit_right: 'Armpit right',
  cuff_left: 'Cuff left',
  cuff_right: 'Cuff right',
  hem_left: 'Hem left',
  hem_right: 'Hem right',
  hem_center: 'Hem centre',
  waist_left: 'Waist left',
  waist_right: 'Waist right',
};

/** Offset below the armpit at which bicep width is read, in cm. */
export const BICEP_OFFSET_CM = 2.5;

/**
 * Centimetres per image pixel at a plane `planeDistanceM` metres from the camera.
 *
 * A pinhole camera maps a length L at distance d to L * fx / d pixels, so one
 * pixel spans d / fx metres on the plane. `intrinsicsWidthPx` is the image width
 * the intrinsics were computed for; when the image we measure on has another
 * width, fx is scaled accordingly.
 */
export function cmPerPixel(
  intrinsics: Intrinsics,
  planeDistanceM: number,
  imageWidthPx: number,
  intrinsicsWidthPx: number = imageWidthPx,
): number {
  const [fx] = intrinsics;
  if (fx <= 0 || planeDistanceM <= 0 || imageWidthPx <= 0 || intrinsicsWidthPx <= 0) {
    throw new RangeError('cmPerPixel: intrinsics, distance and widths must be positive');
  }
  const fxScaled = fx * (imageWidthPx / intrinsicsWidthPx);
  return (planeDistanceM * 100) / fxScaled;
}

export function distance(p: Point, q: Point): number {
  return Math.hypot(q.x - p.x, q.y - p.y);
}

export function midpoint(p: Point, q: Point): Point {
  return { x: (p.x + q.x) / 2, y: (p.y + q.y) / 2 };
}

/** Perpendicular distance from `p` to the infinite line through `a` and `b`. */
export function distanceToLine(p: Point, a: Point, b: Point): number {
  const len = distance(a, b);
  if (len === 0) return distance(p, a);
  const cross = (b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x);
  return Math.abs(cross) / len;
}

export function scalePolygon(polygon: readonly (readonly [number, number])[], width: number, height: number): Point[] {
  return polygon.map(([x, y]) => ({ x: x * width, y: y * height }));
}

function round1(v: number): number {
  return Math.round(v * 10) / 10;
}

/**
 * Derives flat-lay garment measurements (cm) from landmark pixel positions.
 *
 *  chest_width     armpit L–R
 *  shoulder_width  shoulder L–R
 *  length          HPS to hem midpoint
 *  hem_width       hem L–R
 *  sleeve_length   shoulder to cuff (averaged when both sleeves are present)
 *  bicep_width     width across the sleeve 2.5 cm below the armpit, perpendicular to the sleeve axis
 *  collar          collar L–R
 *  waist_width     waist L–R
 */
export function measurementsFromLandmarks(landmarks: Landmarks, cmPerPx: number): Partial<Record<GarmentField, number>> {
  const out: Partial<Record<GarmentField, number>> = {};
  const cm = (px: number) => round1(px * cmPerPx);
  const L = landmarks;

  if (L.armpit_left && L.armpit_right) out.chest_width = cm(distance(L.armpit_left, L.armpit_right));
  if (L.shoulder_left && L.shoulder_right) out.shoulder_width = cm(distance(L.shoulder_left, L.shoulder_right));
  if (L.hem_left && L.hem_right) out.hem_width = cm(distance(L.hem_left, L.hem_right));
  if (L.collar_left && L.collar_right) out.collar = cm(distance(L.collar_left, L.collar_right));
  if (L.waist_left && L.waist_right) out.waist_width = cm(distance(L.waist_left, L.waist_right));

  const hemMid = L.hem_center ?? (L.hem_left && L.hem_right ? midpoint(L.hem_left, L.hem_right) : undefined);
  if (L.hps && hemMid) out.length = cm(distance(L.hps, hemMid));

  const sleeves: number[] = [];
  if (L.shoulder_left && L.cuff_left) sleeves.push(distance(L.shoulder_left, L.cuff_left));
  if (L.shoulder_right && L.cuff_right) sleeves.push(distance(L.shoulder_right, L.cuff_right));
  if (sleeves.length) out.sleeve_length = cm(sleeves.reduce((a, b) => a + b, 0) / sleeves.length);

  const biceps: number[] = [];
  const bicep = (shoulder?: Point, armpit?: Point, cuff?: Point) => {
    if (!shoulder || !armpit || !cuff) return;
    const axisLen = distance(shoulder, cuff);
    if (axisLen === 0) return;
    const ux = (cuff.x - shoulder.x) / axisLen;
    const uy = (cuff.y - shoulder.y) / axisLen;
    const offsetPx = BICEP_OFFSET_CM / cmPerPx;
    const p = { x: armpit.x + ux * offsetPx, y: armpit.y + uy * offsetPx };
    biceps.push(distanceToLine(p, shoulder, cuff));
  };
  bicep(L.shoulder_left, L.armpit_left, L.cuff_left);
  bicep(L.shoulder_right, L.armpit_right, L.cuff_right);
  if (biceps.length) out.bicep_width = cm(biceps.reduce((a, b) => a + b, 0) / biceps.length);

  return out;
}

function bounds(points: readonly Point[]) {
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const p of points) {
    if (p.x < minX) minX = p.x;
    if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.y > maxY) maxY = p.y;
  }
  return { minX, maxX, minY, maxY, width: maxX - minX, height: maxY - minY };
}

function centroid(points: readonly Point[]): Point {
  const n = points.length;
  return {
    x: points.reduce((s, p) => s + p.x, 0) / n,
    y: points.reduce((s, p) => s + p.y, 0) / n,
  };
}

function extreme(points: readonly Point[], pick: (a: Point, b: Point) => boolean): Point | undefined {
  let best: Point | undefined;
  for (const p of points) if (!best || pick(p, best)) best = p;
  return best;
}

/**
 * Proposes landmarks from a garment silhouette (pixel coordinates, image
 * origin top-left). Heuristics for a top laid flat, sleeves out:
 *
 *  - topmost points (within 1 % of height) form the HPS line: its midpoint is
 *    `hps`, its ends are the collar;
 *  - the top band (8 % of height) spans the shoulders: leftmost/rightmost points;
 *  - armpits are the innermost points of each side between the shoulders and
 *    60 % of the height (the concave corner where sleeve meets body);
 *  - cuffs are the centre of each side's outermost run of points;
 *  - hem corners are the leftmost/rightmost points of the bottom band.
 *
 * Returns an empty object for degenerate input (< 3 points).
 */
export function proposeLandmarks(polygon: readonly Point[]): Landmarks {
  if (polygon.length < 3) return {};
  const b = bounds(polygon);
  if (b.width === 0 || b.height === 0) return {};
  const c = centroid(polygon);
  const out: Landmarks = {};

  // HPS line and collar.
  const hpsBand = polygon.filter((p) => p.y <= b.minY + b.height * 0.01);
  const hpsLeft = extreme(hpsBand, (a, z) => a.x < z.x);
  const hpsRight = extreme(hpsBand, (a, z) => a.x > z.x);
  if (hpsLeft && hpsRight) {
    out.hps = midpoint(hpsLeft, hpsRight);
    if (hpsLeft !== hpsRight) {
      out.collar_left = hpsLeft;
      out.collar_right = hpsRight;
    }
  }

  // Shoulders.
  const topBand = polygon.filter((p) => p.y <= b.minY + b.height * 0.08);
  out.shoulder_left = extreme(topBand, (a, z) => a.x < z.x);
  out.shoulder_right = extreme(topBand, (a, z) => a.x > z.x);
  const shoulderY = Math.max(out.shoulder_left?.y ?? b.minY, out.shoulder_right?.y ?? b.minY);

  // Armpits: innermost point on each side between shoulders and 60 % height.
  const yLo = shoulderY + b.height * 0.05;
  const yHi = b.minY + b.height * 0.6;
  const mid = polygon.filter((p) => p.y > yLo && p.y < yHi);
  const leftSide = mid.filter((p) => p.x < c.x);
  const rightSide = mid.filter((p) => p.x > c.x);
  const tol = b.width * 0.01;
  const armpitLeftX = extreme(leftSide, (a, z) => a.x > z.x)?.x;
  if (armpitLeftX !== undefined) {
    out.armpit_left = extreme(
      leftSide.filter((p) => p.x >= armpitLeftX - tol),
      (a, z) => a.y < z.y,
    );
  }
  const armpitRightX = extreme(rightSide, (a, z) => a.x < z.x)?.x;
  if (armpitRightX !== undefined) {
    out.armpit_right = extreme(
      rightSide.filter((p) => p.x <= armpitRightX + tol),
      (a, z) => a.y < z.y,
    );
  }

  // Cuffs: centre of the outermost run on each side, above the armpit line.
  const cuffTol = b.width * 0.08;
  const armpitY = Math.max(out.armpit_left?.y ?? yHi, out.armpit_right?.y ?? yHi) + b.height * 0.05;
  const leftRun = polygon.filter((p) => p.x <= b.minX + cuffTol && p.y <= armpitY);
  const rightRun = polygon.filter((p) => p.x >= b.maxX - cuffTol && p.y <= armpitY);
  if (leftRun.length) out.cuff_left = centroid(leftRun);
  if (rightRun.length) out.cuff_right = centroid(rightRun);

  // Hem.
  const bottomBand = polygon.filter((p) => p.y >= b.maxY - b.height * 0.05);
  out.hem_left = extreme(bottomBand, (a, z) => a.x < z.x);
  out.hem_right = extreme(bottomBand, (a, z) => a.x > z.x);
  if (out.hem_left && out.hem_right) out.hem_center = midpoint(out.hem_left, out.hem_right);

  for (const key of Object.keys(out) as LandmarkName[]) {
    if (out[key] === undefined) delete out[key];
  }
  return out;
}
