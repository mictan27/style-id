import type { ConfigContext, ExpoConfig } from 'expo/config';

/**
 * Free-signing builds: `STYLEID_FREE_SIGNING=1 npx expo run:ios --device` on a Mac with a
 * free Apple ID (Xcode "Personal Team"). Personal teams cannot sign Sign in with Apple or
 * App Groups, so those builds leave out the Apple sign-in entitlement and the share
 * extension (which needs an App Group). Everything else, including ARKit and Vision, works.
 * Free builds expire after 7 days; rerun the command to reinstall.
 */
const FREE_SIGNING = process.env.STYLEID_FREE_SIGNING === '1';

/**
 * A bundle id is owned by the first Apple team that registers it, so free builds use
 * their own: set IOS_BUNDLE_ID (e.g. `id.style.app.dev.william`) if Xcode says the id
 * is taken.
 */
const BUNDLE_ID = process.env.IOS_BUNDLE_ID ?? (FREE_SIGNING ? 'id.style.app.dev' : 'id.style.app');

/** Expo project `styleid` (expo.dev). Override with EAS_PROJECT_ID for a fork. */
const EAS_PROJECT_ID = process.env.EAS_PROJECT_ID ?? '4f8c56ad-6f9b-4ca0-ba87-02cc083624fe';

const shareIntentPlugin: [string, Record<string, unknown>] = [
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
];

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: 'style.id',
  slug: 'styleid',
  version: '0.1.0',
  orientation: 'portrait',
  scheme: 'styleid',
  icon: './assets/images/icon.png',
  userInterfaceStyle: 'automatic',
  // web: development preview for layout checks and screenshots (pnpm screenshots); not shipped.
  platforms: ['ios', 'android', 'web'],
  web: { bundler: 'metro', output: 'single' },
  ios: {
    bundleIdentifier: BUNDLE_ID,
    supportsTablet: false,
    usesAppleSignIn: !FREE_SIGNING,
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
    ...(FREE_SIGNING ? [] : ['expo-apple-authentication']),
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
    ...(FREE_SIGNING ? [] : [shareIntentPlugin]),
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
    ...(FREE_SIGNING ? ['./plugins/withFreeSigning.js'] : []),
  ],
  experiments: {
    typedRoutes: false,
  },
  extra: {
    freeSigning: FREE_SIGNING,
    eas: {
      projectId: EAS_PROJECT_ID,
    },
  },
});
