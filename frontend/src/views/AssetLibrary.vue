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
      :description="search ? '调整搜索词后再试。' : '把可复用的人物和环境沉淀下来,后续每条方案都能直接用。'"
    >
      <template v-if="!search" #action>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建资产</el-button>
      </template>
    </EmptyState>

    <div v-else class="asset-grid">
      <article
        v-for="item in items"
        :key="item.id"
        class="asset-card"
        role="button"
        tabindex="0"
        @click="openEdit(item)"
        @keydown.enter.space.prevent="openEdit(item)"
      >
        <div v-if="coverOf(item)" class="asset-cover">
          <img :src="coverOf(item)?.thumb_url || coverOf(item)?.url" :alt="item.name" />
          <span v-if="(item.images?.length ?? 0) > 1" class="asset-cover-count">
            {{ item.images!.length }} 张
          </span>
        </div>
        <div v-else class="asset-cover asset-cover--empty">
          <el-icon><Picture /></el-icon>
        </div>

        <div class="asset-body">
          <header class="asset-card-head">
            <h3 class="asset-name">{{ item.name }}</h3>
            <span class="asset-badge">{{ schema.title }}</span>
          </header>

          <footer class="asset-card-actions" @click.stop>
            <el-button text type="danger" :icon="Delete" size="small" @click="remove(item)">删除</el-button>
          </footer>
        </div>
      </article>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑资产' : '新建资产'"
      width="720px"
      class="asset-edit-dialog"
    >
      <el-form label-position="top">
        <!-- 参考图 first, no label — gallery is its own visual block. -->
        <el-form-item class="aed-gallery-item">
          <AssetImageGallery
            v-model="images"
            :labels="schema.imageLabels"
            :ai-prompt-provider="buildAssetPrompt"
          />
        </el-form-item>

        <!-- Field table: each row is "字段名 | 值",一律左右两列对齐显示。
             比纵向 form 列表更紧凑,信息密度高,跟资料卡的"档案"感一致。 -->
        <table class="aed-table">
          <tbody>
            <tr>
              <th>名称</th>
              <td>
                <el-input v-model="form.name" placeholder="例如: 女主小满 / 狗熊岭森林" />
              </td>
            </tr>
            <tr v-for="field in schema.fields" :key="field.key">
              <th>{{ field.label }}</th>
              <td>
                <el-input
                  v-if="field.kind === 'text'"
                  v-model="textValues[field.key]"
                  :placeholder="field.placeholder"
                />
                <el-input
                  v-else
                  v-model="textValues[field.key]"
                  type="textarea"
                  :autosize="{ minRows: 1 }"
                  :placeholder="field.placeholder"
                />
              </td>
            </tr>
            <tr>
              <th>固定特征</th>
              <td>
                <el-input
                  v-model="fixedTraitsText"
                  type="textarea"
                  :autosize="{ minRows: 1 }"
                  placeholder="每行一条:发色 / 性格 / 口头禅"
                />
              </td>
            </tr>
          </tbody>
        </table>
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
import { Delete, Picture, Plus, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { assetsApi } from '@/api/assets'
import AssetImageGallery from '@/components/AssetImageGallery.vue'
import CardSkeleton from '@/components/CardSkeleton.vue'
import EmptyState from '@/components/EmptyState.vue'
import { ASSET_SCHEMAS, type AssetField } from '@/data/assetSchemas'
import type { AssetBase, AssetImage, AssetType } from '@/types/api'

const route = useRoute()
const assetType = computed(() => route.meta.assetType as AssetType)
const schema = computed(() => ASSET_SCHEMAS[assetType.value])

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const items = ref<AssetBase[]>([])

const search = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

const form = reactive({ name: '' })
const textValues = reactive<Record<string, string>>({})
const fixedTraitsList = ref<string[]>([])
const images = ref<AssetImage[]>([])

const fixedTraitsText = computed({
  get: () => fixedTraitsList.value.join('\n'),
  set: (v) => {
    fixedTraitsList.value = v.split('\n').map((s) => s.trim()).filter(Boolean)
  },
})

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
  images.value = []
  dialogVisible.value = true
}

function openEdit(item: AssetBase) {
  editingId.value = item.id
  form.name = item.name
  resetTextValues((item.payload as Record<string, unknown>) || {})
  fixedTraitsList.value = Array.isArray(item.fixed_traits)
    ? item.fixed_traits.map((x) => String(x))
    : []
  images.value = Array.isArray(item.images) ? [...item.images] : []
  dialogVisible.value = true
}

/**
 * Synthesise a Chinese prompt for AI image generation from the current form
 * state. Used by AssetImageGallery's `aiPromptProvider` so users don't have
 * to type a description themselves.
 */
function buildAssetPrompt(): string {
  const lines: string[] = []
  if (form.name.trim()) lines.push(`资产名称:${form.name.trim()}`)
  lines.push(`资产类型:${schema.value.title}`)
  for (const field of schema.value.fields) {
    const raw = (textValues[field.key] || '').trim()
    if (raw) lines.push(`${field.label}:${raw}`)
  }
  if (fixedTraitsList.value.length) {
    lines.push(`固定特征:${fixedTraitsList.value.join(' / ')}`)
  }
  lines.push('请基于以上设定生成一张高质量参考图,写实风格,主体清晰,白色或浅色背景,工作室柔光。')
  return lines.join('\n')
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  const payload = buildPayloadFromFields()

  saving.value = true
  try {
    const body = {
      name: form.name.trim(),
      payload,
      fixed_traits: [...fixedTraitsList.value],
      images: [...images.value],
    }
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

function coverOf(item: AssetBase): AssetImage | undefined {
  return Array.isArray(item.images) && item.images.length ? item.images[0] : undefined
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
.asset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.asset-card {
  min-height: 176px;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-lg);
  background: var(--vp-surface);
  box-shadow: var(--vp-shadow-xs);
  transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease;
  overflow: hidden;
  cursor: pointer;
}
.asset-card:hover {
  border-color: var(--vp-border-strong);
  box-shadow: var(--vp-shadow-md);
  transform: translateY(-2px);
}
.asset-card:focus-visible {
  outline: 2px solid var(--vp-primary);
  outline-offset: 2px;
}

.asset-cover {
  position: relative;
  width: 100%;
  /* Taller cover so portrait images (人物全身像) display larger. */
  height: 148px;
  background: var(--vp-surface-alt, #f3f4f6);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.asset-cover img {
  max-width: 100%;
  max-height: 100%;
  /* Contain (not cover) so a tall portrait — like a full-body 熊大 — shows
     the entire figure with letterboxing on the sides instead of getting
     sliced through the middle. The cover background fills the empty area. */
  object-fit: contain;
  display: block;
}
.asset-cover--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--vp-text-4, #d1d5db);
  font-size: 30px;
}
.asset-cover-count {
  position: absolute;
  right: 10px;
  bottom: 10px;
  padding: 2px 10px;
  border-radius: 999px;
  background: rgba(0, 0, 0, .55);
  color: #fff;
  font-size: 11.5px;
  font-weight: 500;
}

.asset-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px 9px;
  flex: 1;
}
.asset-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.asset-name {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.005em;
  color: var(--vp-text-1);
  line-height: 1.3;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  flex: 1;
  min-width: 0;
}
.asset-badge {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: var(--vp-r-pill);
  background: var(--vp-primary-soft);
  color: var(--vp-primary);
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}
.asset-card-actions {
  margin-top: auto;
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  padding-top: 6px;
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

<!-- Dialog inputs are styled globally in styles/asset-edit-dialog.css -->
