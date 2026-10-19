import { Canvas } from '@react-three/fiber';
import { StyleSheet, View } from 'react-native';

import { colors } from '@/theme';

import { Body, type BodyAvatarProps } from './BodyAvatarScene';

export type { ZoneLabels } from './BodyAvatarScene';

export function BodyAvatar(props: BodyAvatarProps) {
  return (
    <View style={styles.wrap}>
      <Canvas camera={{ position: [0, 0.2, 2.6], fov: 40 }} style={styles.canvas}>
        <ambientLight intensity={0.9} />
        <directionalLight position={[2, 3, 3]} intensity={1.2} />
        <Body {...props} />
      </Canvas>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: colors.surfaceMuted, borderRadius: 16, overflow: 'hidden' },
  canvas: { flex: 1 },
});
