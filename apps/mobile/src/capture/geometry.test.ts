import {
  cmPerPixel,
  distance,
  distanceToLine,
  measurementsFromLandmarks,
  midpoint,
  proposeLandmarks,
  scalePolygon,
  type Landmarks,
  type Point,
} from './geometry';

/** Synthetic tee laid flat in a 1000 x 1200 px image, sleeves out, clockwise. */
const TEE: Point[] = [
  { x: 300, y: 100 }, // shoulder left
  { x: 420, y: 80 }, // HPS left
  { x: 460, y: 130 },
  { x: 500, y: 145 }, // neckline dip
  { x: 540, y: 130 },
  { x: 580, y: 80 }, // HPS right
  { x: 700, y: 100 }, // shoulder right
  { x: 900, y: 330 }, // cuff right top
  { x: 860, y: 420 }, // cuff right bottom
  { x: 720, y: 380 }, // armpit right
  { x: 730, y: 1100 }, // hem right
  { x: 270, y: 1100 }, // hem left
  { x: 280, y: 380 }, // armpit left
  { x: 140, y: 420 }, // cuff left bottom
  { x: 100, y: 330 }, // cuff left top
];

describe('cmPerPixel', () => {
  it('is distance / fx in cm', () => {
    expect(cmPerPixel([1000, 1000, 960, 540], 1, 1920)).toBeCloseTo(0.1);
  });
  it('rescales fx when the measured image is smaller than the intrinsics frame', () => {
    expect(cmPerPixel([1000, 1000, 960, 540], 1, 960, 1920)).toBeCloseTo(0.2);
  });
  it('rejects non-positive input', () => {
    expect(() => cmPerPixel([0, 1, 1, 1], 1, 100)).toThrow(RangeError);
    expect(() => cmPerPixel([1000, 1000, 1, 1], -1, 100)).toThrow(RangeError);
  });
});

describe('distance helpers', () => {
  it('computes euclidean distance and midpoints', () => {
    expect(distance({ x: 0, y: 0 }, { x: 3, y: 4 })).toBe(5);
    expect(midpoint({ x: 0, y: 0 }, { x: 4, y: 2 })).toEqual({ x: 2, y: 1 });
  });
  it('computes perpendicular distance to a line', () => {
    expect(distanceToLine({ x: 0, y: 5 }, { x: -10, y: 0 }, { x: 10, y: 0 })).toBe(5);
    expect(distanceToLine({ x: 3, y: 4 }, { x: 0, y: 0 }, { x: 0, y: 0 })).toBe(5);
  });
  it('scales a normalised polygon to pixels', () => {
    expect(scalePolygon([[0.5, 0.25]], 1000, 1200)).toEqual([{ x: 500, y: 300 }]);
  });
});

describe('proposeLandmarks', () => {
  const lm = proposeLandmarks(TEE);

  it('finds the shoulders as the extremes of the top band', () => {
    expect(lm.shoulder_left).toEqual({ x: 300, y: 100 });
    expect(lm.shoulder_right).toEqual({ x: 700, y: 100 });
  });
  it('places the HPS at the middle of the topmost points and the collar at its ends', () => {
    expect(lm.hps).toEqual({ x: 500, y: 80 });
    expect(lm.collar_left).toEqual({ x: 420, y: 80 });
    expect(lm.collar_right).toEqual({ x: 580, y: 80 });
  });
  it('finds the armpits as the innermost side points below the shoulders', () => {
    expect(lm.armpit_left).toEqual({ x: 280, y: 380 });
    expect(lm.armpit_right).toEqual({ x: 720, y: 380 });
  });
  it('finds the hem corners and centre', () => {
    expect(lm.hem_left).toEqual({ x: 270, y: 1100 });
    expect(lm.hem_right).toEqual({ x: 730, y: 1100 });
    expect(lm.hem_center).toEqual({ x: 500, y: 1100 });
  });
  it('centres the cuffs on the outer sleeve edge', () => {
    expect(lm.cuff_left).toEqual({ x: 120, y: 375 });
    expect(lm.cuff_right).toEqual({ x: 880, y: 375 });
  });
  it('returns nothing for degenerate input', () => {
    expect(proposeLandmarks([])).toEqual({});
    expect(proposeLandmarks([{ x: 1, y: 1 }, { x: 1, y: 2 }, { x: 1, y: 3 }])).toEqual({});
  });
  it('is invariant to point order', () => {
    const shuffled = [...TEE].reverse();
    expect(proposeLandmarks(shuffled)).toEqual(lm);
  });
});

describe('measurementsFromLandmarks', () => {
  const cmPerPx = 0.1;
  const lm = proposeLandmarks(TEE);

  it('derives widths from the proposed landmarks', () => {
    const m = measurementsFromLandmarks(lm, cmPerPx);
    expect(m.chest_width).toBe(44);
    expect(m.shoulder_width).toBe(40);
    expect(m.hem_width).toBe(46);
    expect(m.collar).toBe(16);
  });
  it('measures length from HPS to the hem midpoint', () => {
    expect(measurementsFromLandmarks(lm, cmPerPx).length).toBe(102);
  });
  it('measures sleeve length from shoulder to cuff', () => {
    const expected = Math.round(Math.hypot(300 - 120, 375 - 100) * cmPerPx * 10) / 10;
    expect(measurementsFromLandmarks(lm, cmPerPx).sleeve_length).toBe(expected);
  });
  it('measures bicep width across the sleeve 2.5 cm below the armpit', () => {
    // Horizontal sleeve: shoulder (0,0) -> cuff (300,0); armpit at (60,120).
    const horizontal: Landmarks = {
      shoulder_left: { x: 0, y: 0 },
      cuff_left: { x: 300, y: 0 },
      armpit_left: { x: 60, y: 120 },
    };
    expect(measurementsFromLandmarks(horizontal, cmPerPx).bicep_width).toBe(12);
  });
  it('omits fields whose landmarks are missing', () => {
    const m = measurementsFromLandmarks({ hem_left: { x: 0, y: 0 }, hem_right: { x: 100, y: 0 } }, cmPerPx);
    expect(m).toEqual({ hem_width: 10 });
  });
  it('averages both sleeves when present', () => {
    const m = measurementsFromLandmarks(
      {
        shoulder_left: { x: 0, y: 0 },
        cuff_left: { x: 0, y: 100 },
        shoulder_right: { x: 0, y: 0 },
        cuff_right: { x: 0, y: 300 },
      },
      cmPerPx,
    );
    expect(m.sleeve_length).toBe(20);
  });
});
