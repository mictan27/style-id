// Config plugin for the local `ar-capture` module. Autolinking already finds the
// module by directory convention (apps/mobile/modules/*); this plugin only adds
// the native build settings ARKit needs.
const { withInfoPlist } = require('expo/config-plugins');

/** @type {import('expo/config-plugins').ConfigPlugin} */
const withArCapture = (config) =>
  withInfoPlist(config, (mod) => {
    const plist = mod.modResults;
    plist.NSCameraUsageDescription =
      plist.NSCameraUsageDescription ??
      'style.id uses the camera to measure a flat-laid garment and, optionally, to scan your body.';
    const caps = new Set(plist.UIRequiredDeviceCapabilities ?? []);
    caps.add('arkit');
    plist.UIRequiredDeviceCapabilities = Array.from(caps);
    return mod;
  });

module.exports = withArCapture;
