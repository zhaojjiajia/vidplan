import { http } from './index'
import type { AssetType } from '@/types/api'
import type { AssetField, AssetSchema } from '@/data/assetSchemas'

export interface PlanMarkdownImportData {
  idea?: string
  target_platform?: string
  target_audience?: string
  duration_seconds?: number | null
  style?: string
}

export interface AssetMarkdownImportData {
  name?: string
  payload?: Record<string, unknown>
  fixed_traits?: unknown[]
}

export type MarkdownImportAnalyzeResponse<T> =
  | { ok: true; data: T }
  | { ok: false; detail?: string }

interface AnalyzePayload {
  mode: 'plan' | 'asset'
  markdown: string
  asset_type?: AssetType
  asset_title?: string
  fields?: Pick<AssetField, 'key' | 'label' | 'kind'>[]
}

export const markdownImportApi = {
  analyzePlan(markdown: string) {
    return analyze<PlanMarkdownImportData>({
      mode: 'plan',
      markdown,
    })
  },

  analyzeAsset(markdown: string, assetType: AssetType, schema: AssetSchema) {
    return analyze<AssetMarkdownImportData>({
      mode: 'asset',
      markdown,
      asset_type: assetType,
      asset_title: schema.title,
      fields: schema.fields.map((field) => ({
        key: field.key,
        label: field.label,
        kind: field.kind,
      })),
    })
  },
}

function analyze<T>(payload: AnalyzePayload) {
  return http
    .post<MarkdownImportAnalyzeResponse<T>>('/ai-settings/markdown-import/analyze/', payload)
    .then((r) => r.data)
}
