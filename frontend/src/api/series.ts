import { http } from './index'
import type { AITask, Paginated, SeriesPlan, TaskAware, VideoPlan } from '@/types/api'

export type SeriesExportFormat = 'md' | 'docx'
export interface AITaskRequestOptions {
  async?: boolean
}

export type SeriesPayload = Omit<
  SeriesPlan,
  'id' | 'user' | 'episode_count' | 'episodes' | 'created_at' | 'updated_at'
>

export interface SeriesGenerateInput {
  direction: string
  idea: string
  target_platform?: string
  target_audience?: string
  update_frequency?: string
  episode_duration_seconds?: number
  planned_episodes?: number
  style?: string
  auto_create_assets?: boolean
}

export interface EpisodeGenerateInput {
  topic: string
  episode_goal?: string
  extra_requirements?: string
}

export interface ConsistencyIssue {
  level: 'warning' | 'error' | 'info' | string
  asset_type: string | null
  asset_id: string | null
  field: string | null
  plan_id: string | null
  message: string
  suggestion: string
}

export interface ConsistencyReport {
  score: number
  issues: ConsistencyIssue[]
  task_id?: string
}

export type GenerateSeriesResponse = TaskAware<SeriesPlan> | AITask
export type GenerateEpisodeResponse = TaskAware<VideoPlan> | AITask
export type CheckConsistencyResponse = ConsistencyReport | AITask

export const seriesApi = {
  list: () => http.get<Paginated<SeriesPlan>>('/series/').then((r) => r.data),

  get: (id: string) => http.get<SeriesPlan>(`/series/${id}/`).then((r) => r.data),

  create: (payload: SeriesPayload) =>
    http.post<SeriesPlan>('/series/', payload).then((r) => r.data),

  patch: (id: string, payload: Partial<SeriesPayload>) =>
    http.patch<SeriesPlan>(`/series/${id}/`, payload).then((r) => r.data),

  remove: (id: string) => http.delete(`/series/${id}/`).then((r) => r.data),

  exportSeries: async (id: string, format: SeriesExportFormat, fallbackTitle = 'series'): Promise<void> => {
    const resp = await http.get(`/series/${id}/export/`, {
      params: { format },
      responseType: 'blob',
    })
    const filename = parseFilename(resp.headers['content-disposition']) || `${fallbackTitle}.${format}`
    triggerDownload(resp.data as Blob, filename)
  },

  generate: (input: SeriesGenerateInput, options: AITaskRequestOptions = {}) =>
    http.post<GenerateSeriesResponse>('/series/generate/', input, aiTaskRequestConfig(options)).then((r) => r.data),

  generateEpisode: (id: string, input: EpisodeGenerateInput, options: AITaskRequestOptions = {}) =>
    http.post<GenerateEpisodeResponse>(`/series/${id}/episodes/`, input, aiTaskRequestConfig(options)).then((r) => r.data),

  checkConsistency: (
    id: string,
    payload: { plan_id?: string; scope?: 'all' | 'single' } = {},
    options: AITaskRequestOptions = {},
  ) =>
    http.post<CheckConsistencyResponse>(
      `/series/${id}/check-consistency/`,
      payload,
      aiTaskRequestConfig(options),
    ).then((r) => r.data),
}

function aiTaskRequestConfig(options: AITaskRequestOptions) {
  const mode = import.meta.env.VITE_AI_TASK_MODE
  const wantsAsync = options.async || mode === 'async'
  return wantsAsync ? { params: { async: '1' } } : undefined
}

function parseFilename(disposition?: string): string | null {
  if (!disposition) return null
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(disposition)
  if (utf8) {
    try { return decodeURIComponent(utf8[1]) } catch { /* fallthrough */ }
  }
  const plain = /filename="?([^";]+)"?/i.exec(disposition)
  return plain ? plain[1] : null
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
