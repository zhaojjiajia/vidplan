import { http } from './index'
import type { AssetBase, AssetType, Paginated } from '@/types/api'

export type AssetPayload = Pick<AssetBase, 'name' | 'payload' | 'fixed_traits'>

export const assetsApi = {
  list: (type: AssetType, params?: { search?: string; ordering?: string }) =>
    http.get<Paginated<AssetBase>>(`/assets/${type}/`, { params }).then((r) => r.data),

  create: (type: AssetType, payload: AssetPayload) =>
    http.post<AssetBase>(`/assets/${type}/`, payload).then((r) => r.data),

  patch: (type: AssetType, id: string, payload: Partial<AssetPayload>) =>
    http.patch<AssetBase>(`/assets/${type}/${id}/`, payload).then((r) => r.data),

  remove: (type: AssetType, id: string) =>
    http.delete(`/assets/${type}/${id}/`).then((r) => r.data),
}
