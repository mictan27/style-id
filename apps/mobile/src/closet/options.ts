import type { Cut, GarmentField, GarmentKind, Label, StretchClass } from '@/api/schema';
import type { ChoiceOption } from '@/components/Choice';

export const KIND_OPTIONS: readonly ChoiceOption<GarmentKind>[] = [
  { value: 'tee', label: 'T-shirt' },
  { value: 'shirt', label: 'Shirt' },
  { value: 'sweater', label: 'Sweater' },
  { value: 'hoodie', label: 'Hoodie' },
];

export const KIND_NAMES: Record<GarmentKind, string> = {
  tee: 'T-shirt',
  shirt: 'Shirt',
  sweater: 'Sweater',
  hoodie: 'Hoodie',
};

/** Fabric picker: everyday names mapped onto the engine's stretch classes. */
export type Fabric =
  | 'cotton_tee'
  | 'stretch_tee'
  | 'poplin_shirt'
  | 'stretch_shirt'
  | 'knit_sweater'
  | 'fleece_hoodie';

export const FABRIC_OPTIONS: readonly ChoiceOption<Fabric>[] = [
  { value: 'cotton_tee', label: 'Cotton tee', hint: 'Plain cotton jersey: gives a little, recovers.' },
  { value: 'stretch_tee', label: 'Stretchy tee', hint: 'Jersey with elastane: noticeably stretchy.' },
  { value: 'poplin_shirt', label: 'Woven shirt', hint: 'Poplin, oxford, linen: no stretch.' },
  { value: 'stretch_shirt', label: 'Stretch shirt', hint: 'Woven with a few percent elastane.' },
  { value: 'knit_sweater', label: 'Knit sweater', hint: 'Knits behave like cotton jersey.' },
  { value: 'fleece_hoodie', label: 'Fleece hoodie', hint: 'Brushed fleece: a little give.' },
];

export const FABRIC_TO_STRETCH: Record<Fabric, StretchClass> = {
  cotton_tee: 'cotton_jersey',
  stretch_tee: 'jersey_elastane',
  poplin_shirt: 'rigid_woven',
  stretch_shirt: 'woven_elastane',
  knit_sweater: 'cotton_jersey',
  fleece_hoodie: 'cotton_jersey',
};

export const STRETCH_NAMES: Record<StretchClass, string> = {
  rigid_woven: 'Rigid woven',
  woven_elastane: 'Woven with elastane',
  cotton_jersey: 'Cotton jersey',
  jersey_elastane: 'Jersey with elastane',
};

export const CUT_OPTIONS: readonly ChoiceOption<Cut>[] = [
  { value: 'set_in', label: 'Set-in sleeve', hint: 'Seam sits on the shoulder point.' },
  { value: 'raglan', label: 'Raglan', hint: 'Diagonal seam from underarm to collar.' },
  { value: 'drop_shoulder', label: 'Drop shoulder', hint: 'Seam sits down the upper arm.' },
];

export const FIT_TAG_OPTIONS: readonly ChoiceOption<Label>[] = [
  { value: 'fitted', label: 'Fitted', hint: 'Close to the body.' },
  { value: 'regular', label: 'Regular', hint: 'Easy, not loose.' },
  { value: 'relaxed', label: 'Relaxed', hint: 'Roomy, drapes away from the body.' },
];

export const FIELD_NAMES: Record<GarmentField, string> = {
  chest_width: 'Chest width',
  waist_width: 'Waist width',
  hem_width: 'Hem width',
  bicep_width: 'Bicep width',
  shoulder_width: 'Shoulder width',
  sleeve_length: 'Sleeve length',
  length: 'Length',
  collar: 'Collar',
};

export const FIELD_GUIDE: Record<GarmentField, string> = {
  chest_width: 'Flat, armpit seam to armpit seam, 2.5 cm below the armhole.',
  waist_width: 'Flat, side to side at the narrowest point between chest and hem.',
  hem_width: 'Flat, side to side along the bottom edge.',
  bicep_width: 'Flat across the sleeve, 2.5 cm below the armpit seam.',
  shoulder_width: 'Shoulder seam to shoulder seam across the back.',
  sleeve_length: 'Shoulder seam down the outside of the sleeve to the cuff edge.',
  length: 'High point of shoulder (next to the collar) straight down to the hem.',
  collar: 'Collar opening edge to edge, flat.',
};

export const FIELDS_FOR_KIND: Record<GarmentKind, GarmentField[]> = {
  tee: ['chest_width', 'shoulder_width', 'length', 'sleeve_length', 'hem_width', 'bicep_width', 'collar'],
  shirt: ['chest_width', 'shoulder_width', 'length', 'sleeve_length', 'hem_width', 'waist_width', 'bicep_width', 'collar'],
  sweater: ['chest_width', 'shoulder_width', 'length', 'sleeve_length', 'hem_width', 'bicep_width'],
  hoodie: ['chest_width', 'shoulder_width', 'length', 'sleeve_length', 'hem_width', 'bicep_width'],
};
