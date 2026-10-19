/**
 * Domain types for the app.
 *
 * Enum constant arrays stay hand-written (they drive pickers and iteration).
 * Every model and API envelope type is an alias of the generated OpenAPI type in
 * ./types.gen.ts (`pnpm gen:api`), so this file is the only import site to touch
 * when the API changes.
 */
import type { components, paths } from './types.gen';

type Schemas = components['schemas'];

// ---- Enums (constant arrays for UI; types checked against the generated enums) --

export const ZONES = ['chest', 'shoulder', 'waist', 'hem', 'bicep', 'collar', 'length', 'sleeve'] as const satisfies readonly Schemas['Zone'][];
export type Zone = Schemas['Zone'];

export const LABELS = ['tight', 'fitted', 'regular', 'relaxed'] as const satisfies readonly Schemas['Label'][];
export type Label = Schemas['Label'];

export const GARMENT_FIELDS = [
  'chest_width',
  'waist_width',
  'hem_width',
  'bicep_width',
  'shoulder_width',
  'sleeve_length',
  'length',
  'collar',
] as const satisfies readonly Schemas['GarmentField'][];
export type GarmentField = Schemas['GarmentField'];

export const BODY_FIELDS = [
  'height',
  'neck',
  'shoulder',
  'chest',
  'waist',
  'hip',
  'arm_length',
  'bicep',
  'back_length',
] as const satisfies readonly Schemas['BodyField'][];
export type BodyField = Schemas['BodyField'];

export const STRETCH_CLASSES = ['rigid_woven', 'woven_elastane', 'cotton_jersey', 'jersey_elastane'] as const satisfies readonly Schemas['StretchClass'][];
export type StretchClass = Schemas['StretchClass'];

export const CUTS = ['set_in', 'raglan', 'drop_shoulder'] as const satisfies readonly Schemas['Cut'][];
export type Cut = Schemas['Cut'];

export const GARMENT_KINDS = ['tee', 'shirt', 'sweater', 'hoodie'] as const satisfies readonly Schemas['GarmentKind'][];
export type GarmentKind = Schemas['GarmentKind'];

export const SOURCES = ['flatlay', 'chart', 'brand_ease_estimate', 'manual', 'lidar', 'photo', 'size_anchor'] as const satisfies readonly Schemas['Source'][];
export type Source = Schemas['Source'];

export const CONFIDENCES = ['high', 'medium', 'low'] as const satisfies readonly Schemas['Confidence'][];
export type Confidence = Schemas['Confidence'];

export type Basis = Schemas['Basis'];
export type Direction = Schemas['Direction'];

// ---- Shared models ---------------------------------------------------------

export type MeasurementModel = Schemas['MeasurementModel'];
export type LandmarksModel = Schemas['LandmarksModel'];
export type PositionModel = Schemas['PositionModel'];
export type ZoneResultModel = Schemas['ZoneResultModel'];
export type SizeResultModel = Schemas['SizeResultModel'];
export type FitReportModel = Schemas['FitReportModel'];
export type PreferencesModel = Schemas['PreferencesModel'];
export type LandmarkPoint = Schemas['LandmarkPoint'];

/** Measurement maps are keyed by field name in the API (string index); these narrow them for the UI. */
export type GarmentMeasurements = Partial<Record<GarmentField, MeasurementModel>>;
export type BodyMeasurements = Partial<Record<BodyField, MeasurementModel>>;

// ---- API envelopes (aliases of the generated schemas) ----------------------

export type Me = Schemas['MeOut'];
export type MePatch = Schemas['MePatch'];
export type AuthToken = Schemas['TokenResponse'];
export type AppleAuthRequest = Schemas['AppleSignInRequest'];

export type Garment = Schemas['ClosetGarmentOut'];
export type GarmentCreate = Schemas['ClosetGarmentIn'];
/** PUT replaces the whole garment; there is no PATCH. */
export type GarmentUpdate = Schemas['ClosetGarmentIn'];
export type LandmarkCorrection = Schemas['LandmarkCorrectionOut'];
export type LandmarkCorrectionCreate = Schemas['LandmarkCorrectionIn'];

export type BodyRecord = Schemas['BodyRecordOut'];
export type BodyRecordCreate = Schemas['BodyRecordIn'];
export type BodyConfirm = Schemas['BodyConfirmIn'];

export type Brand = Schemas['BrandOut'];
export type SizeChart = Schemas['SizeChartOut'];
export type SizeChartStatus = Schemas['SizeChartStatus'];
export type Product = Schemas['ProductOut'];
export type ProductCheckRequest = Schemas['ProductCheckIn'];

export type FitReport = Schemas['FitReportOut'];
export type FitReportCreate = Schemas['FitReportIn'];

export type Outcome = Schemas['OutcomeOut'];
export type OutcomeCreate = Schemas['OutcomeIn'];

export type ValidationError = Schemas['HTTPValidationError'];

/** Convenience: the JSON body of a successful response for a path + method. */
export type ResponseOf<
  P extends keyof paths,
  M extends keyof paths[P],
  S extends keyof NonNullable<paths[P][M]>['responses' & keyof NonNullable<paths[P][M]>] = 200 & keyof NonNullable<paths[P][M]>['responses' & keyof NonNullable<paths[P][M]>],
> = NonNullable<paths[P][M]>['responses' & keyof NonNullable<paths[P][M]>][S] extends { content: { 'application/json': infer R } } ? R : never;

/** Strips the server-side fields so a ClosetGarmentOut can be sent back as a ClosetGarmentIn (PUT). */
export function toGarmentUpdate(garment: Garment, patch: Partial<GarmentUpdate> = {}): GarmentUpdate {
  const { id: _id, created_at: _c, updated_at: _u, ...rest } = garment;
  return { ...rest, ...patch };
}
