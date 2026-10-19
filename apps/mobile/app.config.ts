import type { ConfigContext, ExpoConfig } from 'expo/config';

const BUNDLE_ID = 'id.style.app';

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: 'style.id',
  slug: 'style-id',
  version: '0.1.0',
  orientation: 'portrait',
  scheme: 'styleid',
  icon: './assets/images/icon.png',
  userInterfaceStyle: 'automatic',
  platforms: ['ios', 'android'],
  ios: {
    bundleIdentifier: BUNDLE_ID,
    supportsTablet: false,
    usesAppleSignIn: true,
    infoPlist: {
      NSCameraUsageDescription:
        'style.id uses the camera to measure a flat-laid garment and, optionally, to scan your body for a better fit estimate.',
      NSPhotoLibraryUsageDescription:
        'style.id can read a photo of a flat-laid garment from your library to measure it.',
      NSPhotoLibraryAddUsageDescription: 'style.id saves garment photos you capture to your library on request.',
      ITSAppUsesNonExemptEncryption: false,
    },
  },
  android: {
    package: BUNDLE_ID,
    adaptiveIcon: {
      backgroundColor: '#F4F1EC',
      foregroundImage: './assets/images/android-icon-foreground.png',
      backgroundImage: './assets/images/android-icon-background.png',
      monochromeImage: './assets/images/android-icon-monochrome.png',
    },
  },
  plugins: [
    'expo-router',
    'expo-apple-authentication',
    'expo-secure-store',
    'expo-dev-client',
    [
      'expo-camera',
      {
        cameraPermission: 'style.id uses the camera to measure garments and, optionally, your body.',
        microphonePermission: false,
        recordAudioAndroid: false,
      },
    ],
    [
      'expo-share-intent',
      {
        // Only URLs and web pages: shoppers share a product page from Safari or a shop app.
        iosActivationRules: {
          NSExtensionActivationSupportsWebURLWithMaxCount: 1,
          NSExtensionActivationSupportsWebPageWithMaxCount: 1,
          NSExtensionActivationSupportsText: true,
        },
        iosShareExtensionName: 'Check fit with style.id',
        iosAppGroupIdentifier: `group.${BUNDLE_ID}`,
        androidIntentFilters: ['text/*'],
      },
    ],
    [
      'expo-splash-screen',
      {
        backgroundColor: '#F4F1EC',
        image: './assets/images/splash-icon.png',
        imageWidth: 120,
      },
    ],
    // Local Expo Modules (modules/*). Autolinking finds them by directory convention;
    // these plugins only add the native build settings each module needs.
    './modules/ar-capture/app.plugin.js',
    './modules/vision-masks/app.plugin.js',
  ],
  experiments: {
    typedRoutes: false,
  },
  extra: {
    eas: {
      // Filled in by `eas init`.
      projectId: process.env.EAS_PROJECT_ID,
    },
  },
});
