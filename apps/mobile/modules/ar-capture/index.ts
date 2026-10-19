import { requireNativeViewManager, requireOptionalNativeModule } from 'expo-modules-core';
import { createElement, type ComponentType } from 'react';
import { Platform, View } from 'react-native';

import type {
  ArCaptureViewProps,
  BodyScanOptions,
  BodyScanResult,
  FlatLayCapture,
} from './src/ArCapture.types';

export * from './src/ArCapture.types';

interface NativeArCaptureModule {
  isLidarAvailable(): boolean;
  captureFlatLay(): Promise<FlatLayCapture>;
  startBodyScan(options?: BodyScanOptions): Promise<void>;
  stopScan(): Promise<BodyScanResult | null>;
}

const NativeModule: NativeArCaptureModule | null =
  Platform.OS === 'ios' ? requireOptionalNativeModule<NativeArCaptureModule>('ArCapture') : null;

export class ArCaptureUnavailableError extends Error {
  constructor() {
    super('ar-capture needs an iOS development build (ARKit is not available here).');
    this.name = 'ArCaptureUnavailableError';
  }
}

/** True when the native module is linked (iOS dev/production build). */
export function isAvailable(): boolean {
  return NativeModule !== null;
}

/** True on devices with a LiDAR scanner (ARKit `sceneDepth` frame semantics). */
export function isLidarAvailable(): boolean {
  return NativeModule?.isLidarAvailable() ?? false;
}

/** Grabs the current AR frame once a floor plane is tracked. Requires a mounted `ArCaptureView` in `flatlay` mode. */
export function captureFlatLay(): Promise<FlatLayCapture> {
  return NativeModule ? NativeModule.captureFlatLay() : Promise.reject(new ArCaptureUnavailableError());
}

/** Starts collecting keyframes. Requires a mounted `ArCaptureView` in `body` mode. */
export function startBodyScan(options?: BodyScanOptions): Promise<void> {
  return NativeModule ? NativeModule.startBodyScan(options) : Promise.reject(new ArCaptureUnavailableError());
}

/** Stops the scan, writes manifest.json and returns the keyframe directory (or null if nothing was recorded). */
export function stopScan(): Promise<BodyScanResult | null> {
  return NativeModule ? NativeModule.stopScan() : Promise.reject(new ArCaptureUnavailableError());
}

const NativeView: ComponentType<ArCaptureViewProps> | null = NativeModule
  ? requireNativeViewManager<ArCaptureViewProps>('ArCapture')
  : null;

/** ARSession-backed camera preview. Renders an empty view where ARKit is unavailable. */
export function ArCaptureView(props: ArCaptureViewProps) {
  if (!NativeView) return createElement(View, { style: props.style });
  return createElement(NativeView, props);
}
