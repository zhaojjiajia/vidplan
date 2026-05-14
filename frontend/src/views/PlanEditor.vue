<template>
  <div class="editor-page" v-loading="loading && !plan">
    <template v-if="plan">
      <!-- 顶部工具栏只放状态和操作，不承载正文编辑内容。 -->
      <header class="doc-toolbar">
        <div class="dt-left">
          <el-button text :icon="ArrowLeft" @click="backFromToolbar">返回</el-button>
          <span class="dt-divider" />
          <span class="dt-status" :data-tone="statusTone">{{ statusLabel || '草稿' }}</span>
          <span v-if="saveStatus" class="dt-save" :data-state="saveState">
            <span class="dt-save-dot" />
            {{ saveStatus }}
          </span>
        </div>
        <div class="dt-right">
          <el-button class="dt-series-btn" :icon="Connection" @click="openSeriesDialog">
            关联系列
          </el-button>
          <el-button
            class="dt-confirm-btn"
            :type="plan.status === 'confirmed' ? 'success' : 'primary'"
            :icon="Check"
            :loading="confirming"
            :disabled="plan.status === 'confirmed'"
            @click="onConfirm"
          >
            <span class="dt-btn-label">{{ plan.status === 'confirmed' ? '已确认' : '确认方案' }}</span>
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
          </div>
        </template>
      </el-alert>

      <!-- 中央单列文档编辑区。 -->
      <div class="doc-wrap">
        <article class="doc">
          <div class="doc-head">
            <input
              v-model="form.title"
              class="doc-title"
              placeholder="给方案起个标题"
              @input="onTitleChange"
            />
            <textarea
              v-model="form.summary"
              class="doc-summary-input"
              rows="2"
              placeholder="一句话简介"
              @input="scheduleSave"
            />
          </div>

          <CollapsibleSection
            :title="`章节脚本 · ${form.sections.length} 章`"
            :subtitle="storyboardSubtitle"
            :open="sections.storyboard"
            anchor-id="storyboard"
            @update:open="(v) => (sections.storyboard = v)"
          >
            <template #actions>
              <el-button text size="small" :icon="Plus" @click="addSection">添加章节</el-button>
              <el-button v-if="flatStoryboard.length" text size="small" @click="expandAllShots">全部展开</el-button>
              <el-button v-if="flatStoryboard.length" text size="small" @click="collapseAllShots">全部收起</el-button>
              <el-popover
                v-model:visible="regenPopoverOpen"
                :width="320"
                trigger="manual"
                placement="bottom-end"
              >
                <template #reference>
                  <el-button text size="small" @click="regenPopoverOpen = !regenPopoverOpen">重新生成</el-button>
                </template>
                <div class="regen-popover">
                  <p class="regen-hint">让 AI 把所有分镜重写一遍。可选写一句你想要的方向(节奏更快 / 加冲突 / ...)</p>
                  <el-input
                    v-model="regenHint"
                    type="textarea"
                    :rows="3"
                    placeholder="例如:节奏再快一点,每镜更短"
                  />
                  <div class="regen-actions">
                    <el-button text size="small" @click="regenPopoverOpen = false">取消</el-button>
                    <el-button
                      type="primary"
                      size="small"
                      :loading="regenLoading"
                      @click="onRegenerateStoryboard"
                    >
                      生成
                    </el-button>
                  </div>
                </div>
              </el-popover>
            </template>
            <div v-if="form.sections.length === 0" class="empty-state">
              <p>暂无章节,可让 AI 生成或手动添加。</p>
              <el-button type="primary" :icon="Plus" @click="addSection">添加第一个章节</el-button>
            </div>
            <div v-else class="plan-sections">
              <section v-for="(section, sectionIdx) in form.sections" :key="section._uiKey" class="plan-section">
                <header class="plan-section-head">
                  <div class="plan-section-main">
                    <input
                      v-model="section.title"
                      class="section-title-input"
                      :placeholder="`章节 ${sectionIdx + 1}`"
                      @input="scheduleSave"
                    />
                    <textarea
                      v-model="section.summary"
                      class="section-summary-input"
                      rows="1"
                      placeholder="这一章要完成什么"
                      @input="onSectionSummaryInput"
                    />
                  </div>
                  <div class="plan-section-tools">
                    <el-button text size="small" :icon="ArrowUp" :disabled="sectionIdx === 0" title="上移章节" @click="moveSection(sectionIdx, -1)" />
                    <el-button text size="small" :icon="ArrowDown" :disabled="sectionIdx === form.sections.length - 1" title="下移章节" @click="moveSection(sectionIdx, 1)" />
                    <el-button text size="small" type="danger" :icon="Delete" title="删除章节" @click="removeSection(sectionIdx)" />
                  </div>
                </header>

                <div class="section-shot-heading">
                  <button type="button" class="section-shot-toggle" @click="toggleSectionStoryboard(section)">
                    <el-icon :class="{ open: isSectionStoryboardOpen(section) }"><ArrowDown /></el-icon>
                    <span>分镜脚本</span>
                  </button>
                  <el-button
                    text
                    size="small"
                    :icon="MagicStick"
                    :loading="sectionGeneratingKey === section._uiKey"
                    @click="generateSectionStoryboard(sectionIdx)"
                  >
                    AI 生成本章分镜
                  </el-button>
                </div>

                <div v-if="isSectionStoryboardOpen(section)">
                  <div v-if="section.storyboard.length === 0" class="section-empty">
                    <span>这一章暂无镜头</span>
                    <el-button text size="small" :icon="Plus" @click="addShotAt(sectionIdx, 0)">添加镜头</el-button>
                  </div>
                  <div v-else class="shots">
                    <ShotInsertSlot :position="1" @click="addShotAt(sectionIdx, 0)" />
                    <template v-for="(shot, shotIdx) in section.storyboard" :key="shot._uiKey">
                      <StoryboardShotCard
                        :plan-id="plan.id"
                        :index="globalShotIndex(sectionIdx, shotIdx)"
                        :shot="shot"
                        :expanded="!!shotExpanded[shot._uiKey]"
                        @toggle="(v: boolean) => (shotExpanded[shot._uiKey] = v)"
                        @update="(field, value) => onShotUpdate(sectionIdx, shotIdx, field, value)"
                        @remove="removeShot(sectionIdx, shotIdx)"
                        @rewrite="applyRewrite"
                        @register-rewrite-ref="bindRewriteRef"
                      />
                      <ShotInsertSlot :position="shotIdx + 2" @click="addShotAt(sectionIdx, shotIdx + 1)" />
                    </template>
                  </div>
                </div>
              </section>
            </div>
          </CollapsibleSection>

          <CollapsibleSection
            title="交付准备"
            subtitle="字幕 / 音乐 / 发布文案 / 封面字"
            :open="sections.delivery"
            anchor-id="delivery"
            @update:open="(v) => (sections.delivery = v)"
          >
            <el-form label-position="top" class="doc-form">
              <el-form-item label="字幕样式建议">
                <el-input
                  v-model="contentDraft.subtitles"
                  type="textarea"
                  :autosize="{ minRows: 1 }"
                  @input="scheduleSave"
                />
              </el-form-item>
              <el-form-item label="音乐建议">
                <el-input
                  v-model="contentDraft.music"
                  type="textarea"
                  :autosize="{ minRows: 1 }"
                  @input="scheduleSave"
                />
              </el-form-item>
              <el-form-item label="发布文案">
                <el-input
                  v-model="contentDraft.publish_caption"
                  type="textarea"
                  :autosize="{ minRows: 2 }"
                  @input="scheduleSave"
                />
              </el-form-item>
              <el-form-item label="封面文案">
                <el-input
                  v-model="contentDraft.cover_caption"
                  type="textarea"
                  :autosize="{ minRows: 1 }"
                  @input="scheduleSave"
                />
              </el-form-item>
            </el-form>
          </CollapsibleSection>

          <CollapsibleSection
            title="剪辑建议"
            subtitle="每行一条剪辑提示"
            :open="sections.editing"
            @update:open="(v) => (sections.editing = v)"
          >
            <el-input
              v-model="editingText"
              type="textarea"
              :autosize="{ minRows: 3 }"
              placeholder="每行一条建议"
              @input="scheduleSave"
            />
          </CollapsibleSection>

          <!-- 仅在已有内容时展示 AI 生成提示词，避免大多数方案出现空段落。 -->
          <CollapsibleSection
            v-if="aiPromptDraft.positive || aiPromptDraft.negative"
            title="AI 生成提示词"
            subtitle="正向 / 负向"
            :open="sections.ai_prompts"
            @update:open="(v) => (sections.ai_prompts = v)"
          >
            <el-form label-position="top" class="doc-form">
              <el-form-item label="正向提示词">
                <el-input v-model="aiPromptDraft.positive" type="textarea" :rows="3" @input="scheduleSave" />
              </el-form-item>
              <el-form-item label="负向提示词">
                <el-input v-model="aiPromptDraft.negative" type="textarea" :rows="2" @input="scheduleSave" />
              </el-form-item>
            </el-form>
          </CollapsibleSection>
        </article>
      </div>

      <el-dialog
        v-model="seriesDialogOpen"
        title="关联系列"
        width="460px"
        :close-on-click-modal="false"
      >
        <el-form label-position="top" class="props-form">
          <el-form-item label="关联系列">
            <el-select
              :model-value="seriesId"
              placeholder="未关联系列"
              clearable
              filterable
              style="width: 100%"
              @update:model-value="onSeriesChange"
            >
              <el-option v-for="s in seriesOptions" :key="s.id" :label="s.title" :value="s.id" />
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="seriesDialogOpen = false">关闭</el-button>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, ArrowLeft, ArrowUp, Check, Connection, Delete, MagicStick, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import CollapsibleSection from '@/components/CollapsibleSection.vue'
import ShotInsertSlot from '@/components/ShotInsertSlot.vue'
import StoryboardShotCard from '@/components/StoryboardShotCard.vue'
import { isAITaskResponse } from '@/api/aiTasks'
import { plansApi, type OptimizeScope } from '@/api/plans'
import { seriesApi } from '@/api/series'
import { findDirectionLabel } from '@/data/directions'
import { useDebouncedSave } from '@/composables/useDebouncedSave'
import type { AITask, PlanSection, SeriesPlan, StoryboardShot, VideoPlan } from '@/types/api'

/** 客户端专用的分镜 key，用于在插入、删除、重排时稳定追踪分镜状态；保存前会剥离。 */
type ShotWithKey = StoryboardShot & { _uiKey: string }
type PlanSectionWithKey = {
  _uiKey: string
  title: string
  summary: string
  duration: number | string
  storyboard: ShotWithKey[]
}
let _uidCounter = 0
function nextUiKey(): string {
  _uidCounter += 1
  return `s${Date.now().toString(36)}-${_uidCounter}`
}
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
  storyboard: [] as ShotWithKey[],
  sections: [] as PlanSectionWithKey[],
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

// 方案级元数据保留在独立草稿中,避免保存正文时丢失这些字段。
const propsDraft = reactive({
  target_platform: '',
  target_audience: '',
  duration_seconds: 30,
  style: '',
})

// 单个分镜的展开状态，用 _uiKey 作为键，避免插入或重排后状态错位。
const shotExpanded = reactive<Record<string, boolean>>({})
const sectionStoryboardOpen = reactive<Record<string, boolean>>({})
const sectionGeneratingKey = ref('')

// 文档分段的折叠状态。正文只默认展开分镜，其他内容由用户按需打开。
// structure 在新版界面不再单独展示，但继续透传旧数据，避免保存时丢失。
const sections = reactive({
  storyboard: true,
  delivery: false,
  editing: false,
  ai_prompts: false,
})

const seriesDialogOpen = ref(false)
const confirming = ref(false)

function openSeriesDialog() {
  seriesDialogOpen.value = true
}

function backFromToolbar() {
  const sid = plan.value?.series
  router.push(sid ? `/app/series/${sid}` : '/app/me/plans')
}

// 按 path 记录分镜卡片里的重写入口，便于子组件注册和释放。
type RewriteAPI = { open: (opts?: { hint?: string; autoRun?: boolean }) => void; close: () => void }
const rewriteRefs = ref<Record<string, RewriteAPI>>({})

function bindRewriteRef(path: string, el: unknown) {
  const api = el as RewriteAPI | null
  if (api && typeof api.open === 'function') {
    rewriteRefs.value[path] = api
  } else {
    delete rewriteRefs.value[path]
  }
}

function flattenSections(): ShotWithKey[] {
  return form.sections.flatMap((section) => section.storyboard)
}

const flatStoryboard = computed(() => flattenSections())

function shotLocationByGlobalIndex(index: number): { sectionIdx: number; shotIdx: number; shot: ShotWithKey } | null {
  let cursor = 0
  for (let sectionIdx = 0; sectionIdx < form.sections.length; sectionIdx += 1) {
    const section = form.sections[sectionIdx]
    const next = cursor + section.storyboard.length
    if (index >= cursor && index < next) {
      const shotIdx = index - cursor
      return { sectionIdx, shotIdx, shot: section.storyboard[shotIdx] }
    }
    cursor = next
  }
  return null
}

function applyRewrite(path: string, value: string) {
  if (path === 'title') {
    form.title = value
  } else if (path === 'summary') {
    form.summary = value
  } else if (path.startsWith('content.structure.')) {
    const key = path.split('.').pop() as keyof typeof contentDraft.structure
    contentDraft.structure[key] = value
  } else if (path === 'content.positioning') {
    contentDraft.positioning = value
  } else if (path === 'content.subtitles') {
    contentDraft.subtitles = value
  } else if (path === 'content.music') {
    contentDraft.music = value
  } else if (path === 'content.publish_caption') {
    contentDraft.publish_caption = value
  } else if (path === 'content.cover_caption') {
    contentDraft.cover_caption = value
  } else {
    const m = path.match(/^storyboard\[(\d+)\]\.(\w+)$/)
    if (m) {
      const idx = Number(m[1])
      const field = m[2] as keyof StoryboardShot
      const located = shotLocationByGlobalIndex(idx)
      if (located) {
        ;(located.shot as any)[field] = field === 'description' ? normalizeDescriptionFormat(value) : value
      }
    }
  }
  scheduleSave()
}

const editingText = computed({
  get: () => editingDraft.steps.join('\n'),
  set: (v) => {
    editingDraft.steps = v.split('\n').map((s) => s.trim()).filter(Boolean)
  },
})
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

/**
 * 将旧版多字段分镜迁移为新版单 description 结构。
 * 老方案会保留原字段，同时把可读内容拼进 description，后续以 description 为编辑主入口。
 */
/**
 * 给 description 中的画面、台词、剪辑等段落补换行；已有换行的内容保持原样。
 */
function normalizeCjkSpacing(text: string): string {
  let normalized = text.replace(/\r\n?/g, '\n')
  let prev = ''
  // AI 偶尔会返回“画 面 ： 黑 屏”这种逐字空格，循环去掉中文字符之间的空格。
  while (normalized !== prev) {
    prev = normalized
    normalized = normalized.replace(/([\u3400-\u9fff\uf900-\ufaff])[\t \u00a0]+([\u3400-\u9fff\uf900-\ufaff])/g, '$1$2')
  }
  return normalized
    .replace(/([\u3400-\u9fff\uf900-\ufaff])[\t \u00a0]+([:：,，.。!！?？;；、/\\\-—）)》】\]”’])/g, '$1$2')
    .replace(/([\u3400-\u9fff\uf900-\ufaff])([:：,，.。!！?？;；、/\\\-—])[\t \u00a0]+([\u3400-\u9fff\uf900-\ufaff])/g, '$1$2$3')
    .replace(/([（(《【\["“'‘])[\t \u00a0]+([\u3400-\u9fff\uf900-\ufaff])/g, '$1$2')
}

function normalizeDescriptionFormat(text: string): string {
  if (!text) return ''
  const cleaned = normalizeCjkSpacing(text)
  if (cleaned.includes('\n')) {
    return cleaned.replace(/\n{3,}/g, '\n\n').trim()
  }
  return cleaned
    // 在关键词标记前插入换行。
    .replace(/(\s*[。.;；])?\s*(画面|台词\s*\/\s*旁白|台词|旁白|剪辑|运镜|字幕)\s*[:：]/g, '\n$2：')
    // 展开旧结构里用分号分隔的内容。
    .replace(/[;；]\s*/g, '\n')
    .replace(/\n{2,}/g, '\n')
    .trim()
}

function parseDurationSeconds(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value) && value > 0) {
    return Math.round(value)
  }
  if (typeof value !== 'string') return null
  const text = value.trim()
  if (!text) return null

  const range = text.match(/(\d+(?:\.\d+)?)\s*(?:-|~|—|至|到)\s*(\d+(?:\.\d+)?)/)
  if (range) {
    const start = Number(range[1])
    const end = Number(range[2])
    if (Number.isFinite(start) && Number.isFinite(end)) {
      const seconds = Math.abs(end - start) || end
      return seconds > 0 ? Math.round(seconds) : null
    }
  }

  const firstNumber = text.match(/\d+(?:\.\d+)?/)
  if (!firstNumber) return null
  const seconds = Number(firstNumber[0])
  return Number.isFinite(seconds) && seconds > 0 ? Math.round(seconds) : null
}

function normalizeShotDuration(shot: StoryboardShot | Record<string, unknown>): number {
  const rawShot = shot as Record<string, unknown>
  const seconds = parseDurationSeconds(rawShot.duration)
    ?? parseDurationSeconds(rawShot.duration_seconds)
    ?? parseDurationSeconds(rawShot.seconds)
    ?? parseDurationSeconds(rawShot.time)
  return Math.min(Math.max(seconds ?? 3, 1), 600)
}

function migrateShotToDescription(shot: StoryboardShot): StoryboardShot {
  if ((shot.description || '').trim()) {
    return {
      ...shot,
      duration: normalizeShotDuration(shot),
      description: normalizeDescriptionFormat(shot.description as string),
    }
  }
  const parts: string[] = []
  // visual 旧字段通常已经带主体、动作、表情等子标签，直接保留即可。
  // ai_prompt 属于生成模型提示词噪声，不拼入可读分镜描述。
  if (shot.visual?.trim()) parts.push(shot.visual.trim())
  if (shot.line?.trim()) parts.push(`台词:"${shot.line.trim()}"`)
  if (shot.editing?.trim()) parts.push(`剪辑:${shot.editing.trim()}`)

  return {
    ...shot,
    duration: normalizeShotDuration(shot),
    description: normalizeDescriptionFormat(parts.join('\n')),
  }
}

function shotWithKey(shot: StoryboardShot, idx: number): ShotWithKey {
  return {
    ...migrateShotToDescription(shot),
    idx: idx + 1,
    _uiKey: nextUiKey(),
  }
}

function normalizeSection(raw: PlanSection, idx: number, fallbackShots: StoryboardShot[] = []): PlanSectionWithKey {
  const rawShots = Array.isArray(raw.storyboard) ? raw.storyboard : fallbackShots
  return {
    _uiKey: nextUiKey(),
    title: (raw.title || raw.name || `章节 ${idx + 1}`).trim(),
    summary: (raw.summary || raw.goal || '').trim(),
    duration: raw.duration ?? '',
    storyboard: rawShots.map((shot, shotIdx) => shotWithKey(shot, shotIdx)),
  }
}

function buildFallbackSections(p: VideoPlan, content: Record<string, any>): PlanSectionWithKey[] {
  const shots = Array.isArray(p.storyboard) ? p.storyboard : []
  const structure = content.structure
  if (Array.isArray(structure) && structure.length) {
    const chunks = splitShots(shots, structure.length)
    return structure
      .filter((item: unknown) => item && typeof item === 'object')
      .map((item: any, idx: number) => normalizeSection(item, idx, chunks[idx] || []))
  }
  return [normalizeSection({
    title: '章节 1',
    summary: p.summary || '',
    duration: p.duration_seconds || '',
    storyboard: shots,
  }, 0)]
}

function splitShots(shots: StoryboardShot[], count: number): StoryboardShot[][] {
  if (count <= 0) return []
  const base = Math.floor(shots.length / count)
  const extra = shots.length % count
  const chunks: StoryboardShot[][] = []
  let cursor = 0
  for (let idx = 0; idx < count; idx += 1) {
    const size = base + (idx < extra ? 1 : 0)
    chunks.push(shots.slice(cursor, cursor + size))
    cursor += size
  }
  return chunks
}

function serializeSections() {
  let globalIdx = 1
  return form.sections.map((section) => ({
    title: section.title,
    summary: section.summary,
    duration: section.duration,
    storyboard: section.storyboard.map(({ _uiKey, ...shot }) => ({
      ...shot,
      duration: normalizeShotDuration(shot),
      description: normalizeDescriptionFormat(shot.description || ''),
      idx: globalIdx++,
    })),
  }))
}

function loadFromPlan(p: VideoPlan) {
  form.title = p.title
  form.summary = p.summary
  const c = (p.content as Record<string, any>) || {}
  const rawSections = Array.isArray(c.sections) ? c.sections : []
  form.sections = rawSections.length
    ? rawSections.map((section: PlanSection, idx: number) => normalizeSection(section, idx))
    : buildFallbackSections(p, c)
  form.storyboard = flattenSections()
  // 重新加载后旧 key 失效，展开状态也一起重置。
  for (const k of Object.keys(shotExpanded)) delete shotExpanded[k]
  for (const k of Object.keys(sectionStoryboardOpen)) delete sectionStoryboardOpen[k]
  seriesId.value = p.series

  propsDraft.target_platform = p.target_platform || ''
  propsDraft.target_audience = p.target_audience || ''
  propsDraft.duration_seconds = p.duration_seconds || 30
  propsDraft.style = p.style || ''

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
  resizeAllSectionSummaryInputs()
}

function buildPayload(): Partial<VideoPlan> {
  const serializedSections = serializeSections()
  return {
    title: form.title,
    summary: form.summary,
    target_platform: propsDraft.target_platform,
    target_audience: propsDraft.target_audience,
    duration_seconds: propsDraft.duration_seconds,
    style: propsDraft.style,
    storyboard: serializedSections.flatMap((section) => section.storyboard),
    content: {
      positioning: contentDraft.positioning,
      highlights: contentDraft.highlights,
      structure: contentDraft.structure,
      sections: serializedSections,
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

function resizeTextareaToContent(el: HTMLTextAreaElement | null) {
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${el.scrollHeight}px`
}

function resizeAllSectionSummaryInputs() {
  void nextTick(() => {
    document
      .querySelectorAll<HTMLTextAreaElement>('.editor-page .section-summary-input')
      .forEach(resizeTextareaToContent)
  })
}

function onSectionSummaryInput(event: Event) {
  resizeTextareaToContent(event.target as HTMLTextAreaElement | null)
  scheduleSave()
}

/**
 * 在任意位置插入空分镜。新分镜默认展开，方便用户立即编辑。
 */
function addShotAt(sectionIdx: number, idx: number) {
  const section = form.sections[sectionIdx]
  if (!section) return
  const newShot: ShotWithKey = {
    _uiKey: nextUiKey(),
    idx: globalShotIndex(sectionIdx, idx),
    duration: 3,
    description: '',
  }
  section.storyboard.splice(idx, 0, newShot)
  form.storyboard = flattenSections()
  shotExpanded[newShot._uiKey] = true
  sectionStoryboardOpen[section._uiKey] = true
  // 从任意页面状态点击插入时，确保分镜区可见。
  sections.storyboard = true
  scheduleSave()
}

function removeShot(sectionIdx: number, idx: number) {
  const section = form.sections[sectionIdx]
  if (!section) return
  const removed = section.storyboard.splice(idx, 1)[0]
  if (removed) delete shotExpanded[removed._uiKey]
  form.storyboard = flattenSections()
  scheduleSave()
}

function onShotUpdate(sectionIdx: number, idx: number, field: keyof StoryboardShot, value: string | number) {
  const shot = form.sections[sectionIdx]?.storyboard[idx]
  if (!shot) return
  ;(shot as any)[field] = field === 'description' && typeof value === 'string'
    ? normalizeDescriptionFormat(value)
    : value
  form.storyboard = flattenSections()
  scheduleSave()
}

function addSection() {
  const section: PlanSectionWithKey = {
    _uiKey: nextUiKey(),
    title: `章节 ${form.sections.length + 1}`,
    summary: '',
    duration: '',
    storyboard: [],
  }
  form.sections.push(section)
  sectionStoryboardOpen[section._uiKey] = false
  sections.storyboard = true
  resizeAllSectionSummaryInputs()
  scheduleSave()
}

function removeSection(idx: number) {
  const removed = form.sections.splice(idx, 1)[0]
  if (removed) {
    for (const shot of removed.storyboard) delete shotExpanded[shot._uiKey]
  }
  if (!form.sections.length) addSection()
  form.storyboard = flattenSections()
  resizeAllSectionSummaryInputs()
  scheduleSave()
}

function moveSection(idx: number, delta: -1 | 1) {
  const target = idx + delta
  if (target < 0 || target >= form.sections.length) return
  const [item] = form.sections.splice(idx, 1)
  if (!item) return
  form.sections.splice(target, 0, item)
  form.storyboard = flattenSections()
  resizeAllSectionSummaryInputs()
  scheduleSave()
}

function isSectionStoryboardOpen(section: PlanSectionWithKey) {
  return !!sectionStoryboardOpen[section._uiKey]
}

function toggleSectionStoryboard(section: PlanSectionWithKey) {
  sectionStoryboardOpen[section._uiKey] = !sectionStoryboardOpen[section._uiKey]
}

function buildSectionStoryboardHint(sectionIdx: number) {
  const section = form.sections[sectionIdx]
  const allSections = form.sections
    .map((item, idx) => `${idx + 1}. ${item.title || `章节 ${idx + 1}`}: ${item.summary || '未填写'}`)
    .join('\n')
  return [
    `只为 content.sections[${sectionIdx}] 生成分镜脚本。`,
    `本章标题:${section?.title || `章节 ${sectionIdx + 1}`}`,
    `本章内容:${section?.summary || '未填写'}`,
    `全片章节结构:\n${allSections}`,
    '要求:结合本章内容和系列上下文生成当前章节的完整分镜脚本。每个分镜可以是一段可执行镜头组,不要按 3 秒短镜头硬拆。',
    '每个镜头 description 用三行:画面、台词/旁白、剪辑/运镜/字幕。',
    '不要改动其他章节的标题、摘要和 storyboard。返回 content.sections,并同步返回顶层 storyboard 扁平数组。',
  ].join('\n')
}

async function generateSectionStoryboard(sectionIdx: number) {
  if (!plan.value || sectionGeneratingKey.value) return
  const section = form.sections[sectionIdx]
  if (!section) return
  await flush()
  sectionGeneratingKey.value = section._uiKey
  try {
    const updated = await plansApi.optimize(plan.value.id, 'storyboard', {
      hint: buildSectionStoryboardHint(sectionIdx),
    })
    if (isAITaskResponse(updated)) {
      saveActiveAITask({
        taskId: updated.id,
        taskType: 'optimize_plan',
        label: '生成本章分镜',
        targetId: plan.value.id,
        createdAt: new Date().toISOString(),
      })
      await followOptimizeTask(updated, plan.value.id, { silent: true, successMessage: '本章分镜已生成' })
    } else {
      plan.value = updated
      loadFromPlan(updated)
      ElMessage.success('本章分镜已生成')
    }
    const refreshed = form.sections[sectionIdx]
    if (refreshed) sectionStoryboardOpen[refreshed._uiKey] = true
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || '生成本章分镜失败'
    ElMessage.error(String(detail))
  } finally {
    sectionGeneratingKey.value = ''
  }
}

function globalShotIndex(sectionIdx: number, shotIdx: number) {
  let index = shotIdx
  for (let i = 0; i < sectionIdx; i += 1) {
    index += form.sections[i]?.storyboard.length || 0
  }
  return index
}

function expandAllShots() {
  for (const section of form.sections) sectionStoryboardOpen[section._uiKey] = true
  for (const shot of flatStoryboard.value) shotExpanded[shot._uiKey] = true
}
function collapseAllShots() {
  for (const section of form.sections) sectionStoryboardOpen[section._uiKey] = false
  for (const shot of flatStoryboard.value) shotExpanded[shot._uiKey] = false
}

// --- 分镜重新生成：直接替换，不走候选确认 ---
const regenPopoverOpen = ref(false)
const regenHint = ref('')
const regenLoading = ref(false)

/**
 * 重新生成整段分镜，使用用户补充提示作为额外方向，成功后用服务端返回结果覆盖本地状态。
 */
async function onRegenerateStoryboard() {
  if (!plan.value || regenLoading.value) return
  await flush()
  regenLoading.value = true
  try {
    const updated = await plansApi.optimize(plan.value.id, 'storyboard', {
      hint: regenHint.value.trim(),
    })
    if (isAITaskResponse(updated)) {
      // 异步任务沿用现有优化任务恢复流程。
      saveActiveAITask({
        taskId: updated.id,
        taskType: 'optimize_plan',
        label: '重新生成分镜',
        targetId: plan.value.id,
        createdAt: new Date().toISOString(),
      })
      await followOptimizeTask(updated, plan.value.id)
    } else {
      plan.value = updated
      loadFromPlan(updated)
      ElMessage.success('分镜已重新生成')
    }
    regenPopoverOpen.value = false
    regenHint.value = ''
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || '重新生成失败'
    ElMessage.error(String(detail))
  } finally {
    regenLoading.value = false
  }
}

const storyboardSubtitle = computed(() => {
  if (!flatStoryboard.value.length) return '先写章节内容,分镜脚本可按章节单独生成'
  return '先按章节组织内容,再展开每章分镜脚本'
})


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
  if (!plan.value || confirming.value) return
  confirming.value = true
  try {
    await flush()
    plan.value = await plansApi.patch(plan.value.id, { status: 'confirmed' })
    ElMessage.success('已确认')
  } finally {
    confirming.value = false
  }
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
  const nextSeriesId = value || null
  await flush()
  plan.value = await plansApi.patch(plan.value.id, { series: nextSeriesId })
  seriesId.value = plan.value.series
  seriesDialogOpen.value = false
  ElMessage.success(nextSeriesId ? '已关联到系列' : '已取消系列关联')
}

watch(() => route.params.id, load, { immediate: true })
onBeforeUnmount(() => {
  optimizeAbortController?.abort()
  void flush()
})

async function followOptimizeTask(
  task: AITask,
  planId: string,
  options: { silent?: boolean; successMessage?: string } = {},
) {
  optimizeAbortController?.abort()
  optimizeAbortController = new AbortController()
  if (!options.silent) {
    optimizeTaskProgress.value = Math.max(task.progress || 0, 10)
    optimizeTaskMessage.value = task.status === 'queued' ? 'AI 优化任务已排队…' : 'AI 正在优化方案…'
  }
  try {
    await waitForAITask(task.id, {
      signal: optimizeAbortController.signal,
      onUpdate: (latest) => {
        if (!options.silent) {
          optimizeTaskProgress.value = Math.max(latest.progress || 0, 10)
          optimizeTaskMessage.value = latest.status === 'queued' ? 'AI 优化任务已排队…' : 'AI 正在优化方案…'
        }
      },
    })
    removeActiveAITask(task.id)
    const updated = await plansApi.get(planId)
    plan.value = updated
    loadFromPlan(updated)
    ElMessage.success(options.successMessage || 'AI 优化完成')
  } catch (err) {
    if (!isAbortError(err)) {
      removeActiveAITask(task.id)
      ElMessage.error(err instanceof Error ? err.message : 'AI 优化失败')
    }
  } finally {
    optimizing.value = false
    if (!options.silent) {
      optimizeTaskMessage.value = ''
      optimizeTaskProgress.value = 0
    }
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
/* 页面保持透明，让 App.vue 的花朵背景露出；正文区域自身负责可读性。 */
.editor-page { min-height: 100vh; background: transparent; }

/* ========== 顶部工具栏 ========== */
.doc-toolbar {
  position: sticky;
  top: var(--vp-topbar-h);
  z-index: 9;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 8px 24px;
  background: color-mix(in srgb, var(--vp-bg) 92%, transparent);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--vp-divider);
}
.dt-left, .dt-right {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.dt-left { flex: 0 1 auto; }
.dt-right { flex: 0 0 auto; }
.dt-divider {
  width: 1px;
  height: 16px;
  background: var(--vp-divider);
  flex-shrink: 0;
}
.dt-status {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  background: var(--vp-surface-alt);
  color: var(--vp-text-2);
  white-space: nowrap;
  flex-shrink: 0;
}
.dt-status[data-tone="warning"] {
  background: var(--vp-warning-soft, #fef3c7);
  color: var(--vp-warning, #92400e);
}
.dt-status[data-tone="success"] {
  background: var(--vp-success-soft, #d1fae5);
  color: var(--vp-success, #065f46);
}
.dt-save {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--vp-text-3);
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--vp-surface-alt);
  user-select: none;
  white-space: nowrap;
  flex-shrink: 0;
}
.dt-save-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--vp-text-4);
}
.dt-save[data-state="saving"] { color: var(--vp-warning); }
.dt-save[data-state="saving"] .dt-save-dot {
  background: var(--vp-warning);
  animation: vp-pulse 1.2s ease-in-out infinite;
}
.dt-save[data-state="saved"] { color: var(--vp-success); }
.dt-save[data-state="saved"] .dt-save-dot { background: var(--vp-success); }
.dt-btn {
  position: relative;
  flex-shrink: 0;
}
.dt-btn :deep(.el-icon) { margin-right: 4px; }
.dt-btn-label {
  white-space: nowrap;
}
/* 工具栏按钮文字不换行，避免窄屏时中文被挤成竖排。 */
.doc-toolbar :deep(.el-button) {
  white-space: nowrap;
  flex-shrink: 0;
}
.dt-primary-btn,
.dt-series-btn,
.dt-confirm-btn {
  flex-shrink: 0;
}
.dt-badge {
  position: absolute;
  top: 0;
  right: 0;
  min-width: 16px;
  height: 16px;
  border-radius: 8px;
  background: #ef4444;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
  padding: 0 4px;
  transform: translate(35%, -25%);
}

/* ========== 任务提示 ========== */
.task-alert { margin: 12px 24px 0; }
.task-title { display: flex; align-items: center; gap: 12px; width: 100%; }

/* ========== 文档主体 ========== */
.doc-wrap {
  padding: 32px 24px 96px;
  display: flex;
  justify-content: center;
}
.doc {
  width: 100%;
  max-width: 880px;
}

/* 标题区不使用卡片包裹，保持文档标题的观感。 */
.doc-head {
  margin-bottom: 28px;
}
.doc-title {
  border: none;
  outline: none;
  background: transparent;
  font-size: 30px;
  font-weight: 700;
  color: var(--vp-text-1, #1f2937);
  padding: 4px 0;
  letter-spacing: -0.01em;
  font-family: inherit;
  width: 100%;
}
.doc-title::placeholder { color: var(--vp-text-4, #d1d5db); font-weight: 600; }

.doc-summary-input {
  width: 100%;
  height: 54px;
  margin-top: 6px;
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  color: var(--vp-text-2);
  font: inherit;
  font-size: 17px;
  line-height: 1.65;
  padding: 0;
}
.doc-summary-input::placeholder {
  color: var(--vp-text-4, #d1d5db);
}
/* ========== 表单片段 ========== */
.doc-form :deep(.el-form-item) { margin-bottom: 18px; }
.doc-form :deep(.el-form-item:last-child) { margin-bottom: 0; }

.field-label-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  min-height: 24px;
  margin-bottom: 4px;
}
.field-label-text {
  display: flex;
  flex-direction: column;
  line-height: 1.35;
}
.field-label-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--vp-text-1);
}
.field-label-hint {
  font-size: 11.5px;
  color: var(--vp-text-3);
  margin-top: 2px;
}

.structure-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px 18px;
}
.structure-cell { display: flex; flex-direction: column; }
@media (max-width: 720px) {
  .structure-grid { grid-template-columns: 1fr; }
}

/* 重新生成弹层只保留输入框和生成按钮，不展示候选流。 */
.regen-popover {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.regen-hint {
  margin: 0;
  font-size: 12.5px;
  color: var(--vp-text-3, #9ca3af);
  line-height: 1.5;
}
.regen-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 32px 16px;
  border: 1px dashed var(--vp-border);
  border-radius: 10px;
  color: var(--vp-text-3);
  font-size: 13px;
}
.empty-state p { margin: 0; }

.shots {
  display: flex;
  flex-direction: column;
  gap: 0; /* ShotInsertSlot 自带间距。 */
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow: hidden;
  padding: 0 1px;
}
.plan-sections {
  display: grid;
  gap: 18px;
  max-width: 100%;
  min-width: 0;
}
.plan-section {
  padding: 16px 0 10px;
  border-top: 1px solid var(--vp-divider);
  max-width: 100%;
  min-width: 0;
  overflow: hidden;
}
.plan-section:first-child {
  border-top: none;
  padding-top: 0;
}
.plan-section-head {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 10px;
}
.plan-section-main {
  flex: 1;
  min-width: 0;
}
.section-title-input,
.section-summary-input {
  border: none;
  outline: none;
  background: transparent;
  font-family: inherit;
  color: var(--vp-text-1);
}
.section-title-input {
  width: 100%;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.4;
}
.section-summary-input {
  width: 100%;
  resize: none;
  overflow: hidden;
  color: var(--vp-text-2);
  font-size: 16px;
  line-height: 1.7;
  padding: 4px 0 0;
}
.plan-section-tools {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  flex-wrap: wrap;
  max-width: 320px;
}
.plan-section-tools :deep(.el-button + .el-button) {
  margin-left: 0;
}
.section-shot-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin: 2px 0 6px;
  min-width: 0;
}
.section-shot-toggle {
  border: none;
  background: transparent;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
  cursor: pointer;
  color: var(--vp-text-1);
  font-size: 14px;
  font-weight: 700;
}
.section-shot-toggle :deep(.el-icon) {
  color: var(--vp-text-3);
  transition: transform .15s;
}
.section-shot-toggle :deep(.el-icon.open) {
  transform: rotate(180deg);
}
.section-shot-heading :deep(.el-button) {
  margin-left: auto;
}
.section-shot-heading small {
  color: var(--vp-text-3);
  font-size: 12px;
}
.section-empty {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 44px;
  padding: 8px 0;
  color: var(--vp-text-3);
  font-size: 13px;
}

.props-form :deep(.el-form-item) { margin-bottom: 16px; }
.muted { color: var(--vp-text-3); font-size: 12.5px; }

@media (max-width: 720px) {
  .doc-wrap { padding: 20px 14px 80px; }
  .doc-toolbar { padding: 8px 14px; flex-wrap: wrap; }
  .dt-right { flex-wrap: wrap; }
  .plan-section-head {
    flex-direction: column;
  }
  .plan-section-tools {
    max-width: none;
    justify-content: flex-start;
  }
}
</style>

<!--
  CollapsibleSection 的 `.csec-body` 属于子组件作用域，这里用全局样式统一处理编辑区 textarea。
-->
<style>
/* 分镜、交付、剪辑、AI 提示词等正文编辑区使用无边框段落感。
   这里需要 !important 覆盖 Element Plus 后加载的 textarea box-shadow 边框。 */
.editor-page .csec .csec-body .el-textarea__inner {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  padding: 8px 0 !important;
  font-size: 16px !important;
  line-height: 1.78 !important;
  color: var(--vp-text-1, #1f2937);
  resize: none;
  font-family: inherit;
  /* autosize 会随内容撑高，隐藏偶发的 1-2px 计算误差滚动条。 */
  overflow-y: hidden !important;
}
.editor-page .csec .csec-body .el-textarea__inner:focus,
.editor-page .csec .csec-body .el-textarea__inner:hover {
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
}
.editor-page .csec .csec-body .el-textarea__inner:focus {
  background: rgba(0, 0, 0, .025) !important;
  border-radius: 4px;
}
.editor-page .csec .csec-body .el-textarea__inner::placeholder {
  color: var(--vp-text-4, #d1d5db);
  font-size: 14.5px;
}
.editor-page .csec .csec-body .el-form-item__label {
  font-size: 15.5px !important;
  color: var(--vp-text-1, #1f2937);
  font-weight: 600;
  padding-bottom: 6px !important;
  line-height: 1.5;
}
.editor-page .csec .csec-body .el-input__wrapper {
  box-shadow: 0 0 0 1px var(--vp-border, #e5e7eb) inset;
  background: transparent;
}
.editor-page .csec .csec-body .el-input__wrapper.is-focus {
  box-shadow: 0 0 0 1px var(--vp-primary, #4f46e5) inset;
}
.editor-page .csec,
.editor-page .csec .csec-body {
  max-width: 100%;
  min-width: 0;
  overflow: hidden;
}
</style>
