<template>
  <div class="vp-page vp-page--narrow wizard">
    <header class="head">
      <div>
        <h1>创建视频方案</h1>
        <p class="hint">花一两分钟回答几个问题,AI 帮你生成完整的方案草稿。</p>
      </div>
      <el-button text @click="$router.push('/app/me/plans')">返回方案列表</el-button>
    </header>

    <div class="wizard-shell">
      <aside class="wizard-rail">
        <div class="rail-card">
          <div class="rail-title">创建进度</div>
          <ol class="rail-steps">
            <li v-for="(item, index) in wizardSteps" :key="item" :class="{ active: step === index, done: step > index }">
              <span>{{ index + 1 }}</span>
              <strong>{{ item }}</strong>
            </li>
          </ol>
          <div class="rail-summary">
            <div>
              <span>方向</span>
              <strong>{{ selectedDirectionLabel }}</strong>
            </div>
            <div>
              <span>类型</span>
              <strong>{{ typeLabel }}</strong>
            </div>
            <div>
              <span>想法</span>
              <p>{{ ideaPreview }}</p>
            </div>
          </div>
        </div>
      </aside>

      <section class="card">
        <el-steps :active="step" finish-status="success" simple class="steps">
          <el-step title="选择方向" />
          <el-step title="选择类型" />
          <el-step title="填写想法" />
          <el-step title="AI 生成" />
        </el-steps>

        <div v-if="step === 0" class="step">
          <DirectionPicker
            v-model:category="picker.category"
            v-model:direction="picker.direction"
          />
          <div class="actions">
            <span />
            <el-button type="primary" :disabled="!picker.direction" @click="step = 1">
              下一步<el-icon class="el-icon--right"><ArrowRight /></el-icon>
            </el-button>
          </div>
        </div>

        <div v-else-if="step === 1" class="step">
          <h3>选择创作类型</h3>
          <p class="hint">单条方案适合独立短片,系列方案让人设、风格、栏目长期复用。</p>
          <div class="type-grid">
            <div
              :class="['type-card', { active: planType === 'single' }]"
              role="button" tabindex="0"
              @click="planType = 'single'"
              @keydown.enter.space.prevent="planType = 'single'"
            >
              <div class="type-icon"><el-icon><Document /></el-icon></div>
              <h4>单条视频方案</h4>
              <p class="hint">适合 Vlog、教程、口播、单条短片</p>
            </div>
            <div
              :class="['type-card', { active: planType === 'series' }]"
              role="button" tabindex="0"
              @click="planType = 'series'"
              @keydown.enter.space.prevent="planType = 'series'"
            >
              <div class="type-icon"><el-icon><Files /></el-icon></div>
              <h4>系列视频方案</h4>
              <p class="hint">适合短剧、IP 账号、栏目化连载内容</p>
            </div>
          </div>
          <div class="actions">
            <el-button @click="step = 0">上一步</el-button>
            <el-button type="primary" @click="onTypeNext">
              {{ planType === 'series' ? '创建系列方案' : '下一步' }}
              <el-icon class="el-icon--right"><ArrowRight /></el-icon>
            </el-button>
          </div>
        </div>

        <div v-else-if="step === 2" class="step">
          <h3>填写创作想法</h3>
          <p class="hint">想法描述越具体,AI 生成得越准。</p>
          <el-form :model="form" label-position="top" class="form">
            <el-form-item>
              <template #label>
                <span>想法描述</span>
                <span class="label-hint">或直接拖入Markdown 文件</span>
              </template>
              <div
                class="idea-drop"
                :class="{ dragging: ideaDragging }"
                @dragenter.prevent="ideaDragging = true"
                @dragover.prevent="ideaDragging = true"
                @dragleave="onIdeaDragLeave"
                @drop.prevent="onIdeaDrop"
              >
                <el-input
                  v-model="form.idea"
                  type="textarea"
                  :rows="5"
                  placeholder="例: 一条 30 秒的 AI 美女写真,西湖边漫步,秋天的氛围,温柔治愈感"
                />
                <div v-if="ideaDragging" class="drop-overlay">
                  <el-icon><Upload /></el-icon>
                  <span>松开即可导入</span>
                </div>
              </div>
            </el-form-item>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="目标平台">
                  <el-select v-model="form.target_platform" style="width:100%">
                    <el-option label="抖音" value="抖音" />
                    <el-option label="小红书" value="小红书" />
                    <el-option label="快手" value="快手" />
                    <el-option label="B 站" value="B站" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="时长 (秒)">
                  <el-input-number v-model="form.duration_seconds" :min="5" :max="600" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="目标观众">
                  <el-input v-model="form.target_audience" placeholder="例: 25-35 岁都市白领" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="内容风格">
                  <el-input v-model="form.style" placeholder="例: 治愈、悬疑、轻松搞笑" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item v-if="picker.category === 'real'">
              <el-checkbox v-model="form.is_ai_generated_video">本视频部分画面也需要 AI 生成</el-checkbox>
            </el-form-item>
          </el-form>
          <div class="actions">
            <el-button @click="step = 1">上一步</el-button>
            <el-button type="primary" :loading="generating" :disabled="!form.idea" @click="onGenerate">
              <el-icon class="el-icon--left"><MagicStick /></el-icon>
              AI 生成方案
            </el-button>
          </div>
        </div>

        <div v-else-if="step === 3" class="generating">
          <el-progress type="circle" :percentage="taskProgress" :width="120" :stroke-width="6" v-if="generating" />
          <p>{{ generating ? taskMessage : '生成完成,正在跳转编辑器…' }}</p>
          <p class="hint">可以放心切走,任务会在后台继续。</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, Document, Files, MagicStick, Upload } from '@element-plus/icons-vue'

import { isAITaskResponse } from '@/api/aiTasks'
import type { PlanMarkdownImportData } from '@/api/markdownImport'
import DirectionPicker from '@/components/DirectionPicker.vue'
import { plansApi } from '@/api/plans'
import { findDirectionLabel, type Category } from '@/data/directions'
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

const router = useRouter()

const step = ref(0)
const picker = reactive<{ category: Category | ''; direction: string }>({ category: '', direction: '' })
const planType = ref<'single' | 'series'>('single')
const wizardSteps = ['选择方向', '选择类型', '填写想法', 'AI 生成']

const form = reactive({
  idea: '',
  target_platform: '抖音',
  target_audience: '',
  duration_seconds: 30,
  style: '',
  is_ai_generated_video: false,
})

const generating = ref(false)
const ideaDragging = ref(false)
const taskProgress = ref(10)
const taskMessage = ref('AI 正在生成方案,通常 10-30 秒…')
let taskAbortController: AbortController | null = null

const selectedDirectionLabel = computed(() => picker.direction ? findDirectionLabel(picker.direction) : '未选择')
const typeLabel = computed(() => planType.value === 'series' ? '系列视频方案' : '单条视频方案')
const ideaPreview = computed(() => {
  const idea = form.idea.trim()
  return idea ? (idea.length > 52 ? `${idea.slice(0, 52)}…` : idea) : '未填写'
})

function onTypeNext() {
  if (planType.value === 'series') {
    router.push('/app/series/new')
    return
  }
  step.value = 2
}

function importPlanMarkdown(text: string, successMessage: string) {
  const local = parsePlanMarkdown(text)
  applyPlanImportValues(local)
  ElMessage.success(successMessage)
}

function parsePlanMarkdown(text: string): PlanMarkdownImportData {
  const plain = markdownToPlain(text)
  const idea = extractMarkdownValue(text, ['想法描述', '创作想法', '想法', '方案', '简介', '摘要', '内容'])
  const platform = extractMarkdownValue(text, ['目标平台', '平台', '发布平台'])
  const audience = extractMarkdownValue(text, ['目标观众', '目标受众', '受众', '观众'])
  const style = extractMarkdownValue(text, ['内容风格', '风格', '调性'])
  const duration = extractPlanDuration(text)

  return {
    idea: idea || plain,
    target_platform: platform ? normalizePlatform(platform) : '',
    target_audience: audience,
    duration_seconds: duration,
    style,
  }
}

function applyPlanImportValues(values: PlanMarkdownImportData) {
  if (values.idea) form.idea = values.idea
  if (values.target_platform) form.target_platform = normalizePlatform(values.target_platform)
  if (values.target_audience) form.target_audience = values.target_audience
  if (values.style) form.style = values.style
  if (values.duration_seconds) {
    form.duration_seconds = Math.min(600, Math.max(5, Math.round(values.duration_seconds)))
  }
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

function normalizePlatform(value: string) {
  if (/小红书/.test(value)) return '小红书'
  if (/抖音/.test(value)) return '抖音'
  if (/快手/.test(value)) return '快手'
  if (/B\s*站|bilibili/i.test(value)) return 'B站'
  return value.trim()
}

async function onGenerate() {
  if (!picker.category || !picker.direction) {
    ElMessage.warning('请回到第一步选择方向')
    return
  }
  generating.value = true
  taskProgress.value = 10
  taskMessage.value = 'AI 正在生成方案,通常 10-30 秒…'
  step.value = 3
  try {
    const result = await plansApi.generate({
      direction: picker.direction,
      category: picker.category,
      is_ai_generated_video: picker.category === 'ai_generated' ? true : form.is_ai_generated_video,
      idea: form.idea,
      target_platform: form.target_platform,
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
      await followGenerateTask(result)
      return
    }
    router.push(`/app/plan/${result.id}`)
  } catch {
    step.value = 2
  } finally {
    generating.value = false
  }
}

async function followGenerateTask(task: AITask) {
  taskAbortController?.abort()
  taskAbortController = new AbortController()
  taskProgress.value = Math.max(task.progress || 0, 10)
  taskMessage.value = task.status === 'queued' ? 'AI 任务已排队,正在等待执行…' : 'AI 正在生成方案…'
  try {
    const finished = await waitForAITask(task.id, {
      signal: taskAbortController.signal,
      onUpdate: (latest) => {
        taskProgress.value = Math.max(latest.progress || 0, 10)
        taskMessage.value = latest.status === 'queued' ? 'AI 任务已排队,正在等待执行…' : 'AI 正在生成方案…'
      },
    })
    removeActiveAITask(task.id)
    const planId = typeof finished.result_payload.plan_id === 'string' ? finished.result_payload.plan_id : ''
    if (!planId) throw new Error('AI 任务已完成,但未返回方案 ID')
    ElMessage.success('AI 生成完成')
    router.push(`/app/plan/${planId}`)
  } catch (err) {
    if (isAbortError(err)) return
    removeActiveAITask(task.id)
    ElMessage.error(err instanceof Error ? err.message : 'AI 生成失败')
    step.value = 2
  }
}

onMounted(async () => {
  const active = findActiveAITask('generate_plan')
  if (!active) return
  generating.value = true
  step.value = 3
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
  })
  generating.value = false
})

onBeforeUnmount(() => {
  taskAbortController?.abort()
})

function isAbortError(err: unknown) {
  return err instanceof DOMException && err.name === 'AbortError'
}
</script>

<style scoped>
.wizard { padding-top: 32px; max-width: 1120px; }
.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}
.head h1 { font-size: 26px; margin-bottom: 6px; }
.hint { color: var(--vp-text-3); font-size: 13.5px; line-height: 1.55; }

.wizard-shell {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}
.wizard-rail { position: sticky; top: 24px; }
.rail-card {
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-lg);
  background: var(--vp-surface);
  padding: 16px;
  box-shadow: var(--vp-shadow-xs);
}
.rail-title {
  color: var(--vp-text-1);
  font-size: 13px;
  font-weight: 650;
  margin-bottom: 12px;
}
.rail-steps {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0;
  margin: 0 0 16px;
}
.rail-steps li {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 32px;
  color: var(--vp-text-3);
}
.rail-steps span {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--vp-border);
  background: var(--vp-surface-alt);
  font-size: 12px;
  font-weight: 650;
  flex-shrink: 0;
}
.rail-steps strong { font-size: 13px; font-weight: 600; }
.rail-steps li.active,
.rail-steps li.done { color: var(--vp-primary); }
.rail-steps li.active span,
.rail-steps li.done span {
  border-color: var(--vp-primary);
  background: var(--vp-primary-soft);
}
.rail-summary {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px solid var(--vp-divider);
}
.rail-summary span {
  display: block;
  color: var(--vp-text-3);
  font-size: 12px;
  margin-bottom: 3px;
}
.rail-summary strong,
.rail-summary p {
  color: var(--vp-text-1);
  font-size: 13px;
  line-height: 1.45;
}
.steps { margin: 0 0 24px; }
:deep(.el-steps--simple) { background: transparent; padding: 0; }

.card {
  background: var(--vp-surface);
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-xl);
  padding: 28px;
  box-shadow: var(--vp-shadow-xs);
}

.step h3 { font-size: 18px; margin-bottom: 4px; }
.step .hint { margin-bottom: 18px; }

.type-grid { display: grid; gap: 12px; grid-template-columns: 1fr 1fr; margin: 18px 0; }
.type-card {
  cursor: pointer;
  background: var(--vp-surface);
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-lg);
  padding: 22px 20px;
  transition: border-color .15s ease, background .15s ease, transform .15s ease;
  position: relative;
}
.type-card:hover {
  border-color: var(--vp-border-strong);
  transform: translateY(-1px);
}
.type-card.active {
  border-color: var(--vp-primary);
  background: var(--vp-primary-soft);
  box-shadow: 0 0 0 1px var(--vp-primary) inset;
  transform: none;
}
.type-card.active::after {
  /* 选中右上角对勾 */
  content: "✓";
  position: absolute;
  top: 12px; right: 14px;
  width: 22px; height: 22px;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 50%;
  background: var(--vp-primary);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
}
.type-icon {
  width: 36px; height: 36px;
  border-radius: var(--vp-r-md);
  background: var(--vp-primary-soft); color: var(--vp-primary);
  display: inline-flex; align-items: center; justify-content: center;
  margin-bottom: 12px;
}
.type-card.active .type-icon { background: var(--vp-primary); color: #fff; }
.type-icon :deep(svg) { width: 18px; height: 18px; }
.type-card h4 { margin-bottom: 4px; font-size: 15px; }

.form { margin-top: 16px; }

.idea-drop {
  position: relative;
  width: 100%;
  padding: 8px;
  border: 1px dashed transparent;
  border-radius: var(--vp-r-md);
  transition: border-color .15s ease, background .15s ease;
}
.idea-drop.dragging {
  border-color: var(--vp-primary);
  background: var(--vp-primary-soft);
}
.drop-overlay {
  position: absolute;
  inset: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: var(--vp-r-sm);
  background: color-mix(in srgb, var(--vp-surface) 78%, var(--vp-primary-soft));
  color: var(--vp-primary);
  font-size: 16px;
  font-weight: 600;
  pointer-events: none;
}
.drop-overlay :deep(svg) {
  width: 18px;
  height: 18px;
}
.label-hint {
  margin-left: 8px;
  color: var(--vp-text-3);
  font-size: 14px;
  font-weight: 400;
}
.actions {
  margin-top: 28px;
  display: flex; justify-content: space-between; gap: 12px;
}

.generating {
  text-align: center; padding: 32px 0 16px;
  display: flex; flex-direction: column; align-items: center; gap: 16px;
}
.generating p { font-size: 14px; color: var(--vp-text-2); }
.generating .hint { font-size: 12.5px; }

@media (max-width: 720px) {
  .head { flex-direction: column; }
  .wizard-shell { grid-template-columns: 1fr; }
  .wizard-rail { position: static; }
  .type-grid { grid-template-columns: 1fr; }
  .card { padding: 20px; }
  .steps { display: none; }
  .form :deep(.el-col) {
    max-width: 100%;
    flex: 0 0 100%;
  }
}
</style>
