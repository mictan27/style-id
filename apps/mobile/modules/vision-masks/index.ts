import { requireOptionalNativeModule } from 'expo-modules-core';
import { Platform } from 'react-native';

import type { BodyPoseResult, ForegroundMaskResult, PersonSegmentationResult } from './src/VisionMasks.types';

export * from './src/VisionMasks.types';

interface NativeVisionMasksModule {
  supportsForegroundMask(): boolean;
  foregroundMask(imageUri: string): Promise<ForegroundMaskResult>;
  personSegmentation(imageUri: string): Promise<PersonSegmentationResult>;
  bodyPose(imageUri: string): Promise<BodyPoseResult>;
}

const NativeModule: NativeVisionMasksModule | null =
  Platform.OS === 'ios' ? requireOptionalNativeModule<NativeVisionMasksModule>('VisionMasks') : null;

export class VisionMasksUnavailableError extends Error {
  constructor() {
    super('vision-masks needs an iOS development build (Apple Vision is not available here).');
    this.name = 'VisionMasksUnavailableError';
  }
}

/** True when the native module is linked (iOS dev/production build). */
export function isAvailable(): boolean {
  return NativeModule !== null;
}

/** Foreground instance masks need iOS 17 (VNGenerateForegroundInstanceMaskRequest). */
export function supportsForegroundMask(): boolean {
  return NativeModule?.supportsForegroundMask() ?? false;
}

/** Cuts the salient foreground (the garment on the floor) out of a photo and traces its outline. */
export function foregroundMask(imageUri: string): Promise<ForegroundMaskResult> {
  return NativeModule ? NativeModule.foregroundMask(imageUri) : Promise.reject(new VisionMasksUnavailableError());
}

export function personSegmentation(imageUri: string): Promise<PersonSegmentationResult> {
  return NativeModule ? NativeModule.personSegmentation(imageUri) : Promise.reject(new VisionMasksUnavailableError());
}

export function bodyPose(imageUri: string): Promise<BodyPoseResult> {
  return NativeModule ? NativeModule.bodyPose(imageUri) : Promise.reject(new VisionMasksUnavailableError());
}
