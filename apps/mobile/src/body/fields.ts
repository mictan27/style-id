import type { BodyField } from '@/api/schema';

export const BODY_FIELD_NAMES: Record<BodyField, string> = {
  height: 'Height',
  neck: 'Neck',
  shoulder: 'Shoulder width',
  chest: 'Chest',
  waist: 'Waist',
  hip: 'Hip',
  arm_length: 'Arm length',
  bicep: 'Bicep',
  back_length: 'Back length',
};

export const BODY_FIELD_GUIDE: Record<BodyField, string> = {
  height: 'Barefoot, standing straight.',
  neck: 'Around the base of the neck.',
  shoulder: 'Across the back, shoulder point to shoulder point.',
  chest: 'Around the fullest part, tape level, relaxed breath.',
  waist: 'Around the narrowest point of the torso.',
  hip: 'Around the fullest part of the hips.',
  arm_length: 'Shoulder point to the wrist bone, arm slightly bent.',
  bicep: 'Around the fullest part of the upper arm, relaxed.',
  back_length: 'Base of the neck down the spine to the waist.',
};
