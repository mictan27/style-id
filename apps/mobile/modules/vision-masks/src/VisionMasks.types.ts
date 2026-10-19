/** A polygon vertex normalised to 0..1 with the origin at the image's top-left. */
export type NormalisedPoint = [number, number];

export interface ForegroundMaskResult {
  /** file:// URI of an 8-bit grayscale PNG the size of the input (255 = foreground). */
  maskUri: string;
  imageWidth: number;
  imageHeight: number;
  /** Largest contour of the mask, simplified to at most 200 points. */
  polygon: NormalisedPoint[];
}

export interface PersonSegmentationResult {
  /** file:// URI of an 8-bit grayscale PNG (255 = person). */
  maskUri: string;
  imageWidth: number;
  imageHeight: number;
}

/** Vision joint name → [x, y, confidence], x/y normalised with a top-left origin. */
export type BodyPosePoints = Record<string, [number, number, number]>;

export interface BodyPoseResult {
  points: BodyPosePoints;
  imageWidth: number;
  imageHeight: number;
}
