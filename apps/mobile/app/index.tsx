import { Redirect } from 'expo-router';

import { selectIsSignedIn, useAuthStore } from '@/store/auth';

/** Launch route: there is no screen at "/", so send people to the closet or to sign-in. */
export default function Index() {
  const signedIn = useAuthStore(selectIsSignedIn);
  return <Redirect href={signedIn ? '/closet' : '/sign-in'} />;
}
