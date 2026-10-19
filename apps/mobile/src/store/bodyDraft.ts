import { create } from 'zustand';

import type { BodyField, BodyMeasurements, BodyRecordCreate, Source } from '@/api/schema';

/** In-memory draft handed from scan/photo/manual screens to body/confirm. */
export interface BodyDraft {
  source: Source;
  measurements: BodyMeasurements;
  /** Blob key of an uploaded fitted mesh, once the scan upload exists. */
  mesh_blob_key?: string | null;
  /** "I'm an M in brand X": not in the API yet, kept for the size-anchor flow. */
  size_anchor?: { brand: string; size_label: string } | null;
  /** Local scan artefacts awaiting upload (LiDAR directory or photo URIs). */
  localScan?: { directoryPath?: string; photos?: string[]; heightCm?: number } | null;
}

interface BodyDraftState {
  draft: BodyDraft | null;
  setDraft: (draft: BodyDraft) => void;
  updateMeasurement: (field: BodyField, value: number | null) => void;
  clear: () => void;
}

export const useBodyDraft = create<BodyDraftState>((set) => ({
  draft: null,
  setDraft: (draft) => set({ draft }),
  updateMeasurement: (field, value) =>
    set((state) => {
      if (!state.draft) return state;
      const measurements = { ...state.draft.measurements };
      if (value === null) delete measurements[field];
      else measurements[field] = { value_cm: value, source: 'manual', confidence: 'high' };
      return { draft: { ...state.draft, measurements } };
    }),
  clear: () => set({ draft: null }),
}));

/**
 * The API takes a BodyModel plus an optional `mesh_blob_key`. Scan artefacts
 * (`localScan`) and the size anchor are kept on the draft for the upload step,
 * which is not wired yet.
 */
export function toBodyRecordCreate(draft: BodyDraft): BodyRecordCreate {
  return {
    source: draft.source,
    measurements: draft.measurements,
    landmarks: null,
    mesh_blob_key: draft.mesh_blob_key ?? null,
  };
}
