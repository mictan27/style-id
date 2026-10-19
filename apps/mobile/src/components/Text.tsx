import { Text as RNText, type TextProps } from 'react-native';

import { typography } from '@/theme';

type Variant = keyof typeof typography;

export function Text({ variant = 'body', style, ...rest }: TextProps & { variant?: Variant }) {
  return <RNText style={[typography[variant], style]} {...rest} />;
}
