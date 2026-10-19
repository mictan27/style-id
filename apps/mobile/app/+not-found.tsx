import { Redirect } from 'expo-router';

/**
 * Unknown links, and protected screens while signed out (expo-router treats a guarded
 * screen as missing), go back to the launch route, which picks closet or sign-in.
 */
export default function NotFound() {
  return <Redirect href="/" />;
}
