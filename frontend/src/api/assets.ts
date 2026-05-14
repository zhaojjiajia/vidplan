import { http } from './index'
import type {
  AssetBase,
  AssetImage,
  AssetType,
  CustomAsset,
  CustomAssetKind,
  Paginated,
} from '@/types/api'

export type AssetPayload = Pick<AssetBase, 'name' | 'payload' | 'fixed_traits'> & {
  images?: AssetImage[]
}

export const assetsApi = {
  list: (type: AssetType, params?: { search?: string; ordering?: string }) =>
    http.get<Paginated<AssetBase>>(`/assets/${type}/`, { params }).then((r) => r.data),

  get: (type: AssetType, id: string) =>
    http.get<AssetBase>(`/assets/${type}/${id}/`).then((r) => r.data),

  create: (type: AssetType, payload: AssetPayload) =>
    http.post<AssetBase>(`/assets/${type}/`, payload).then((r) => r.data),

  patch: (type: AssetType, id: string, payload: Partial<AssetPayload>) =>
    http.patch<AssetBase>(`/assets/${type}/${id}/`, payload).then((r) => r.data),

  remove: (type: AssetType, id: string) =>
    http.delete(`/assets/${type}/${id}/`).then((r) => r.data),

  /**
   * Upload one image. Backend writes the file under MEDIA_ROOT and returns
   * the descriptor the caller should append to its asset's `images` array.
   */
  uploadImage: (file: File): Promise<AssetImage> => {
    const form = new FormData()
    form.append('file', file)
    return http
      .post<AssetImage>('/assets/upload-image/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  /** Generate one image via the user's configured AI provider (DALL-E 3 etc.). */
  generateImage: (input: { prompt: string; size?: '1024x1024' | '1792x1024' | '1024x1792' }) =>
    http
      .post<AssetImage>('/assets/generate-image/', input)
      .then((r) => r.data),
}

// ---- Custom asset kinds (user-defined categories) ----------------------

export type AssetKindPayload = Pick<
  CustomAssetKind,
  'name' | 'label' | 'icon' | 'description' | 'schema' | 'image_labels'
>

export const assetKindsApi = {
  list: () =>
    http.get<Paginated<CustomAssetKind>>('/asset-kinds/').then((r) => r.data),

  create: (payload: AssetKindPayload) =>
    http.post<CustomAssetKind>('/asset-kinds/', payload).then((r) => r.data),

  patch: (id: string, payload: Partial<AssetKindPayload>) =>
    http.patch<CustomAssetKind>(`/asset-kinds/${id}/`, payload).then((r) => r.data),

  remove: (id: string) =>
    http.delete(`/asset-kinds/${id}/`).then((r) => r.data),
}

// ---- Custom asset instances --------------------------------------------

export const customAssetsApi = {
  list: (params?: { kind?: string; search?: string }) =>
    http.get<Paginated<CustomAsset>>('/custom-assets/', { params }).then((r) => r.data),

  get: (id: string) =>
    http.get<CustomAsset>(`/custom-assets/${id}/`).then((r) => r.data),

  create: (payload: { kind: string } & AssetPayload) =>
    http.post<CustomAsset>('/custom-assets/', payload).then((r) => r.data),

  patch: (id: string, payload: Partial<{ kind: string } & AssetPayload>) =>
    http.patch<CustomAsset>(`/custom-assets/${id}/`, payload).then((r) => r.data),

  remove: (id: string) =>
    http.delete(`/custom-assets/${id}/`).then((r) => r.data),
}
