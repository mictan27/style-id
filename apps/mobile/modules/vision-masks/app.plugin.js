// Config plugin for the local `vision-masks` module. Vision has no entitlements or
// usage strings of its own; the plugin exists so the module is listed explicitly in
// app.config.ts and can grow build settings later (e.g. a minimum iOS version bump).
const { withInfoPlist } = require('expo/config-plugins');

/** @type {import('expo/config-plugins').ConfigPlugin} */
const withVisionMasks = (config) =>
  withInfoPlist(config, (mod) => {
    mod.modResults.NSPhotoLibraryUsageDescription =
      mod.modResults.NSPhotoLibraryUsageDescription ??
      'style.id can read a photo of a flat-laid garment from your library to measure it.';
    return mod;
  });

module.exports = withVisionMasks;
