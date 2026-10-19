import * as AppleAuthentication from 'expo-apple-authentication';
import Constants from 'expo-constants';
import { useEffect, useState } from 'react';
import { Platform, StyleSheet, Text, View } from 'react-native';

import { useAppleSignIn } from '@/api/hooks';
import { Button } from '@/components/Button';
import { ErrorNotice } from '@/components/Card';
import { Toggle } from '@/components/Choice';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { useAuthStore } from '@/store/auth';
import { colors, spacing, typography } from '@/theme';

export default function SignInScreen() {
  const [isAdult, setIsAdult] = useState(false);
  const [appleAvailable, setAppleAvailable] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [devHandle, setDevHandle] = useState('');
  const setToken = useAuthStore((s) => s.setToken);
  const setDevUser = useAuthStore((s) => s.setDevUser);
  const appleSignIn = useAppleSignIn();

  // Free-signing builds have no Sign in with Apple entitlement; use the developer sign-in.
  const freeSigning = Constants.expoConfig?.extra?.freeSigning === true;

  useEffect(() => {
    if (Platform.OS !== 'ios' || freeSigning) return;
    AppleAuthentication.isAvailableAsync().then(setAppleAvailable).catch(() => setAppleAvailable(false));
  }, [freeSigning]);

  const signInWithApple = async () => {
    setError(null);
    try {
      const credential = await AppleAuthentication.signInAsync({
        requestedScopes: [AppleAuthentication.AppleAuthenticationScope.EMAIL],
      });
      if (!credential.identityToken) throw new Error('Apple did not return an identity token.');
      const token = await appleSignIn.mutateAsync({
        identity_token: credential.identityToken,
        dob_verified_18: isAdult,
      });
      await setToken(token.access_token);
    } catch (e) {
      if ((e as { code?: string }).code === 'ERR_REQUEST_CANCELED') return;
      setError(e);
    }
  };

  return (
    <Screen style={styles.root}>
      <View style={styles.hero}>
        <Text style={typography.title}>style.id</Text>
        <Text style={typography.body}>
          Will this exact top fit you, and where will it be tight or loose? Measure one tee you love and every
          product you check is compared against it.
        </Text>
      </View>

      <Toggle
        label="I am 18 or older"
        hint="Body scanning is adults-only. You can still measure garments and check fit without it."
        value={isAdult}
        onChange={setIsAdult}
      />

      {freeSigning ? (
        <Text style={typography.caption}>
          This is a free-signing build without Sign in with Apple. Use the developer sign-in below.
        </Text>
      ) : appleAvailable ? (
        <AppleAuthentication.AppleAuthenticationButton
          buttonType={AppleAuthentication.AppleAuthenticationButtonType.SIGN_IN}
          buttonStyle={AppleAuthentication.AppleAuthenticationButtonStyle.BLACK}
          cornerRadius={10}
          style={styles.appleButton}
          onPress={signInWithApple}
        />
      ) : (
        <Button title="Sign in with Apple" onPress={signInWithApple} disabled={Platform.OS !== 'ios'} />
      )}
      {Platform.OS !== 'ios' ? (
        <Text style={typography.caption}>Sign in with Apple is only available on iOS in v1.</Text>
      ) : null}
      <ErrorNotice error={error} />

      {__DEV__ ? (
        <View style={styles.dev}>
          <Text style={[typography.caption, { fontWeight: '600' }]}>Developer sign-in (X-Dev-User header)</Text>
          <TextField
            placeholder="handle, e.g. william"
            autoCapitalize="none"
            autoCorrect={false}
            value={devHandle}
            onChangeText={setDevHandle}
          />
          <Button
            title="Continue as dev user"
            variant="secondary"
            disabled={devHandle.trim().length === 0}
            onPress={() => setDevUser(devHandle)}
          />
        </View>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  root: { justifyContent: 'center', gap: spacing.lg, flexGrow: 1 },
  hero: { gap: spacing.md, marginBottom: spacing.lg },
  appleButton: { height: 48, width: '100%' },
  dev: {
    marginTop: spacing.xxl,
    gap: spacing.sm,
    padding: spacing.md,
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: colors.border,
    borderRadius: 10,
  },
});
