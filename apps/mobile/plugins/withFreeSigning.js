// Free Apple IDs (Xcode "Personal Team") cannot sign Sign in with Apple or App Groups.
// Expo auto-applies expo-apple-authentication's plugin whenever the package is
// installed, so leaving it out of `plugins` is not enough: strip the entitlements here.
const { withEntitlementsPlist } = require('expo/config-plugins');

const PAID_ONLY = ['com.apple.developer.applesignin', 'com.apple.security.application-groups'];

/** @type {import('expo/config-plugins').ConfigPlugin} */
const withFreeSigning = (config) =>
  withEntitlementsPlist(config, (mod) => {
    for (const key of PAID_ONLY) delete mod.modResults[key];
    return mod;
  });

module.exports = withFreeSigning;
