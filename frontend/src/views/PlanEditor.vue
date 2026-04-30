<template>
  <div class="editor" v-loading="loading && !plan">
    <template v-if="plan">
      <header class="head">
        <div>
          <el-input v-model="form.title" class="title-input" placeholder="视频标题" @input="onTitleChange" />
          <div class="meta">
            <span class="vp-status" data-tone="primary">{{ findDirectionLabel(plan.direction) }}</span>
            <span class="vp-status">{{ plan.target_platform || '未指定平台' }}</span>
            <span class="vp-status">{{ plan.duration_seconds }}s</span>
            <span class="vp-status" :data-tone="statusTone" :class="{ 'is-pulsing': plan.status === 'optimizing' }">
              {{ statusLabel }}
            </span>
            <el-select
              v-model="seriesId"
              placeholder="未关联系列"
              size="small"
              clearable
              filterable
              class="series-select"
              @change="onSeriesChange"
            >
              <el-option v-for="s in seriesOptions" :key="s.id" :label="s.title" :value="s.id" />
            </el-select>
            <span v-if="saveStatus" class="save-pill" :data-state="saveState">
              <span class="save-dot" />
              {{ saveStatus }}
            </span>
          </div>
        </div>
        <div class="head-actions">
          <el-button :icon="ArrowLeft" @click="router.push('/app/me/plans')">返回</el-button>
          <el-dropdown @command="onOptimize">
            <el-button :loading="optimizing" type="primary">
              AI 优化<el-icon class="el-icon--right"><arrow-down /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="full">完善整体方案</el-dropdown-item>
                <el-dropdown-item command="title">优化标题</el-dropdown-item>
                <el-dropdown-item command="hook">优化开头钩子</el-dropdown-item>
                <el-dropdown-item command="storyboard">优化分镜</el-dropdown-item>
                <el-dropdown-item command="editing">补充剪辑建议</el-dropdown-item>
                <el-dropdown-item command="ai_prompt">优化 AI 提示词</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button :icon="Check" @click="onConfirm" :disabled="plan.status === 'confirmed'">
            {{ plan.status === 'confirmed' ? '已确认' : '确认方案' }}
          </el-button>
        </div>
      </header>

      <el-alert
        v-if="optimizeTaskMessage"
        class="task-alert"
        type="info"
        :closable="false"
        show-icon
      >
        <template #title>
          <div class="task-title">
            <span>{{ optimizeTaskMessage }}</span>
            <el-progress :percentage="optimizeTaskProgress" :stroke-width="6" class="task-progress" />
          </div>
        </template>
      </el-alert>

      <div class="body editor-grid">
        <aside class="editor-outline">
          <div class="outline-card">
            <span class="outline-kicker">方案档案</span>
            <strong>{{ statusLabel || '草稿' }}</strong>
            <p>{{ outlineSummary }}</p>
            <div class="outline-metrics">
              <div>
                <span>分镜</span>
                <b>{{ form.storyboard.length }}</b>
              </div>
              <div>
                <span>镜头时长</span>
                <b>{{ totalShotDuration }}s</b>
              </div>
            </div>
            <nav class="outline-nav" aria-label="编辑区导航">
              <a href="#positioning">视频定位</a>
              <a href="#structure">视频结构</a>
              <a href="#storyboard">分镜脚本</a>
              <a href="#delivery">发布交付</a>
            </nav>
          </div>
        </aside>

        <section class="editor-main">
          <el-card id="positioning" class="editor-section">
            <template #header>视频定位</template>
            <el-form label-position="top">
              <el-form-item label="一句话简介">
                <el-input v-model="form.summary" type="textarea" :rows="2" @input="scheduleSave" />
              </el-form-item>
              <el-form-item label="核心定位">
                <el-input v-model="contentDraft.positioning" type="textarea" :rows="2" @input="scheduleSave" />
              </el-form-item>
              <el-form-item label="核心看点">
                <el-input v-model="highlightsText" type="textarea" :rows="3" placeholder="每行一个看点" @input="scheduleSave" />
              </el-form-item>
            </el-form>
          </el-card>

          <el-card id="structure" class="mt editor-section">
            <template #header>视频结构</template>
            <el-form label-position="top">
              <el-form-item label="开头 0-3 秒">
                <el-input v-model="contentDraft.structure.hook" type="textarea" :rows="2" @input="scheduleSave" />
              </el-form-item>
              <el-form-item label="中段展开">
                <el-input v-model="contentDraft.structure.body" type="textarea" :rows="3" @input="scheduleSave" />
              </el-form-item>
              <el-form-item label="高潮 / 反转">
                <el-input v-model="contentDraft.structure.climax" type="textarea" :rows="2" @input="scheduleSave" />
              </el-form-item>
              <el-form-item label="结尾引导">
                <el-input v-model="contentDraft.structure.ending" type="textarea" :rows="2" @input="scheduleSave" />
              </el-form-item>
            </el-form>
          </el-card>

          <el-card id="storyboard" class="mt editor-section">
            <template #header>
              <div class="card-header-row">
                分镜脚本
                <el-button text type="primary" :icon="Plus" @click="addShot">添加分镜</el-button>
              </div>
            </template>
            <div v-if="form.storyboard.length === 0" class="muted">暂无分镜,可让 AI 生成或手动添加。</div>
            <div v-for="(shot, idx) in form.storyboard" :key="idx" class="shot">
              <div class="shot-head">
                <strong>镜头 {{ idx + 1 }}</strong>
                <div class="shot-control">
                  <el-input-number v-model="shot.duration" :min="1" :max="60" size="small" /> 秒
                  <el-button text type="danger" size="small" :icon="Delete" @click="removeShot(idx)">删除</el-button>
                </div>
              </div>
              <el-input v-model="shot.visual" placeholder="画面描述" size="small" @input="scheduleSave" />
              <el-input v-model="shot.line" placeholder="台词 / 旁白" size="small" class="mt-sm" @input="scheduleSave" />
              <el-input v-model="shot.editing" placeholder="剪辑提示" size="small" class="mt-sm" @input="scheduleSave" />
              <el-input v-model="shot.ai_prompt" placeholder="AI 生成提示词" size="small" class="mt-sm" @input="scheduleSave" />
            </div>
          </el-card>
        </section>

        <aside id="delivery" class="editor-side">
          <el-card>
            <template #header>发布与封面</template>
            <el-form label-position="top">
              <el-form-item label="字幕建议">
                <el-input v-model="contentDraft.subtitles" type="textarea" :rows="2" @input="scheduleSave" />
              </el-form-item>
              <el-form-item label="音乐建议">
                <el-input v-model="contentDraft.music" type="textarea" :rows="2" @input="scheduleSave" />
              </el-form-item>
              <el-form-item label="发布文案">
                <el-input v-model="contentDraft.publish_caption" type="textarea" :rows="3" @input="scheduleSave" />
              </el-form-item>
              <el-form-item label="封面文案">
                <el-input v-model="contentDraft.cover_caption" type="textarea" :rows="2" @input="scheduleSave" />
              </el-form-item>
            </el-form>
          </el-card>

          <el-card class="mt">
            <template #header>剪辑建议</template>
            <el-input v-model="editingText" type="textarea" :rows="6" placeholder="每行一条建议" @input="scheduleSave" />
          </el-card>

          <el-card class="mt">
            <template #header>AI 生成提示词</template>
            <el-form label-position="top">
              <el-form-item label="正向提示词">
                <el-input v-model="aiPromptDraft.positive" type="textarea" :rows="3" @input="scheduleSave" />
              </el-form-item>
              <el-form-item label="负向提示词">
                <el-input v-model="aiPromptDraft.negative" type="textarea" :rows="2" @input="scheduleSave" />
              </el-form-item>
            </el-form>
          </el-card>
        </aside>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, ArrowLeft, Check, Delete, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { isAITaskResponse } from '@/api/aiTasks'
import { plansApi, type OptimizeScope } from '@/api/plans'
import { seriesApi } from '@/api/series'
import { findDirectionLabel } from '@/data/directions'
import { useDebouncedSave } from '@/composables/useDebouncedSave'
import type { AITask, SeriesPlan, StoryboardShot, VideoPlan } from '@/types/api'
import {
  findActiveAITask,
  removeActiveAITask,
  saveActiveAITask,
  waitForAITask,
} from '@/utils/aiTaskRecovery'

const route = useRoute()
const router = useRouter()

const plan = ref<VideoPlan | null>(null)
const loading = ref(false)
const optimizing = ref(false)
const optimizeTaskProgress = ref(0)
const optimizeTaskMessage = ref('')
const seriesOptions = ref<SeriesPlan[]>([])
const seriesId = ref<string | null>(null)
let optimizeAbortController: AbortController | null = null

const form = reactive({
  title: '',
  summary: '',
  storyboard: [] as StoryboardShot[],
})

const contentDraft = reactive({
  positioning: '',
  highlights: [] as string[],
  structure: { hook: '', body: '', climax: '', ending: '' },
  subtitles: '',
  music: '',
  publish_caption: '',
  cover_caption: '',
})

const editingDraft = reactive<{ steps: string[] }>({ steps: [] })
const aiPromptDraft = reactive({ positive: '', negative: '' })

const highlightsText = computed({
  get: () => contentDraft.highlights.join('\n'),
  set: (v) => {
    contentDraft.highlights = v.split('\n').map((s) => s.trim()).filter(Boolean)
  },
})

const editingText = computed({
  get: () => editingDraft.steps.join('\n'),
  set: (v) => {
    editingDraft.steps = v.split('\n').map((s) => s.trim()).filter(Boolean)
  },
})
const totalShotDuration = computed(() =>
  form.storyboard.reduce((sum, shot) => sum + (Number(shot.duration) || 0), 0)
)
const outlineSummary = computed(() => {
  const summary = form.summary.trim()
  if (!summary) return '未填写简介'
  return summary.length > 68 ? `${summary.slice(0, 68)}…` : summary
})

const statusLabel = computed(() => {
  switch (plan.value?.status) {
    case 'draft': return '草稿'
    case 'optimizing': return '优化中'
    case 'confirmed': return '已确认'
    case 'completed': return '已完成'
    default: return ''
  }
})
const statusTone = computed(() => {
  switch (plan.value?.status) {
    case 'optimizing': return 'warning'
    case 'confirmed':
    case 'completed': return 'success'
    default: return 'info'
  }
})

const { saving, savedAt, schedule, flush } = useDebouncedSave(async (payload: Partial<VideoPlan>) => {
  if (!plan.value) return
  plan.value = await plansApi.patch(plan.value.id, payload)
})
const saveStatus = computed(() => {
  if (saving.value) return '保存中…'
  if (savedAt.value) return `已保存 ${savedAt.value.toLocaleTimeString().slice(0, 5)}`
  return ''
})
const saveState = computed(() => saving.value ? 'saving' : 'saved')

function loadFromPlan(p: VideoPlan) {
  form.title = p.title
  form.summary = p.summary
  form.storyboard = (p.storyboard || []).map((s) => ({ ...s }))
  seriesId.value = p.series

  const c = (p.content as Record<string, any>) || {}
  contentDraft.positioning = c.positioning || ''
  contentDraft.highlights = Array.isArray(c.highlights) ? [...c.highlights] : []
  contentDraft.structure = {
    hook: c.structure?.hook || '',
    body: c.structure?.body || '',
    climax: c.structure?.climax || '',
    ending: c.structure?.ending || '',
  }
  contentDraft.subtitles = c.subtitles || ''
  contentDraft.music = c.music || ''
  contentDraft.publish_caption = c.publish_caption || ''
  contentDraft.cover_caption = c.cover_caption || ''

  editingDraft.steps = Array.isArray((p.editing_advice as any)?.steps)
    ? [...(p.editing_advice as any).steps]
    : []

  const ai = (p.ai_prompts as Record<string, string>) || {}
  aiPromptDraft.positive = ai.positive || ''
  aiPromptDraft.negative = ai.negative || ''
}

function buildPayload(): Partial<VideoPlan> {
  return {
    title: form.title,
    summary: form.summary,
    storyboard: form.storyboard,
    content: {
      positioning: contentDraft.positioning,
      highlights: contentDraft.highlights,
      structure: contentDraft.structure,
      subtitles: contentDraft.subtitles,
      music: contentDraft.music,
      publish_caption: contentDraft.publish_caption,
      cover_caption: contentDraft.cover_caption,
    },
    editing_advice: { steps: editingDraft.steps },
    ai_prompts: { positive: aiPromptDraft.positive, negative: aiPromptDraft.negative },
  }
}

function scheduleSave() { schedule(buildPayload()) }
function onTitleChange() { schedule(buildPayload()) }

function addShot() {
  form.storyboard.push({
    idx: form.storyboard.length + 1,
    duration: 3,
    visual: '',
    line: '',
    editing: '',
    ai_prompt: '',
  })
  scheduleSave()
}
function removeShot(idx: number) {
  form.storyboard.splice(idx, 1)
  scheduleSave()
}

async function onOptimize(scope: OptimizeScope) {
  if (!plan.value) return
  await flush()
  optimizing.value = true
  optimizeTaskMessage.value = 'AI 正在优化方案…'
  optimizeTaskProgress.value = 10
  try {
    const updated = await plansApi.optimize(plan.value.id, scope)
    if (isAITaskResponse(updated)) {
      saveActiveAITask({
        taskId: updated.id,
        taskType: 'optimize_plan',
        label: '优化方案',
        targetId: plan.value.id,
        createdAt: new Date().toISOString(),
      })
      await followOptimizeTask(updated, plan.value.id)
      return
    }
    plan.value = updated
    loadFromPlan(updated)
    ElMessage.success('AI 优化完成')
  } finally {
    optimizing.value = false
  }
}

async function onConfirm() {
  if (!plan.value) return
  await flush()
  plan.value = await plansApi.patch(plan.value.id, { status: 'confirmed' })
  ElMessage.success('已保存为已确认方案')
  router.push('/app/me/plans')
}

async function load() {
  loading.value = true
  try {
    const [planResp, seriesResp] = await Promise.all([
      plansApi.get(route.params.id as string),
      seriesApi.list().catch(() => ({ count: 0, next: null, previous: null, results: [] })),
    ])
    seriesOptions.value = seriesResp.results
    plan.value = planResp
    loadFromPlan(planResp)
    resumeOptimizeTask(planResp.id)
  } finally {
    loading.value = false
  }
}

async function onSeriesChange(value: string | null) {
  if (!plan.value) return
  await flush()
  plan.value = await plansApi.patch(plan.value.id, { series: value })
  ElMessage.success(value ? '已关联到系列' : '已取消系列关联')
}

watch(() => route.params.id, load, { immediate: true })
onBeforeUnmount(() => {
  optimizeAbortController?.abort()
  void flush()
})

async function followOptimizeTask(task: AITask, planId: string) {
  optimizeAbortController?.abort()
  optimizeAbortController = new AbortController()
  optimizeTaskProgress.value = Math.max(task.progress || 0, 10)
  optimizeTaskMessage.value = task.status === 'queued' ? 'AI 优化任务已排队…' : 'AI 正在优化方案…'
  try {
    await waitForAITask(task.id, {
      signal: optimizeAbortController.signal,
      onUpdate: (latest) => {
        optimizeTaskProgress.value = Math.max(latest.progress || 0, 10)
        optimizeTaskMessage.value = latest.status === 'queued' ? 'AI 优化任务已排队…' : 'AI 正在优化方案…'
      },
    })
    removeActiveAITask(task.id)
    const updated = await plansApi.get(planId)
    plan.value = updated
    loadFromPlan(updated)
    ElMessage.success('AI 优化完成')
  } catch (err) {
    if (!isAbortError(err)) {
      removeActiveAITask(task.id)
      ElMessage.error(err instanceof Error ? err.message : 'AI 优化失败')
    }
  } finally {
    optimizing.value = false
    optimizeTaskMessage.value = ''
    optimizeTaskProgress.value = 0
  }
}

function resumeOptimizeTask(planId: string) {
  const active = findActiveAITask('optimize_plan', (task) => task.targetId === planId)
  if (!active || optimizing.value) return
  optimizing.value = true
  void followOptimizeTask({
    id: active.taskId,
    task_type: active.taskType,
    task_type_label: active.label,
    status: 'queued',
    status_label: '排队中',
    title: active.label,
    progress: 0,
    input_payload: { plan_id: planId },
    result_payload: {},
    error: '',
    started_at: null,
    finished_at: null,
    created_at: active.createdAt,
    updated_at: active.createdAt,
  }, planId)
}

function isAbortError(err: unknown) {
  return err instanceof DOMException && err.name === 'AbortError'
}
</script>

<style scoped>
.editor { padding: 24px 32px 36px; max-width: 1360px; margin: 0 auto; }
.head {
  display: flex; justify-content: space-between; gap: 16px;
  align-items: flex-start;
  margin-bottom: 20px;
  padding: 12px 0 16px;
  border-bottom: 1px solid var(--vp-divider);
  position: sticky;
  top: var(--vp-topbar-h);
  z-index: 8;
  background: color-mix(in srgb, var(--vp-bg) 92%, transparent);
  backdrop-filter: blur(12px);
}
.title-input { padding: 0; }
.title-input :deep(.el-input__wrapper) {
  box-shadow: none !important;
  background: transparent !important;
  padding: 0;
}
.title-input :deep(.el-input__wrapper):hover { box-shadow: none !important; }
.title-input :deep(.el-input__wrapper).is-focus {
  box-shadow: 0 0 0 1px var(--vp-border-strong) inset !important;
  background: var(--vp-surface) !important;
  border-radius: var(--vp-r-sm);
}
.title-input :deep(.el-input__inner) {
  font-size: 22px; font-weight: 600;
  color: var(--vp-text-1);
  letter-spacing: 0;
  padding: 0 4px;
  height: 32px;
}
.meta {
  display: flex; align-items: center; gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
  font-size: 12.5px;
}
.head-actions { display: flex; gap: 8px; align-items: center; }
.task-alert { margin-bottom: 16px; }
.task-title { display: flex; align-items: center; gap: 12px; width: 100%; }
.task-progress { width: 220px; }
.muted { color: var(--vp-text-3); font-size: 12.5px; }
.body { margin-top: 8px; }
.editor-grid {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) 360px;
  gap: 16px;
  align-items: start;
}
.editor-main,
.editor-side,
.editor-outline {
  min-width: 0;
}
.editor-outline {
  position: sticky;
  top: calc(var(--vp-topbar-h) + 78px);
}
.editor-side {
  position: sticky;
  top: calc(var(--vp-topbar-h) + 78px);
}
.outline-card {
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-lg);
  background: var(--vp-surface);
  padding: 16px;
}
.outline-kicker {
  display: block;
  color: var(--vp-text-3);
  font-size: 11.5px;
  font-weight: 700;
  margin-bottom: 8px;
}
.outline-card > strong {
  display: block;
  color: var(--vp-text-1);
  font-size: 18px;
  font-weight: 720;
  margin-bottom: 8px;
}
.outline-card > p {
  color: var(--vp-text-3);
  font-size: 12.5px;
  line-height: 1.55;
}
.outline-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin: 16px 0;
}
.outline-metrics div {
  padding: 10px;
  border-radius: var(--vp-r-md);
  background: var(--vp-surface-alt);
}
.outline-metrics span {
  display: block;
  color: var(--vp-text-3);
  font-size: 11.5px;
  margin-bottom: 4px;
}
.outline-metrics b {
  color: var(--vp-text-1);
  font-size: 16px;
}
.outline-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 12px;
  border-top: 1px solid var(--vp-divider);
}
.outline-nav a {
  min-height: 30px;
  display: flex;
  align-items: center;
  padding: 0 10px;
  border-radius: var(--vp-r-sm);
  color: var(--vp-text-2);
  font-size: 12.5px;
  font-weight: 500;
  text-decoration: none;
  position: relative;
  transition: background .12s ease, color .12s ease, padding-left .12s ease;
}
.outline-nav a::before {
  content: "";
  width: 4px; height: 4px;
  border-radius: 50%;
  background: var(--vp-text-4);
  margin-right: 10px;
  transition: background .12s ease, transform .12s ease;
}
.outline-nav a:hover {
  background: var(--vp-primary-soft);
  color: var(--vp-primary);
  padding-left: 12px;
}
.outline-nav a:hover::before { background: var(--vp-primary); transform: scale(1.4); }
.editor-section {
  scroll-margin-top: calc(var(--vp-topbar-h) + 86px);
}
.mt { margin-top: 16px; }
.mt-sm { margin-top: 8px; }
.card-header-row {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 14px; font-weight: 600;
}
.shot {
  padding: 14px;
  background: var(--vp-surface-alt);
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-md);
  margin-bottom: 10px;
  transition: border-color .15s ease, box-shadow .15s ease, background .15s ease;
}
.shot:hover {
  border-color: var(--vp-border-strong);
  background: var(--vp-surface);
  box-shadow: var(--vp-shadow-xs);
}
.shot:last-child { margin-bottom: 0; }
.shot-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.shot-head strong { font-size: 13px; color: var(--vp-text-2); font-weight: 600; }
.shot-control { display: flex; align-items: center; gap: 6px; color: var(--vp-text-3); font-size: 12.5px; }
.series-select { width: 200px; }

.save-pill {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 12px;
  color: var(--vp-text-3);
  padding: 2px 10px;
  border-radius: var(--vp-r-pill);
  background: var(--vp-surface-alt);
  border: 1px solid var(--vp-divider);
  user-select: none;
}
.save-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--vp-text-4);
}
.save-pill[data-state="saving"] {
  color: var(--vp-warning);
  background: var(--vp-warning-soft);
  border-color: transparent;
}
.save-pill[data-state="saving"] .save-dot {
  background: var(--vp-warning);
  animation: vp-pulse 1.2s ease-in-out infinite;
}
.save-pill[data-state="saved"] {
  color: var(--vp-success);
  background: var(--vp-success-soft);
  border-color: transparent;
}
.save-pill[data-state="saved"] .save-dot { background: var(--vp-success); }

@media (max-width: 1100px) {
  .editor-grid { grid-template-columns: minmax(0, 1fr) 340px; }
  .editor-outline { display: none; }
  .editor-side { position: static; }
}

@media (max-width: 720px) {
  .editor { padding: 18px 16px 28px; }
  .head {
    position: static;
    flex-direction: column;
    align-items: stretch;
  }
  .editor-grid { grid-template-columns: 1fr; }
  .head-actions {
    flex-wrap: wrap;
  }
  .head-actions > * {
    flex: 1 1 auto;
  }
  .series-select { width: 100%; }
  .shot-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }
  .shot-control { width: 100%; flex-wrap: wrap; }
}
</style>
