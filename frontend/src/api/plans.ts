import { http } from './index'
import type { AICritique, AITask, Paginated, TaskAware, VideoPlan } from '@/types/api'

export interface GenerateInput {
  direction?: string
  category: 'real' | 'ai_generated'
  is_ai_generated_video: boolean
  idea: string
  target_platform?: string
  target_audience?: string
  duration_seconds?: number
  style?: string
}

export interface CreationOutlineInput {
  plan_type: 'single' | 'series'
  direction?: string
  idea: string
  target_platform?: string
  target_audience?: string
  duration_seconds?: number
  style?: string
  previous_outline?: string
  feedback?: string
}

export interface CreationOutlineItem {
  title: string
  note: string
}

export interface CreationOutline {
  title: string
  summary: string
  plan_type: 'single' | 'series'
  direction: string
  direction_label: string
  audience: string
  platform: string
  style: string
  duration_hint: string
  outline: CreationOutlineItem[]
  key_points: string[]
}

export type OptimizeScope = 'full' | 'title' | 'hook' | 'storyboard' | 'editing' | 'ai_prompt'
export type PlanExportFormat = 'md' | 'pdf' | 'docx'
export type GeneratePlanResponse = TaskAware<VideoPlan> | AITask
export type OptimizePlanResponse = TaskAware<VideoPlan> | AITask
export type PlanCreatePayload = Pick<
  VideoPlan,
  'title' | 'direction' | 'category' | 'is_ai_generated_video'
> & Partial<Omit<VideoPlan, 'id' | 'user' | 'created_at' | 'updated_at'>>

export interface AITaskRequestOptions {
  async?: boolean
}

export interface RewriteInput {
  path: string
  hint?: string
  count?: number
}

export interface RewriteCandidate {
  value: string
  reason: string
}

export interface RewriteResponse {
  candidates: RewriteCandidate[]
}

export const plansApi = {
  list: () => http.get<Paginated<VideoPlan>>('/plans/').then((r) => r.data),

  get: (id: string) => http.get<VideoPlan>(`/plans/${id}/`).then((r) => r.data),

  create: (payload: PlanCreatePayload) =>
    http.post<VideoPlan>('/plans/', payload).then((r) => r.data),

  patch: (id: string, payload: Partial<VideoPlan>) =>
    http.patch<VideoPlan>(`/plans/${id}/`, payload).then((r) => r.data),

  remove: (id: string) => http.delete(`/plans/${id}/`).then((r) => r.data),

  generate: (input: GenerateInput, options: AITaskRequestOptions = {}) =>
    http.post<GeneratePlanResponse>('/plans/generate/', input, aiTaskRequestConfig(options)).then((r) => r.data),

  outline: (input: CreationOutlineInput) =>
    http.post<CreationOutline>('/plans/outline/', input).then((r) => r.data),

  optimize: (
    id: string,
    scope: OptimizeScope = 'full',
    options: AITaskRequestOptions & { hint?: string } = {},
  ) => {
    const { async: _async, hint, ...rest } = options
    void _async; void rest
    return http
      .post<OptimizePlanResponse>(
        `/plans/${id}/optimize/`,
        { scope, ...(hint ? { hint } : {}) },
        aiTaskRequestConfig(options),
      )
      .then((r) => r.data)
  },

  duplicate: (id: string) =>
    http.post<VideoPlan>(`/plans/${id}/duplicate/`, {}).then((r) => r.data),

  rewrite: (id: string, input: RewriteInput) =>
    http.post<RewriteResponse>(`/plans/${id}/rewrite/`, input).then((r) => r.data),

  review: (id: string) =>
    http.post<AICritique>(`/plans/${id}/review/`, {}).then((r) => r.data),

  exportPlan: async (id: string, format: PlanExportFormat, fallbackTitle = 'plan'): Promise<void> => {
    const resp = await http.get(`/plans/${id}/export/`, {
      params: { format },
      responseType: 'blob',
    })
    const filename = parseFilename(resp.headers['content-disposition']) || `${fallbackTitle}.${format}`
    triggerDownload(resp.data as Blob, filename)
  },

  exportMarkdown: (id: string, fallbackTitle = 'plan') =>
    plansApi.exportPlan(id, 'md', fallbackTitle),
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
