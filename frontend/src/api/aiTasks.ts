import { http } from './index'
import type { AITask, AITaskStatus, AITaskType, Paginated } from '@/types/api'

export interface AITaskListParams {
  status?: AITaskStatus
  task_type?: AITaskType
}

export const aiTasksApi = {
  list: (params: AITaskListParams = {}) =>
    http.get<Paginated<AITask>>('/ai-tasks/', { params }).then((r) => r.data),

  get: (id: string) => http.get<AITask>(`/ai-tasks/${id}/`).then((r) => r.data),
}

export function isAITaskResponse(value: unknown): value is AITask {
  if (!value || typeof value !== 'object') return false
  const obj = value as Record<string, unknown>
  return typeof obj.id === 'string'
    && typeof obj.task_type === 'string'
    && typeof obj.status === 'string'
    && typeof obj.progress === 'number'
    && typeof obj.input_payload === 'object'
    && typeof obj.result_payload === 'object'
}
