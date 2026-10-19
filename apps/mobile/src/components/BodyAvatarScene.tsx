/** The fit-map scene: grey body, zone tints, optional reference outline. Shared by native and web canvases. */
import { useMemo } from 'react';

import type { Label, Zone } from '@/api/schema';
import { labelColor } from '@/fit/format';

export type ZoneLabels = Partial<Record<Zone, Label | null>>;

export interface BodyAvatarProps {
  zones: ZoneLabels;
  /** Draw the reference garment as a wireframe outline over the body. */
  showReference?: boolean;
  /** Reference garment dimensions in cm (half chest width, length) when known. */
  reference?: { chestWidthCm?: number; lengthCm?: number } | null;
}

const GREY = '#B8B2A8';

/**
 * Placeholder body: a stack of capsules and cylinders standing in for the MHR
 * mesh. Each primitive maps to a fit zone and is tinted by that zone's label.
 * Units are metres; the body is ~1.75 m tall and centred on the origin.
 */
export function Body({ zones, showReference, reference }: BodyAvatarProps) {
  const tint = (zone: Zone) => {
    const label = zones[zone];
    return label ? labelColor(label) : GREY;
  };
  const chestRadius = useMemo(() => {
    const half = reference?.chestWidthCm ?? 52; // flat half-chest in cm → rough radius
    return (half / Math.PI) / 100;
  }, [reference]);
  const refLength = (reference?.lengthCm ?? 70) / 100;

  return (
    <group position={[0, -0.1, 0]}>
      {/* head */}
      <mesh position={[0, 0.78, 0]}>
        <sphereGeometry args={[0.11, 24, 16]} />
        <meshStandardMaterial color={GREY} />
      </mesh>
      {/* neck / collar */}
      <mesh position={[0, 0.63, 0]}>
        <cylinderGeometry args={[0.055, 0.065, 0.1, 20]} />
        <meshStandardMaterial color={tint('collar')} />
      </mesh>
      {/* shoulders */}
      <mesh position={[0, 0.52, 0]} rotation={[0, 0, Math.PI / 2]}>
        <capsuleGeometry args={[0.07, 0.34, 6, 16]} />
        <meshStandardMaterial color={tint('shoulder')} />
      </mesh>
      {/* chest */}
      <mesh position={[0, 0.38, 0]}>
        <cylinderGeometry args={[0.17, 0.165, 0.26, 24]} />
        <meshStandardMaterial color={tint('chest')} />
      </mesh>
      {/* waist */}
      <mesh position={[0, 0.17, 0]}>
        <cylinderGeometry args={[0.165, 0.15, 0.16, 24]} />
        <meshStandardMaterial color={tint('waist')} />
      </mesh>
      {/* hips / hem line */}
      <mesh position={[0, 0.0, 0]}>
        <cylinderGeometry args={[0.15, 0.175, 0.18, 24]} />
        <meshStandardMaterial color={tint('hem')} />
      </mesh>
      {/* upper arms (bicep zone) */}
      {[-1, 1].map((side) => (
        <mesh key={`bicep-${side}`} position={[side * 0.27, 0.36, 0]} rotation={[0, 0, side * 0.08]}>
          <capsuleGeometry args={[0.05, 0.22, 6, 14]} />
          <meshStandardMaterial color={tint('bicep')} />
        </mesh>
      ))}
      {/* forearms (sleeve zone) */}
      {[-1, 1].map((side) => (
        <mesh key={`sleeve-${side}`} position={[side * 0.3, 0.1, 0]} rotation={[0, 0, side * 0.08]}>
          <capsuleGeometry args={[0.042, 0.24, 6, 14]} />
          <meshStandardMaterial color={tint('sleeve')} />
        </mesh>
      ))}
      {/* legs */}
      {[-1, 1].map((side) => (
        <mesh key={`leg-${side}`} position={[side * 0.09, -0.45, 0]}>
          <capsuleGeometry args={[0.07, 0.62, 6, 14]} />
          <meshStandardMaterial color={GREY} />
        </mesh>
      ))}
      {showReference ? (
        <mesh position={[0, 0.52 - refLength / 2, 0]}>
          <cylinderGeometry args={[chestRadius, chestRadius, refLength, 20, 1, true]} />
          <meshBasicMaterial color={tint('length')} wireframe transparent opacity={0.6} />
        </mesh>
      ) : null}
    </group>
  );
}
