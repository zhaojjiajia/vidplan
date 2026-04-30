import { http } from './index'
import type { AITask, Paginated, TaskAware, VideoPlan } from '@/types/api'

export interface GenerateInput {
  direction: string
  category: 'real' | 'ai_generated'
  is_ai_generated_video: boolean
  idea: string
  target_platform?: string
  target_audience?: string
  duration_seconds?: number
  style?: string
}

export type OptimizeScope = 'full' | 'title' | 'hook' | 'storyboard' | 'editing' | 'ai_prompt'
export type PlanExportFormat = 'md' | 'pdf' | 'docx'
export type GeneratePlanResponse = TaskAware<VideoPlan> | AITask
export type OptimizePlanResponse = TaskAware<VideoPlan> | AITask

export interface AITaskRequestOptions {
  async?: boolean
}

export const plansApi = {
  list: () => http.get<Paginated<VideoPlan>>('/plans/').then((r) => r.data),

  get: (id: string) => http.get<VideoPlan>(`/plans/${id}/`).then((r) => r.data),

  patch: (id: string, payload: Partial<VideoPlan>) =>
    http.patch<VideoPlan>(`/plans/${id}/`, payload).then((r) => r.data),

  remove: (id: string) => http.delete(`/plans/${id}/`).then((r) => r.data),

  generate: (input: GenerateInput, options: AITaskRequestOptions = {}) =>
    http.post<GeneratePlanResponse>('/plans/generate/', input, aiTaskRequestConfig(options)).then((r) => r.data),

  optimize: (id: string, scope: OptimizeScope = 'full', options: AITaskRequestOptions = {}) =>
    http.post<OptimizePlanResponse>(`/plans/${id}/optimize/`, { scope }, aiTaskRequestConfig(options)).then((r) => r.data),

  duplicate: (id: string) =>
    http.post<VideoPlan>(`/plans/${id}/duplicate/`, {}).then((r) => r.data),

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
