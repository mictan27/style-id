import type { Confidence, Label, Zone, ZoneResultModel } from '@/api/schema';
import { colors } from '@/theme';

const ZONE_NAMES: Record<Zone, string> = {
  chest: 'Chest',
  shoulder: 'Shoulders',
  waist: 'Waist',
  hem: 'Hem',
  bicep: 'Upper arm',
  collar: 'Collar',
  length: 'Length',
  sleeve: 'Sleeve',
};

const ZONE_PHRASE: Record<Zone, string> = {
  chest: 'at the chest',
  shoulder: 'across the shoulders',
  waist: 'at the waist',
  hem: 'at the hem',
  bicep: 'around the upper arm',
  collar: 'at the collar',
  length: 'in length',
  sleeve: 'in the sleeve',
};

export const LABEL_NAMES: Record<Label, string> = {
  tight: 'Tight',
  fitted: 'Fitted',
  regular: 'Regular',
  relaxed: 'Relaxed',
};

export function zoneDisplayName(zone: Zone): string {
  return ZONE_NAMES[zone];
}

/** Formats a cm value: whole numbers stay whole, otherwise one decimal. Always signed when asked. */
export function formatCm(value: number, options: { signed?: boolean; decimals?: number } = {}): string {
  const { signed = false, decimals } = options;
  const rounded = roundTo(value, decimals ?? (Math.abs(value) < 10 ? 1 : 0));
  const magnitude = Number.isInteger(rounded) ? String(Math.abs(rounded)) : Math.abs(rounded).toFixed(1);
  if (rounded === 0) return `0 cm`;
  const sign = rounded < 0 ? '−' : signed ? '+' : '';
  return `${sign}${magnitude} cm`;
}

function roundTo(value: number, decimals: number): number {
  const factor = 10 ** decimals;
  const r = Math.round(value * factor) / factor;
  return r === 0 ? 0 : r; // normalise -0
}

/**
 * Explains a zone result in one sentence.
 *  - with a reference garment: "4 cm more room at the chest than your grey tee"
 *  - without: "4 cm ease at the chest"
 *  - position zones (length/sleeve): the engine's position text.
 */
export function formatEase(zone: ZoneResultModel, referenceName?: string | null): string {
  if (zone.position) {
    return zone.position.text;
  }
  const where = ZONE_PHRASE[zone.zone];
  const delta = zone.delta_vs_ref_cm;
  if (referenceName && delta !== null && delta !== undefined) {
    const amount = roundTo(Math.abs(delta), Math.abs(delta) < 10 ? 1 : 0);
    if (amount === 0) return `Same as your ${referenceName} ${where}`;
    const cm = formatCm(amount);
    return delta > 0
      ? `${cm} more room ${where} than your ${referenceName}`
      : `${cm} less room ${where} than your ${referenceName}`;
  }
  const ease = zone.ease_cm;
  if (ease !== null && ease !== undefined) {
    const cm = formatCm(Math.abs(ease));
    if (roundTo(ease, 1) === 0) return `No ease ${where}`;
    return ease < 0 ? `${cm} negative ease ${where}` : `${cm} ease ${where}`;
  }
  return zone.label ? `${LABEL_NAMES[zone.label]} ${where}` : `No data ${where}`;
}

/** Short comparison chip, e.g. "+4 cm vs your grey tee" or "4 cm ease". */
export function formatEaseShort(zone: ZoneResultModel, referenceName?: string | null): string {
  if (zone.position) return formatCm(zone.position.offset_cm, { signed: true });
  if (referenceName && zone.delta_vs_ref_cm !== null && zone.delta_vs_ref_cm !== undefined) {
    return `${formatCm(zone.delta_vs_ref_cm, { signed: true })} vs your ${referenceName}`;
  }
  if (zone.ease_cm !== null && zone.ease_cm !== undefined) return `${formatCm(zone.ease_cm)} ease`;
  return '—';
}

export function labelColor(label: Label | null | undefined): string {
  return label ? colors.label[label] : colors.textMuted;
}

export function labelSoftColor(label: Label | null | undefined): string {
  return label ? colors.labelSoft[label] : colors.surfaceMuted;
}

export interface ConfidenceBadge {
  text: string;
  color: string;
  hint: string;
}

export function confidenceBadge(confidence: Confidence): ConfidenceBadge {
  switch (confidence) {
    case 'high':
      return { text: 'High confidence', color: colors.confidence.high, hint: 'Measured garment and chart data.' };
    case 'medium':
      return { text: 'Medium confidence', color: colors.confidence.medium, hint: 'Some values are estimated.' };
    case 'low':
      return { text: 'Low confidence', color: colors.confidence.low, hint: 'Mostly estimated. Measure a tee to improve.' };
  }
}

/** "what would change" lines between pick and runner-up. */
export function formatDiff(zone: Zone, diffCm: number): string {
  if (roundTo(diffCm, 1) === 0) return `${zoneDisplayName(zone)}: no change`;
  return `${zoneDisplayName(zone)}: ${formatCm(diffCm, { signed: true })}`;
}
