import { useMutation, useQuery, useQueryClient, type UseQueryOptions } from '@tanstack/react-query';

import { api, unwrap } from './client';
import type {
  AppleAuthRequest,
  BodyConfirm,
  BodyRecord,
  BodyRecordCreate,
  FitReport,
  FitReportCreate,
  Garment,
  GarmentCreate,
  GarmentUpdate,
  LandmarkCorrectionCreate,
  Me,
  OutcomeCreate,
  PreferencesModel,
  ProductCheckRequest,
} from './schema';

export const queryKeys = {
  me: ['me'] as const,
  garments: ['closet', 'garments'] as const,
  garment: (id: string) => ['closet', 'garments', id] as const,
  bodyCurrent: ['body', 'current'] as const,
  product: (id: string) => ['products', id] as const,
  fitReports: ['fit', 'reports'] as const,
  fitReport: (id: string) => ['fit', 'reports', id] as const,
};

type QueryOpts<T> = Omit<UseQueryOptions<T, Error, T, readonly unknown[]>, 'queryKey' | 'queryFn'>;

// ---- me ---------------------------------------------------------------------

export function useMe(options?: QueryOpts<Me>) {
  return useQuery({
    queryKey: queryKeys.me,
    queryFn: async (): Promise<Me> => unwrap(await api.GET('/v1/me')),
    ...options,
  });
}

export function useUpdatePreferences() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PreferencesModel): Promise<PreferencesModel> =>
      unwrap(await api.PATCH('/v1/me/preferences', { body })),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.me }),
  });
}

// ---- closet -----------------------------------------------------------------

export function useGarments(options?: QueryOpts<Garment[]>) {
  return useQuery({
    queryKey: queryKeys.garments,
    queryFn: async (): Promise<Garment[]> => unwrap(await api.GET('/v1/closet/garments')),
    ...options,
  });
}

export function useGarment(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.garment(id ?? ''),
    queryFn: async (): Promise<Garment> =>
      unwrap(await api.GET('/v1/closet/garments/{garment_id}', { params: { path: { garment_id: id! } } })),
    enabled: Boolean(id),
  });
}

export function useCreateGarment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: GarmentCreate): Promise<Garment> => unwrap(await api.POST('/v1/closet/garments', { body })),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.garments }),
  });
}

/** PUT: send the full garment (see `toGarmentUpdate`). */
export function useUpdateGarment(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: GarmentUpdate): Promise<Garment> =>
      unwrap(await api.PUT('/v1/closet/garments/{garment_id}', { params: { path: { garment_id: id } }, body })),
    onSuccess: (garment) => {
      qc.setQueryData(queryKeys.garment(id), garment);
      void qc.invalidateQueries({ queryKey: queryKeys.garments });
    },
  });
}

export function useDeleteGarment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      unwrap(await api.DELETE('/v1/closet/garments/{garment_id}', { params: { path: { garment_id: id } } }));
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.garments }),
  });
}

export function useSubmitLandmarkCorrection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ garmentId, correction }: { garmentId: string; correction: LandmarkCorrectionCreate }) =>
      unwrap(
        await api.POST('/v1/closet/garments/{garment_id}/landmark-corrections', {
          params: { path: { garment_id: garmentId } },
          body: correction,
        }),
      ),
    onSuccess: (correction) => {
      void qc.invalidateQueries({ queryKey: queryKeys.garment(correction.garment_id) });
      void qc.invalidateQueries({ queryKey: queryKeys.garments });
    },
  });
}

// ---- body -------------------------------------------------------------------

export function useCurrentBodyRecord(options?: QueryOpts<BodyRecord | null>) {
  return useQuery({
    queryKey: queryKeys.bodyCurrent,
    queryFn: async (): Promise<BodyRecord | null> => {
      const result = await api.GET('/v1/body/records/current');
      if (result.response.status === 404) return null;
      return unwrap(result);
    },
    ...options,
  });
}

export function useCreateBodyRecord() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: BodyRecordCreate): Promise<BodyRecord> => unwrap(await api.POST('/v1/body/records', { body })),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.bodyCurrent }),
  });
}

export function useConfirmBodyRecord() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: string; body: BodyConfirm }): Promise<BodyRecord> =>
      unwrap(await api.POST('/v1/body/records/{record_id}/confirm', { params: { path: { record_id: id } }, body })),
    onSuccess: (record) => qc.setQueryData(queryKeys.bodyCurrent, record),
  });
}

// ---- products & fit ---------------------------------------------------------

export function useCheckProduct() {
  return useMutation({
    mutationFn: async (body: ProductCheckRequest) => unwrap(await api.POST('/v1/products/check', { body })),
  });
}

export function useProduct(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.product(id ?? ''),
    queryFn: async () => unwrap(await api.GET('/v1/products/{product_id}', { params: { path: { product_id: id! } } })),
    enabled: Boolean(id),
  });
}

export function useFitReports(options?: QueryOpts<FitReport[]>) {
  return useQuery({
    queryKey: queryKeys.fitReports,
    queryFn: async (): Promise<FitReport[]> => unwrap(await api.GET('/v1/fit/reports')),
    ...options,
  });
}

export function useFitReport(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.fitReport(id ?? ''),
    queryFn: async (): Promise<FitReport> =>
      unwrap(await api.GET('/v1/fit/reports/{report_id}', { params: { path: { report_id: id! } } })),
    enabled: Boolean(id),
  });
}

export function useCreateFitReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: FitReportCreate): Promise<FitReport> => unwrap(await api.POST('/v1/fit/reports', { body })),
    onSuccess: (report) => {
      qc.setQueryData(queryKeys.fitReport(report.id), report);
      void qc.invalidateQueries({ queryKey: queryKeys.fitReports });
    },
  });
}

/** Share-sheet / paste flow: check the product, then build a report. */
export function useCheckAndReport() {
  const check = useCheckProduct();
  const report = useCreateFitReport();
  return useMutation({
    mutationFn: async (body: ProductCheckRequest): Promise<FitReport> => {
      const product = await check.mutateAsync(body);
      return report.mutateAsync({ product_id: product.id });
    },
  });
}

// ---- outcomes & auth --------------------------------------------------------

export function useCreateOutcome() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: OutcomeCreate) => unwrap(await api.POST('/v1/outcomes', { body })),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.fitReports }),
  });
}

export function useAppleSignIn() {
  return useMutation({
    mutationFn: async (body: AppleAuthRequest) => unwrap(await api.POST('/v1/auth/apple', { body })),
  });
}
