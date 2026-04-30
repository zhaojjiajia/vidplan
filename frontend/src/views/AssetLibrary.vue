<template>
  <div class="vp-page">
    <header class="vp-section-head">
      <div>
        <h2>{{ schema.title }}</h2>
        <p>{{ schema.desc }}</p>
      </div>
      <div class="header-actions">
        <el-input
          v-model="search"
          placeholder="按名称搜索"
          clearable
          :prefix-icon="Search"
          class="search"
          @input="onSearch"
        />
        <el-button type="primary" :icon="Plus" @click="openCreate">新建资产</el-button>
      </div>
    </header>

    <CardSkeleton v-if="loading && items.length === 0" variant="card" :count="6" />

    <EmptyState
      v-else-if="items.length === 0"
      :title="search ? '没有匹配的资产' : '还没有资产'"
      :description="search ? '调整搜索词后再试。' : '把可复用的人设、风格、栏目沉淀下来,后续每条方案都能直接用。'"
    >
      <template v-if="!search" #action>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建资产</el-button>
      </template>
    </EmptyState>

    <div v-else class="asset-grid">
      <article v-for="item in items" :key="item.id" class="asset-card">
        <header class="asset-card-head">
          <div>
            <h3>{{ item.name }}</h3>
            <p>{{ formatDate(item.updated_at) }}</p>
          </div>
          <span class="asset-badge">{{ schema.title }}</span>
        </header>

        <p class="asset-summary-text">{{ summarize(item) }}</p>

        <div class="trait-list" v-if="item.fixed_traits?.length">
          <el-tag v-for="trait in item.fixed_traits" :key="String(trait)" size="small" effect="plain" class="tag">
            {{ trait }}
          </el-tag>
        </div>
        <p v-else class="muted">暂无固定特征</p>

        <footer class="asset-card-actions">
          <el-button text type="primary" :icon="Edit" @click="openEdit(item)">编辑</el-button>
          <el-button text type="danger" :icon="Delete" @click="remove(item)">删除</el-button>
        </footer>
      </article>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑资产' : '新建资产'" width="720px">
      <el-form label-position="top">
        <div class="dialog-import">
          <el-upload
            accept=".md,text/markdown,text/plain"
            :auto-upload="false"
            :show-file-list="false"
            :on-change="onAssetMarkdownChange"
          >
            <el-button :icon="Upload" :loading="importingMarkdown">导入 Markdown</el-button>
          </el-upload>
          <span>AI 分析并解析为{{ schema.title }}</span>
        </div>

        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="例如: 女主小满 / 治愈写实风格" />
        </el-form-item>

        <el-form-item v-for="field in schema.fields" :key="field.key" :label="field.label">
          <el-input
            v-if="field.kind === 'text'"
            v-model="textValues[field.key]"
            :placeholder="field.placeholder"
          />
          <el-input
            v-else
            v-model="textValues[field.key]"
            type="textarea"
            :rows="field.kind === 'lines' ? 5 : 3"
            :placeholder="field.placeholder"
          />
        </el-form-item>

        <el-form-item label="固定特征 (每行一条)">
          <el-input
            v-model="fixedTraitsText"
            type="textarea"
            :rows="3"
            placeholder="发色&#10;性格&#10;口头禅"
          />
        </el-form-item>

        <el-collapse>
          <el-collapse-item title="高级:原始 JSON" name="advanced">
            <el-form-item label="详细配置 JSON">
              <el-input v-model="rawJson" type="textarea" :rows="8" />
              <div class="hint muted">编辑此处会覆盖上面字段;留空或保持自动同步即可。</div>
            </el-form-item>
          </el-collapse-item>
        </el-collapse>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Delete, Edit, Plus, Search, Upload } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type UploadFile } from 'element-plus'

import { assetsApi } from '@/api/assets'
import { markdownImportApi, type AssetMarkdownImportData } from '@/api/markdownImport'
import CardSkeleton from '@/components/CardSkeleton.vue'
import EmptyState from '@/components/EmptyState.vue'
import { ASSET_SCHEMAS, type AssetField } from '@/data/assetSchemas'
import type { AssetBase, AssetType } from '@/types/api'
import {
  cleanFieldLabel,
  extractMarkdownLines,
  extractMarkdownValue,
  firstMarkdownHeading,
  markdownToPlain,
} from '@/utils/markdownImport'

const route = useRoute()
const assetType = computed(() => route.meta.assetType as AssetType)
const schema = computed(() => ASSET_SCHEMAS[assetType.value])

const loading = ref(false)
const saving = ref(false)
const importingMarkdown = ref(false)
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const items = ref<AssetBase[]>([])

const search = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

const form = reactive({ name: '' })
const textValues = reactive<Record<string, string>>({})
const fixedTraitsList = ref<string[]>([])
const rawJson = ref('{}')

const fixedTraitsText = computed({
  get: () => fixedTraitsList.value.join('\n'),
  set: (v) => {
    fixedTraitsList.value = v.split('\n').map((s) => s.trim()).filter(Boolean)
  },
})

const ASSET_FIELD_ALIASES: Partial<Record<AssetType, Record<string, string[]>>> = {
  characters: {
    role: ['身份', '定位', '角色', '人设'],
    appearance: ['外形', '外貌', '服装', '形象'],
    personality: ['性格', '人格', '人物性格'],
    voice: ['声音', '语气', '口吻', '口头禅'],
  },
  styles: {
    visual: ['画面', '视觉', '画面风格'],
    editing: ['剪辑', '转场', '节奏'],
    music: ['音乐', '配乐', '音效'],
    color: ['色彩', '调色', '色调'],
  },
  worldviews: {
    background: ['背景', '故事背景', '世界设定'],
    rules: ['规则', '世界规则', '设定规则'],
    locations: ['地点', '关键地点', '场景'],
  },
  columns: {
    structure: ['结构', '固定结构', '栏目结构', '固定环节'],
    title_formula: ['标题', '标题套路', '标题公式'],
    cadence: ['节奏', '发布节奏', '更新频率'],
  },
}

onMounted(load)
watch(assetType, () => {
  search.value = ''
  load()
})

async function load() {
  loading.value = true
  try {
    const data = await assetsApi.list(assetType.value, {
      search: search.value || undefined,
      ordering: '-updated_at',
    })
    items.value = data.results
  } finally {
    loading.value = false
  }
}

function onSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 250)
}

function resetTextValues(payload: Record<string, unknown> = {}) {
  for (const key of Object.keys(textValues)) delete textValues[key]
  for (const f of schema.value.fields) {
    textValues[f.key] = fieldFromPayload(f, payload[f.key])
  }
}

function fieldFromPayload(field: AssetField, value: unknown): string {
  if (field.kind === 'lines') {
    if (Array.isArray(value)) return value.map((x) => String(x)).join('\n')
    if (typeof value === 'string') return value.split(/\n|[;；]/).map((s) => s.trim()).filter(Boolean).join('\n')
    return ''
  }
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.map((x) => String(x)).join('\n')
  if (value == null) return ''
  return JSON.stringify(value)
}

function buildPayloadFromFields(): Record<string, unknown> {
  const payload: Record<string, unknown> = {}
  for (const f of schema.value.fields) {
    const raw = textValues[f.key] ?? ''
    if (f.kind === 'lines') {
      payload[f.key] = raw.split('\n').map((s) => s.trim()).filter(Boolean)
    } else {
      payload[f.key] = raw
    }
  }
  return payload
}

function openCreate() {
  editingId.value = null
  form.name = ''
  resetTextValues()
  fixedTraitsList.value = []
  rawJson.value = JSON.stringify(buildPayloadFromFields(), null, 2)
  dialogVisible.value = true
}

function openEdit(item: AssetBase) {
  editingId.value = item.id
  form.name = item.name
  resetTextValues((item.payload as Record<string, unknown>) || {})
  fixedTraitsList.value = Array.isArray(item.fixed_traits)
    ? item.fixed_traits.map((x) => String(x))
    : []
  rawJson.value = JSON.stringify(item.payload || {}, null, 2)
  dialogVisible.value = true
}

async function onAssetMarkdownChange(file: UploadFile) {
  const text = await readUploadText(file)
  if (!text) {
    ElMessage.warning('未读取到 Markdown 内容')
    return
  }

  await importAssetMarkdown(text)
}

async function importAssetMarkdown(text: string) {
  importingMarkdown.value = true
  try {
    const local = parseAssetMarkdownLocally(text)
    const analyzed = await markdownImportApi.analyzeAsset(text, assetType.value, schema.value)
    if (analyzed.ok) {
      applyAssetImportResult(mergeAssetImport(local, analyzed.data))
      ElMessage.success(`AI 已分析并导入${schema.value.title}`)
      return
    }

    applyAssetImportResult(local)
    ElMessage.warning('AI 分析不可用,已使用本地解析')
  } catch {
    applyAssetImportResult(parseAssetMarkdownLocally(text))
    ElMessage.success(`已解析为${schema.value.title}`)
  } finally {
    importingMarkdown.value = false
  }
}

function parseAssetMarkdownLocally(text: string): AssetMarkdownImportData {
  const title = extractMarkdownValue(text, ['名称', '标题', '资产名称']) || firstMarkdownHeading(text)
  const payload: Record<string, unknown> = {}

  let filled = false
  for (const field of schema.value.fields) {
    const labels = getFieldLabels(field)
    if (field.kind === 'lines') {
      const lines = extractMarkdownLines(text, labels)
      if (lines.length) {
        payload[field.key] = lines
        filled = true
      }
      continue
    }

    const value = extractMarkdownValue(text, labels)
    if (value) {
      payload[field.key] = value
      filled = true
    }
  }

  const fixedTraits = extractMarkdownLines(text, ['固定特征', '固定特点', '不可变特征', '禁改特征'])

  if (!filled) {
    const fallbackField = schema.value.fields.find((field) => field.kind !== 'lines') || schema.value.fields[0]
    if (fallbackField) payload[fallbackField.key] = markdownToPlain(text)
  }

  return {
    name: title ? truncate(title.replace(/\n/g, ' '), 80) : '',
    payload,
    fixed_traits: fixedTraits,
  }
}

function mergeAssetImport(local: AssetMarkdownImportData, ai: AssetMarkdownImportData): AssetMarkdownImportData {
  const localPayload = filterAssetPayload(local.payload || {})
  const aiPayload = removeEmptyPayloadValues(filterAssetPayload(ai.payload || {}))
  const aiTraits = normalizeStringList(ai.fixed_traits)

  return {
    name: cleanImportString(ai.name) || local.name || '',
    payload: { ...localPayload, ...aiPayload },
    fixed_traits: aiTraits.length ? aiTraits : normalizeStringList(local.fixed_traits),
  }
}

function applyAssetImportResult(result: AssetMarkdownImportData) {
  const name = cleanImportString(result.name)
  if (name) form.name = truncate(name.replace(/\n/g, ' '), 80)

  const payload = filterAssetPayload(result.payload || {})
  for (const field of schema.value.fields) {
    if (Object.prototype.hasOwnProperty.call(payload, field.key)) {
      textValues[field.key] = fieldFromPayload(field, payload[field.key])
    }
  }

  const fixedTraits = normalizeStringList(result.fixed_traits)
  if (fixedTraits.length) fixedTraitsList.value = fixedTraits

  rawJson.value = JSON.stringify(buildPayloadFromFields(), null, 2)
}

async function readUploadText(file: UploadFile) {
  const raw = file.raw
  if (!raw) return ''
  return raw.text()
}

function getFieldLabels(field: AssetField) {
  const cleaned = cleanFieldLabel(field.label)
  const aliases = ASSET_FIELD_ALIASES[assetType.value]?.[field.key] || []
  return [...new Set([
    cleaned,
    ...cleaned.split(/\s+/),
    field.key,
    ...aliases,
  ].filter(Boolean))]
}

function filterAssetPayload(payload: Record<string, unknown>) {
  const allowed = new Set(schema.value.fields.map((field) => field.key))
  return Object.fromEntries(Object.entries(payload).filter(([key]) => allowed.has(key)))
}

function removeEmptyPayloadValues(payload: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(payload).filter(([, value]) => {
      if (Array.isArray(value)) return value.some((item) => cleanImportString(item))
      if (typeof value === 'string') return value.trim().length > 0
      if (value && typeof value === 'object') return Object.keys(value).length > 0
      return value != null
    })
  )
}

function normalizeStringList(value: unknown) {
  if (Array.isArray(value)) return value.map((item) => cleanImportString(item)).filter(Boolean)
  if (typeof value === 'string') {
    return value.split(/\n|[;；]/).map((item) => item.trim()).filter(Boolean)
  }
  return []
}

function cleanImportString(value: unknown) {
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return ''
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  let payload = buildPayloadFromFields()
  if (rawJson.value && rawJson.value.trim() !== JSON.stringify(payload, null, 2).trim()) {
    try {
      const advanced = JSON.parse(rawJson.value)
      if (advanced && typeof advanced === 'object' && !Array.isArray(advanced)) {
        payload = { ...payload, ...advanced }
      } else {
        ElMessage.error('原始 JSON 必须是对象')
        return
      }
    } catch {
      ElMessage.error('原始 JSON 解析失败')
      return
    }
  }

  saving.value = true
  try {
    const body = { name: form.name.trim(), payload, fixed_traits: [...fixedTraitsList.value] }
    if (editingId.value) {
      await assetsApi.patch(assetType.value, editingId.value, body)
      ElMessage.success('已更新资产')
    } else {
      await assetsApi.create(assetType.value, body)
      ElMessage.success('已创建资产')
    }
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function remove(item: AssetBase) {
  await ElMessageBox.confirm(`确认删除「${item.name}」?`, '删除资产', { type: 'warning' })
  await assetsApi.remove(assetType.value, item.id)
  ElMessage.success('已删除')
  await load()
}

function summarize(item: AssetBase): string {
  const payload = (item.payload as Record<string, unknown>) || {}
  for (const f of schema.value.fields) {
    const v = payload[f.key]
    if (typeof v === 'string' && v.trim()) return truncate(v, 80)
    if (Array.isArray(v) && v.length) return truncate(v.map((x) => String(x)).join(' / '), 80)
  }
  return '尚未填写'
}

function truncate(text: string, max: number) {
  return text.length > max ? `${text.slice(0, max)}…` : text
}

function formatDate(iso: string) {
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.header-actions { display: flex; gap: 10px; align-items: center; }
.search { width: 240px; }
.muted { color: var(--vp-text-3); font-size: 13px; }
.tag { margin-right: 6px; margin-bottom: 4px; }
.hint { margin-top: 4px; }
.dialog-import {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
  color: var(--vp-text-3);
  font-size: 16px;
}
.asset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(292px, 1fr));
  gap: 16px;
}
.asset-card {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-lg);
  background: var(--vp-surface);
  box-shadow: var(--vp-shadow-xs);
  transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease;
}
.asset-card:hover {
  border-color: var(--vp-border-strong);
  box-shadow: var(--vp-shadow-md);
  transform: translateY(-2px);
}
.asset-card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.asset-card-head h3 {
  margin: 0;
  color: var(--vp-text-1);
  font-size: 18px;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.asset-card-head p {
  margin-top: 4px;
  color: var(--vp-text-4);
  font-size: 12.5px;
}
.asset-badge {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: var(--vp-r-pill);
  background: var(--vp-primary-soft);
  color: var(--vp-primary);
  font-size: 12px;
  font-weight: 500;
}
.asset-summary-text {
  color: var(--vp-text-2);
  font-size: 14px;
  line-height: 1.65;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.trait-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: auto;
}
.asset-card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  padding-top: 8px;
  border-top: 1px solid var(--vp-divider);
}

@media (max-width: 820px) {
  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }
  .search { width: 100%; }
  .asset-grid { grid-template-columns: 1fr; }
}
</style>
