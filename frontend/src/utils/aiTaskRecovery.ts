import { aiTasksApi } from '@/api/aiTasks'
import { useAuthStore } from '@/stores/auth'
import type { AITask, AITaskStatus, AITaskType } from '@/types/api'

const STORAGE_KEY = 'vidplan.activeAiTasks.v1'
const DONE_STATUSES = new Set<AITaskStatus>(['succeeded', 'failed', 'canceled'])

export interface ActiveAITask {
  taskId: string
  taskType: AITaskType
  label: string
  targetId?: string
  createdAt: string
}

export interface WaitForAITaskOptions {
  intervalMs?: number
  timeoutMs?: number
  signal?: AbortSignal
  transport?: 'auto' | 'sse' | 'polling'
  onUpdate?: (task: AITask) => void
}

export function saveActiveAITask(task: ActiveAITask) {
  const tasks = loadActiveAITasks().filter((item) => item.taskId !== task.taskId)
  tasks.unshift(task)
  writeActiveAITasks(tasks.slice(0, 20))
}

export function removeActiveAITask(taskId: string) {
  writeActiveAITasks(loadActiveAITasks().filter((item) => item.taskId !== taskId))
}

export function findActiveAITask(
  taskType: AITaskType,
  matcher: (task: ActiveAITask) => boolean = () => true,
): ActiveAITask | null {
  return loadActiveAITasks().find((task) => task.taskType === taskType && matcher(task)) || null
}

export async function waitForAITask(taskId: string, options: WaitForAITaskOptions = {}): Promise<AITask> {
  const transport = options.transport ?? 'auto'
  if (transport !== 'polling') {
    try {
      return await waitForAITaskEvents(taskId, options)
    } catch (err) {
      if (isAbortError(err) || transport === 'sse') throw err
    }
  }
  return waitForAITaskPolling(taskId, options)
}

async function waitForAITaskPolling(taskId: string, options: WaitForAITaskOptions = {}): Promise<AITask> {
  const intervalMs = options.intervalMs ?? 2500
  const timeoutMs = options.timeoutMs ?? 10 * 60 * 1000
  const started = Date.now()

  while (true) {
    if (options.signal?.aborted) throw new DOMException('任务轮询已取消', 'AbortError')

    const task = await aiTasksApi.get(taskId)
    options.onUpdate?.(task)

    if (DONE_STATUSES.has(task.status)) {
      if (task.status === 'succeeded') return task
      throw new Error(task.error || task.status_label || 'AI 任务失败')
    }

    if (Date.now() - started > timeoutMs) {
      throw new Error('AI 任务等待超时,请稍后在任务列表恢复查看')
    }

    await sleep(intervalMs, options.signal)
  }
}

async function waitForAITaskEvents(taskId: string, options: WaitForAITaskOptions = {}): Promise<AITask> {
  const timeoutMs = options.timeoutMs ?? 10 * 60 * 1000
  const auth = useAuthStore()
  const controller = new AbortController()
  let timedOut = false
  const timer = window.setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)
  const abortFromCaller = () => controller.abort()
  options.signal?.addEventListener('abort', abortFromCaller, { once: true })

  try {
    const resp = await fetch(`/api/v1/ai-tasks/${taskId}/events/`, {
      headers: auth.accessToken ? { Authorization: `Bearer ${auth.accessToken}` } : {},
      signal: controller.signal,
    })
    if (!resp.ok || !resp.body) {
      throw new Error(`SSE 连接失败: ${resp.status}`)
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const finished = processSseBuffer(buffer, options.onUpdate)
      buffer = finished.remaining
      if (finished.task) {
        if (finished.task.status === 'succeeded') return finished.task
        throw new Error(finished.task.error || finished.task.status_label || 'AI 任务失败')
      }
    }

    const trailing = processSseBuffer(buffer, options.onUpdate, true)
    if (trailing.task) {
      if (trailing.task.status === 'succeeded') return trailing.task
      throw new Error(trailing.task.error || trailing.task.status_label || 'AI 任务失败')
    }
    throw new Error('SSE 连接已关闭,任务尚未完成')
  } catch (err) {
    if (timedOut) throw new Error('AI 任务等待超时,请稍后在任务列表恢复查看')
    throw err
  } finally {
    window.clearTimeout(timer)
    options.signal?.removeEventListener('abort', abortFromCaller)
  }
}

function processSseBuffer(
  buffer: string,
  onUpdate?: (task: AITask) => void,
  flush = false,
): { remaining: string; task: AITask | null } {
  const normalized = buffer.replace(/\r\n/g, '\n')
  const chunks = normalized.split('\n\n')
  const remaining = flush ? '' : chunks.pop() || ''
  const completeChunks = flush ? chunks : chunks

  for (const chunk of completeChunks) {
    const task = parseSseTask(chunk)
    if (!task) continue
    onUpdate?.(task)
    if (DONE_STATUSES.has(task.status)) {
      return { remaining, task }
    }
  }
  return { remaining, task: null }
}

function parseSseTask(chunk: string): AITask | null {
  const dataLines = chunk
    .split('\n')
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
  if (!dataLines.length) return null
  try {
    const parsed = JSON.parse(dataLines.join('\n'))
    return isAITask(parsed) ? parsed : null
  } catch {
    return null
  }
}

function isAITask(value: unknown): value is AITask {
  if (!value || typeof value !== 'object') return false
  const obj = value as Record<string, unknown>
  return typeof obj.id === 'string'
    && typeof obj.task_type === 'string'
    && typeof obj.status === 'string'
    && typeof obj.progress === 'number'
}

function loadActiveAITasks(): ActiveAITask[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter(isActiveAITask) : []
  } catch {
    return []
  }
}

function writeActiveAITasks(tasks: ActiveAITask[]) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks))
}

function isActiveAITask(value: unknown): value is ActiveAITask {
  if (!value || typeof value !== 'object') return false
  const obj = value as Record<string, unknown>
  return typeof obj.taskId === 'string'
    && typeof obj.taskType === 'string'
    && typeof obj.label === 'string'
    && typeof obj.createdAt === 'string'
}

function sleep(ms: number, signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('任务轮询已取消', 'AbortError'))
      return
    }
    const timer = window.setTimeout(resolve, ms)
    signal?.addEventListener('abort', () => {
      window.clearTimeout(timer)
      reject(new DOMException('任务轮询已取消', 'AbortError'))
    }, { once: true })
  })
}

function isAbortError(err: unknown) {
  return err instanceof DOMException && err.name === 'AbortError'
}
