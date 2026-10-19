import type { StyleProp, ViewStyle } from 'react-native';

export type CaptureMode = 'flatlay' | 'body';

/** Camera intrinsics in pixels of the returned image: [fx, fy, cx, cy]. */
export type Intrinsics = [number, number, number, number];

export interface FlatLayCapture {
  /** file:// URI of a portrait-oriented JPEG. */
  imageUri: string;
  imageWidth: number;
  imageHeight: number;
  /** Centimetres per pixel of `imageUri` at the detected floor plane. */
  cmPerPixel: number;
  intrinsics: Intrinsics;
  /** Distance from the camera to the plane along the optical axis, metres. */
  planeDistanceM: number;
}

export interface BodyScanOptions {
  /** Keyframes to keep across a full 360° turn. Default 40. */
  keyframes?: number;
}

export interface BodyScanResult {
  /** Directory containing kf_XXX.jpg, kf_XXX_depth.png (uint16 mm), kf_XXX_conf.png and manifest.json. */
  directoryPath: string;
  keyframeCount: number;
}

export interface PlaneDetectedEvent {
  distanceM: number;
  cmPerPixel: number;
  /** Plane extent in metres, useful to tell the user to step back. */
  extentM: [number, number];
}

export type TrackingState = 'notAvailable' | 'limited' | 'normal';

export interface FrameEvent {
  trackingState: TrackingState;
  /** Reason when `trackingState` is `limited`. */
  limitedReason?: 'initializing' | 'excessiveMotion' | 'insufficientFeatures' | 'relocalizing';
  hasDepth: boolean;
  /** Camera yaw in degrees, body mode only. */
  yawDeg?: number;
}

export interface KeyframeEvent {
  index: number;
  count: number;
  target: number;
  yawDeg: number;
}

export type ScanCompleteEvent = BodyScanResult;

export interface ErrorEvent {
  code: string;
  message: string;
}

type NativeEvent<T> = (event: { nativeEvent: T }) => void;

export interface ArCaptureViewProps {
  mode: CaptureMode;
  style?: StyleProp<ViewStyle>;
  onPlaneDetected?: NativeEvent<PlaneDetectedEvent>;
  onFrame?: NativeEvent<FrameEvent>;
  onKeyframe?: NativeEvent<KeyframeEvent>;
  onScanComplete?: NativeEvent<ScanCompleteEvent>;
  onError?: NativeEvent<ErrorEvent>;
}
