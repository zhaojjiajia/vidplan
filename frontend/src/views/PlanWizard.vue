<template>
  <div class="vp-page creator-page">
    <section class="creator-shell">
      <h1 v-if="!conversationMessages.length && !generating">说出你的灵感，生成可执行视频方案</h1>

      <div v-if="generating || chatMessages.length" class="chat-stream">
        <div
          v-for="message in chatMessages"
          :key="message.key"
          :class="[
            'chat-bubble',
            `chat-bubble--${message.role}`,
            { 'chat-bubble--thinking': message.key === 'thinking' },
          ]"
        >
          <span>{{ message.text }}</span>
        </div>
      </div>

      <div
        class="ai-composer"
        :class="{ dragging: ideaDragging, generating }"
        @dragenter.prevent="ideaDragging = true"
        @dragover.prevent="ideaDragging = true"
        @dragleave="onIdeaDragLeave"
        @drop.prevent="onIdeaDrop"
      >
        <textarea
          v-model="form.idea"
          :disabled="generating"
          class="composer-input"
          :placeholder="composerPlaceholder"
          rows="4"
          @keydown.meta.enter.prevent="onSubmitComposer"
          @keydown.ctrl.enter.prevent="onSubmitComposer"
        />

        <div v-if="ideaDragging" class="drop-overlay">
          <el-icon><Upload /></el-icon>
          <span>松开即可导入</span>
        </div>

        <div class="composer-bar">
          <div class="mode-tabs" aria-label="创建模式">
            <button
              type="button"
              :class="['mode-pill', { active: planType === 'single' }]"
              :disabled="generating || !!currentOutline"
              @click="planType = 'single'"
            >
              单条模式
            </button>
            <button
              type="button"
              :class="['mode-pill', { active: planType === 'series' }]"
              :disabled="generating || !!currentOutline"
              @click="planType = 'series'"
            >
              系列模式
            </button>
          </div>

          <div class="composer-actions">
            <input
              ref="fileInputRef"
              class="file-input"
              type="file"
              accept=".md,.markdown,.txt,text/markdown,text/plain"
              @change="onFilePicked"
            />
            <button
              type="button"
              class="icon-button"
              title="导入 Markdown"
              :disabled="generating"
              @click="triggerFilePicker"
            >
              <el-icon><Paperclip /></el-icon>
            </button>
            <button
              type="button"
              class="send-button"
              :title="sendButtonTitle"
              :disabled="generating || !canSubmitComposer"
              @click="onSubmitComposer"
            >
              <el-icon v-if="!generating"><Top /></el-icon>
              <span v-else class="send-loading" />
            </button>
          </div>
        </div>
      </div>

      <div v-if="currentOutline && !generating" class="outline-actions">
        <button type="button" class="outline-action outline-action--primary" @click="approveOutlineAndGenerate">
          <el-icon><Check /></el-icon>
          <span>同意大纲，生成详细方案</span>
        </button>
        <button type="button" class="outline-action" @click="resetOutlineDraft">
          <el-icon><RefreshLeft /></el-icon>
          <span>重新开始</span>
        </button>
      </div>

      <div v-if="!currentOutline" class="idea-examples" aria-label="方向灵感">
        <button
          v-for="example in ideaExamples"
          :key="example.title"
          type="button"
          :disabled="generating"
          @click="applyIdeaExample(example)"
        >
          <span>{{ example.title }}</span>
          <small>{{ example.prompt }}</small>
        </button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check, Paperclip, RefreshLeft, Top, Upload } from '@element-plus/icons-vue'

import { isAITaskResponse } from '@/api/aiTasks'
import type { PlanMarkdownImportData } from '@/api/markdownImport'
import { plansApi } from '@/api/plans'
import type { CreationOutline } from '@/api/plans'
import { seriesApi } from '@/api/series'
import type { AITask } from '@/types/api'
import {
  extractMarkdownNumber,
  extractMarkdownValue,
  markdownToPlain,
} from '@/utils/markdownImport'
import {
  findActiveAITask,
  removeActiveAITask,
  saveActiveAITask,
  waitForAITask,
} from '@/utils/aiTaskRecovery'

type PlanType = 'single' | 'series'
type ChatMessage = { key: string; role: 'user' | 'ai'; text: string }
type IdeaExample = { title: string; prompt: string; mode: PlanType }

const router = useRouter()
const planType = ref<PlanType>('single')
const generating = ref(false)
const generationPhase = ref<'outline' | 'detail'>('detail')
const ideaDragging = ref(false)
const taskProgress = ref(10)
const taskMessage = ref('AI 正在生成方案...')
const elapsedSeconds = ref(0)
const fileInputRef = ref<HTMLInputElement | null>(null)
const currentOutline = ref<CreationOutline | null>(null)
const outlineSeed = ref('')
const outlineFeedbacks = ref<string[]>([])
const conversationMessages = ref<ChatMessage[]>([])
let taskAbortController: AbortController | null = null
let elapsedTimer: number | null = null

const form = reactive({
  idea: '',
  target_audience: '',
  duration_seconds: 30,
  style: '',
})

const ideaExamples: IdeaExample[] = [
  {
    title: 'AI 悬疑短剧',
    prompt: '校园里每个人都收到同一条未来短信,60 秒反转收尾',
    mode: 'series',
  },
  {
    title: '探店反差脚本',
    prompt: '一家看起来普通的小店,最后发现隐藏招牌菜',
    mode: 'single',
  },
  {
    title: '知识口播',
    prompt: '用 30 秒讲清一个普通人容易踩坑的 AI 工具用法',
    mode: 'single',
  },
  {
    title: '治愈日常系列',
    prompt: '一个独居女孩和城市角落的温暖小事,每集 60 秒',
    mode: 'series',
  },
  {
    title: '产品种草',
    prompt: '把一个智能硬件做成先痛点后解决方案的种草视频',
    mode: 'single',
  },
  {
    title: '人物关系剧',
    prompt: '三个人在同一个虚拟空间里互相隐瞒身份,做成连载短剧',
    mode: 'series',
  },
]

const composerPlaceholder = computed(() => (
  currentOutline.value ? '补充你想调整的大纲内容...' : '描述你想做的视频或系列...'
))

const sendButtonTitle = computed(() => (
  currentOutline.value ? '补充大纲' : '生成大纲'
))

const canSubmitComposer = computed(() => Boolean(form.idea.trim()))

const chatMessages = computed<ChatMessage[]>(() => {
  const messages: ChatMessage[] = [...conversationMessages.value]
  if (generating.value) {
    messages.push({
      key: 'thinking',
      role: 'ai',
      text: activeGeneratingText.value,
    })
  }
  return messages
})

const generationStages = [
  {
    threshold: 0,
    single: '我在理解你的想法,准备拆成短视频结构。',
    series: '我在理解你的系列设定,准备拆出可连载的核心结构。',
  },
  {
    threshold: 4,
    single: '我在设计钩子、节奏和章节结构。',
    series: '我在设计系列定位、人物/环境资产和单集节奏。',
  },
  {
    threshold: 10,
    single: '我在整理章节内容、核心看点和交付建议。',
    series: '我在整理人物设定、环境设定、选题池和系列模板。',
  },
  {
    threshold: 18,
    single: '我在校验输出格式,马上进入可编辑方案。',
    series: '我在校验系列方案,马上进入系列工作台。',
  },
]

const activeGeneratingText = computed(() => {
  if (generationPhase.value === 'outline') {
    return `我先把内容整理成待确认的大纲。 ${taskMessage.value ? `(${taskMessage.value})` : ''}`
  }
  const stage = [...generationStages]
    .reverse()
    .find((item) => elapsedSeconds.value >= item.threshold) || generationStages[0]
  const base = planType.value === 'series' ? stage.series : stage.single
  return `${base} ${taskMessage.value ? `(${taskMessage.value})` : ''}`
})

function startElapsedClock() {
  const startedAt = Date.now()
  elapsedSeconds.value = 0
  if (elapsedTimer !== null) window.clearInterval(elapsedTimer)
  elapsedTimer = window.setInterval(() => {
    elapsedSeconds.value = Math.floor((Date.now() - startedAt) / 1000)
  }, 250)
}

function stopElapsedClock() {
  if (elapsedTimer !== null) {
    window.clearInterval(elapsedTimer)
    elapsedTimer = null
  }
}

function triggerFilePicker() {
  fileInputRef.value?.click()
}

async function onFilePicked(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  importPlanMarkdown(await file.text(), '已导入文件内容')
  input.value = ''
}

function importPlanMarkdown(text: string, successMessage: string) {
  resetOutlineDraft()
  const local = parsePlanMarkdown(text)
  applyPlanImportValues(local)
  ElMessage.success(successMessage)
}

function parsePlanMarkdown(text: string): PlanMarkdownImportData {
  const plain = markdownToPlain(text)
  const idea = extractMarkdownValue(text, ['想法描述', '创作想法', '想法', '方案', '简介', '摘要', '内容'])
  const audience = extractMarkdownValue(text, ['目标观众', '目标受众', '受众', '观众'])
  const style = extractMarkdownValue(text, ['内容风格', '风格', '调性'])
  const duration = extractPlanDuration(text)

  return {
    idea: idea || plain,
    target_audience: audience,
    duration_seconds: duration,
    style,
  }
}

function applyPlanImportValues(values: PlanMarkdownImportData) {
  if (values.idea) form.idea = values.idea
  if (values.target_audience) form.target_audience = values.target_audience
  if (values.style) form.style = values.style
  if (values.duration_seconds) {
    form.duration_seconds = Math.min(600, Math.max(5, Math.round(values.duration_seconds)))
  }
}

function applyIdeaExample(example: IdeaExample) {
  resetOutlineDraft()
  planType.value = example.mode
  form.idea = example.prompt
}

async function onIdeaDrop(event: DragEvent) {
  ideaDragging.value = false
  const { text, fromFile } = await readDropText(event)
  if (!text) {
    ElMessage.warning('未读取到可导入内容')
    return
  }
  importPlanMarkdown(text, fromFile ? '已解析 Markdown' : '已导入想法描述')
}

function onIdeaDragLeave(event: DragEvent) {
  const target = event.currentTarget
  const related = event.relatedTarget
  if (target instanceof HTMLElement && related instanceof Node && target.contains(related)) return
  ideaDragging.value = false
}

async function readDropText(event: DragEvent) {
  const data = event.dataTransfer
  if (!data) return { text: '', fromFile: false }

  const file = Array.from(data.files || [])[0]
  if (file) return { text: await file.text(), fromFile: true }

  return {
    text: data.getData('text/markdown') || data.getData('text/plain') || '',
    fromFile: false,
  }
}

function extractPlanDuration(text: string) {
  const labeled = extractMarkdownNumber(text, ['时长', '视频时长', '持续时间'])
  if (labeled) return labeled
  const match = markdownToPlain(text).match(/(\d+(?:\.\d+)?)\s*(秒|s|S)/)
  return match ? Number(match[1]) : null
}

async function onSubmitComposer() {
  if (!form.idea.trim() || generating.value) return

  try {
    await requestOutline(form.idea.trim())
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '大纲整理失败')
  }
}

async function requestOutline(input: string) {
  const isFirstOutline = !currentOutline.value
  const previousSeed = outlineSeed.value
  const previousFeedbacks = [...outlineFeedbacks.value]
  const previousMessages = [...conversationMessages.value]
  if (isFirstOutline) {
    outlineSeed.value = input
    outlineFeedbacks.value = []
    conversationMessages.value = [{ key: `user-${Date.now()}`, role: 'user', text: input }]
  } else {
    outlineFeedbacks.value.push(input)
    conversationMessages.value.push({ key: `user-${Date.now()}`, role: 'user', text: input })
  }

  generating.value = true
  generationPhase.value = 'outline'
  taskProgress.value = 10
  taskMessage.value = 'AI 正在整理简单大纲...'
  startElapsedClock()
  try {
    const outline = await plansApi.outline({
      plan_type: planType.value,
      direction: '',
      idea: outlineSeed.value,
      target_audience: form.target_audience,
      style: form.style,
      previous_outline: currentOutline.value ? formatOutlinePlain(currentOutline.value) : '',
      feedback: isFirstOutline ? '' : input,
    })
    currentOutline.value = outline
    conversationMessages.value.push({
      key: `ai-outline-${Date.now()}`,
      role: 'ai',
      text: formatOutlineMessage(outline),
    })
    form.idea = ''
  } catch (err) {
    outlineSeed.value = previousSeed
    outlineFeedbacks.value = previousFeedbacks
    conversationMessages.value = previousMessages
    throw err
  } finally {
    generating.value = false
    stopElapsedClock()
  }
}

async function approveOutlineAndGenerate() {
  if (!currentOutline.value || generating.value) return

  generating.value = true
  generationPhase.value = 'detail'
  taskProgress.value = 10
  taskMessage.value = planType.value === 'series' ? 'AI 正在生成系列方案...' : 'AI 正在生成方案...'
  startElapsedClock()
  try {
    const idea = buildDetailedIdea()
    if (planType.value === 'series') {
      await generateSeries(idea)
    } else {
      await generateSingle(idea)
    }
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : 'AI 生成失败')
  } finally {
    generating.value = false
    stopElapsedClock()
  }
}

async function generateSingle(idea: string) {
  const result = await plansApi.generate({
    direction: '',
    category: 'real',
    is_ai_generated_video: false,
    idea,
    target_platform: '',
    target_audience: form.target_audience,
    duration_seconds: form.duration_seconds,
    style: form.style,
  })
  if (isAITaskResponse(result)) {
    saveActiveAITask({
      taskId: result.id,
      taskType: 'generate_plan',
      label: '生成单条方案',
      createdAt: new Date().toISOString(),
    })
    await followGenerateTask(result, 'single')
    return
  }
  router.push(`/app/plan/${result.id}`)
}

async function generateSeries(idea: string) {
  const result = await seriesApi.generate({
    direction: '',
    idea,
    target_platform: '',
    target_audience: form.target_audience,
    update_frequency: '周更',
    episode_duration_seconds: 60,
    planned_episodes: 10,
    style: form.style,
    auto_create_assets: true,
  })
  if (isAITaskResponse(result)) {
    saveActiveAITask({
      taskId: result.id,
      taskType: 'generate_series',
      label: '生成系列方案',
      createdAt: new Date().toISOString(),
    })
    await followGenerateTask(result, 'series')
    return
  }
  router.push(`/app/series/${result.id}`)
}

function formatOutlineMessage(outline: CreationOutline) {
  const lines = [`大纲: ${outline.title || '未命名'}`]
  if (outline.summary) lines.push(outline.summary)
  const meta = [
    outline.direction_label,
    outline.audience,
    outline.style,
  ].filter(Boolean)
  if (meta.length) lines.push(meta.join(' · '))
  outline.outline.forEach((item, index) => {
    const title = item.title || `第 ${index + 1} 部分`
    lines.push(`${index + 1}. ${title}${item.note ? `: ${item.note}` : ''}`)
  })
  if (outline.key_points.length) {
    lines.push(`确认点: ${outline.key_points.join('；')}`)
  }
  return lines.join('\n')
}

function formatOutlinePlain(outline: CreationOutline) {
  return [
    `标题: ${outline.title}`,
    `摘要: ${outline.summary}`,
    `方向: ${outline.direction_label || outline.direction}`,
    `观众: ${outline.audience}`,
    `风格: ${outline.style}`,
    '大纲:',
    ...outline.outline.map((item, index) => `${index + 1}. ${item.title}${item.note ? ` - ${item.note}` : ''}`),
    outline.key_points.length ? `确认点: ${outline.key_points.join('；')}` : '',
  ].filter(Boolean).join('\n')
}

function buildDetailedIdea() {
  const parts = [
    `用户原始内容:\n${outlineSeed.value}`,
    `用户已确认的大纲:\n${currentOutline.value ? formatOutlinePlain(currentOutline.value) : ''}`,
  ]
  if (outlineFeedbacks.value.length) {
    parts.push(`用户补充要求:\n${outlineFeedbacks.value.join('\n')}`)
  }
  return parts.join('\n\n')
}

function resetOutlineDraft() {
  currentOutline.value = null
  outlineSeed.value = ''
  outlineFeedbacks.value = []
  conversationMessages.value = []
}

async function followGenerateTask(task: AITask, type: PlanType) {
  taskAbortController?.abort()
  taskAbortController = new AbortController()
  taskProgress.value = Math.max(task.progress || 0, 10)
  taskMessage.value = task.status === 'queued' ? 'AI 任务已排队,正在等待执行...' : 'AI 正在生成...'
  try {
    const finished = await waitForAITask(task.id, {
      signal: taskAbortController.signal,
      onUpdate: (latest) => {
        taskProgress.value = Math.max(latest.progress || 0, 10)
        taskMessage.value = latest.status === 'queued' ? 'AI 任务已排队,正在等待执行...' : 'AI 正在生成...'
      },
    })
    removeActiveAITask(task.id)
    if (type === 'series') {
      const seriesId = typeof finished.result_payload.series_id === 'string' ? finished.result_payload.series_id : ''
      if (!seriesId) throw new Error('AI 任务已完成,但未返回系列 ID')
      ElMessage.success('AI 生成完成')
      router.push(`/app/series/${seriesId}`)
      return
    }

    const planId = typeof finished.result_payload.plan_id === 'string' ? finished.result_payload.plan_id : ''
    if (!planId) throw new Error('AI 任务已完成,但未返回方案 ID')
    ElMessage.success('AI 生成完成')
    router.push(`/app/plan/${planId}`)
  } catch (err) {
    if (isAbortError(err)) return
    removeActiveAITask(task.id)
    ElMessage.error(err instanceof Error ? err.message : 'AI 生成失败')
  }
}

onMounted(async () => {
  const activePlan = findActiveAITask('generate_plan')
  const activeSeries = findActiveAITask('generate_series')
  const active = activePlan || activeSeries
  if (!active) return
  planType.value = active.taskType === 'generate_series' ? 'series' : 'single'
  generating.value = true
  generationPhase.value = 'detail'
  startElapsedClock()
  await followGenerateTask({
    id: active.taskId,
    task_type: active.taskType,
    task_type_label: active.label,
    status: 'queued',
    status_label: '排队中',
    title: active.label,
    progress: 0,
    input_payload: {},
    result_payload: {},
    error: '',
    started_at: null,
    finished_at: null,
    created_at: active.createdAt,
    updated_at: active.createdAt,
  }, planType.value)
  generating.value = false
})

onBeforeUnmount(() => {
  taskAbortController?.abort()
  stopElapsedClock()
})

function isAbortError(err: unknown) {
  return err instanceof DOMException && err.name === 'AbortError'
}
</script>

<style scoped>
.creator-page {
  min-height: calc(100vh - var(--vp-topbar-h));
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 44px 18px 92px;
  background: transparent;
}
.creator-shell {
  width: min(860px, 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}
.creator-shell h1 {
  margin: 0;
  color: var(--vp-text-1);
  font-size: 42px;
  line-height: 1.18;
  font-weight: 780;
  text-align: center;
  letter-spacing: 0;
  text-shadow: 0 2px 12px rgba(255, 250, 246, .86), 0 1px 0 rgba(255, 255, 255, .72);
}
.chat-stream {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.chat-bubble {
  max-width: min(680px, 92%);
  border-radius: 18px;
  padding: 12px 16px;
  font-size: 16px;
  line-height: 1.65;
  backdrop-filter: blur(14px) saturate(132%);
}
.chat-bubble span {
  white-space: pre-line;
}
.chat-bubble--user {
  align-self: flex-end;
  color: var(--vp-text-1);
  background: rgba(255, 255, 255, .66);
}
.chat-bubble--ai {
  align-self: flex-start;
  color: var(--vp-text-2);
  background: color-mix(in srgb, var(--vp-primary-soft) 44%, rgba(255, 255, 255, .68));
}
.chat-bubble--thinking {
  color: var(--vp-primary);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, .64), rgba(255, 255, 255, .28)),
    color-mix(in srgb, var(--vp-primary-soft) 72%, transparent);
  box-shadow: 0 14px 38px rgba(84, 40, 36, .08);
  position: relative;
  overflow: hidden;
}
.chat-bubble--thinking::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, transparent 0%, rgba(255, 255, 255, .52) 45%, transparent 72%);
  transform: translateX(-100%);
  animation: thinking-shine 1.8s ease-in-out infinite;
}
.ai-composer {
  position: relative;
  width: 100%;
  min-height: 124px;
  border: 1px solid rgba(94, 78, 70, .14);
  border-radius: 30px;
  background: rgba(255, 255, 255, .58);
  box-shadow: 0 24px 70px rgba(84, 40, 36, .12), 0 1px 0 rgba(255, 255, 255, .72) inset;
  backdrop-filter: blur(18px) saturate(148%);
  padding: 18px 16px 12px;
  transition: border-color .15s, box-shadow .15s, background .15s;
}
.ai-composer:focus-within,
.ai-composer.dragging {
  border-color: color-mix(in srgb, var(--vp-primary) 42%, rgba(94, 105, 111, .18));
  background: rgba(255, 255, 255, .68);
  box-shadow: 0 28px 80px rgba(84, 40, 36, .16), 0 0 0 3px color-mix(in srgb, var(--vp-primary-soft) 76%, transparent);
}
.ai-composer.generating {
  opacity: .86;
}
.composer-input {
  width: 100%;
  height: 86px;
  resize: none;
  border: none;
  outline: none;
  background: transparent;
  color: var(--vp-text-1);
  font: inherit;
  font-size: 16.5px;
  line-height: 1.6;
  padding: 0;
}
.composer-input::placeholder {
  color: color-mix(in srgb, var(--vp-text-3) 72%, white);
}
.composer-bar {
  margin-top: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.mode-tabs,
.composer-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.mode-pill {
  height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(88, 100, 107, .14);
  background: rgba(255, 255, 255, .56);
  color: var(--vp-text-2);
  font: inherit;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
}
.mode-pill:hover {
  color: var(--vp-primary);
}
.mode-pill.active {
  border-color: color-mix(in srgb, var(--vp-primary) 38%, rgba(88, 100, 107, .14));
  background: var(--vp-primary-soft);
  color: var(--vp-primary);
}
.file-input {
  display: none;
}
.icon-button,
.send-button {
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.icon-button {
  background: transparent;
  color: var(--vp-text-2);
}
.icon-button:hover {
  color: var(--vp-primary);
  background: var(--vp-primary-soft);
}
.send-button {
  background: color-mix(in srgb, var(--vp-primary) 74%, #9fb5ff);
  color: #fff;
}
.send-button:hover {
  background: var(--vp-primary);
}
.send-button:disabled,
.mode-pill:disabled,
.icon-button:disabled {
  cursor: not-allowed;
  opacity: .56;
}
.send-loading {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, .48);
  border-top-color: #fff;
  animation: spin .8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
@keyframes thinking-shine {
  to { transform: translateX(100%); }
}
.drop-overlay {
  position: absolute;
  inset: 10px;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 18px;
  background: color-mix(in srgb, var(--vp-surface) 78%, var(--vp-primary-soft));
  color: var(--vp-primary);
  font-size: 15px;
  font-weight: 650;
  pointer-events: none;
}

.outline-actions {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}
.outline-action {
  height: 38px;
  padding: 0 15px;
  border-radius: 999px;
  border: 1px solid rgba(88, 100, 107, .14);
  background: rgba(255, 255, 255, .58);
  color: var(--vp-text-2);
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(84, 40, 36, .07);
}
.outline-action:hover {
  color: var(--vp-primary);
  border-color: color-mix(in srgb, var(--vp-primary) 34%, rgba(88, 100, 107, .14));
  background: rgba(255, 255, 255, .7);
}
.outline-action--primary {
  border-color: color-mix(in srgb, var(--vp-primary) 44%, transparent);
  background: var(--vp-primary);
  color: #fff;
}
.outline-action--primary:hover {
  background: color-mix(in srgb, var(--vp-primary) 86%, #fff);
  color: #fff;
}

.idea-examples {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.idea-examples button {
  min-width: 0;
  min-height: 76px;
  border: 1px solid rgba(94, 78, 70, .11);
  border-radius: 20px;
  background: rgba(255, 255, 255, .46);
  backdrop-filter: blur(14px) saturate(132%);
  color: var(--vp-text-2);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 12px 14px;
  text-align: left;
  box-shadow: 0 12px 30px rgba(84, 40, 36, .07);
  transition: border-color .15s, background .15s, transform .15s, box-shadow .15s;
}
.idea-examples button:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--vp-primary) 34%, rgba(94, 78, 70, .11));
  background: rgba(255, 255, 255, .62);
  box-shadow: 0 16px 36px rgba(84, 40, 36, .10);
}
.idea-examples button:disabled {
  cursor: not-allowed;
  opacity: .58;
}
.idea-examples span {
  color: var(--vp-text-1);
  font-size: 14px;
  font-weight: 760;
  line-height: 1.2;
}
.idea-examples small {
  color: var(--vp-text-3);
  font-size: 12px;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (max-width: 720px) {
  .creator-page {
    align-items: flex-start;
    padding-top: 54px;
  }
  .creator-shell h1 {
    font-size: 30px;
  }
  .composer-bar {
    align-items: stretch;
    flex-direction: column;
  }
  .composer-actions {
    justify-content: flex-end;
  }
  .mode-tabs {
    width: 100%;
  }
  .mode-pill {
    flex: 1;
  }
  .idea-examples {
    grid-template-columns: 1fr;
  }
  .outline-actions {
    align-items: stretch;
    flex-direction: column;
  }
  .outline-action {
    justify-content: center;
    width: 100%;
  }
  .idea-examples button {
    min-height: 64px;
  }
}
</style>
