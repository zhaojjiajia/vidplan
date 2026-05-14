<template>
  <div class="vp-page" v-loading="loadingKind">
    <header class="vp-section-head" v-if="kind">
      <div>
        <h2>{{ kind.icon }} {{ kind.label }}</h2>
        <p>{{ kind.description || '自定义资产类目' }}</p>
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
        <el-button @click="$router.push({ name: 'asset-kinds' })">返回类目</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建资产</el-button>
      </div>
    </header>

    <CardSkeleton v-if="loading && items.length === 0" :count="6" />

    <EmptyState
      v-else-if="items.length === 0"
      :title="search ? '没有匹配的资产' : '还没有资产'"
      :description="search ? '调整搜索词后再试。' : '在这个自定义类目下添加第一个资产。'"
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
          <span v-if="item.images.length > 1" class="asset-cover-count">{{ item.images.length }} 张</span>
        </div>
        <div v-else class="asset-cover asset-cover--empty">
          <el-icon><Picture /></el-icon>
        </div>
        <div class="asset-body">
          <header class="asset-card-head">
            <h3 class="asset-name">{{ item.name }}</h3>
            <span class="asset-badge">{{ kind?.icon }} {{ kind?.label }}</span>
          </header>
          <footer @click.stop>
            <el-button text type="danger" :icon="Delete" size="small" @click="onDelete(item)">删除</el-button>
          </footer>
        </div>
      </article>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑资产' : '新建资产'"
      width="640px"
      :close-on-click-modal="false"
      class="asset-edit-dialog"
    >
      <el-form label-position="top" :model="form" v-if="kind">
        <el-form-item class="aed-gallery-item">
          <AssetImageGallery
            v-model="images"
            :labels="kind.image_labels?.length ? kind.image_labels : ['封面', '其他']"
            :ai-prompt-provider="buildAssetPrompt"
          />
        </el-form-item>

        <table class="aed-table">
          <tbody>
            <tr>
              <th>名称</th>
              <td>
                <el-input v-model="form.name" :placeholder="`例如:${kind.label} 实例`" />
              </td>
            </tr>
            <tr v-for="field in kind.schema" :key="field.key">
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
                  placeholder="每行一条"
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

import { assetKindsApi, customAssetsApi } from '@/api/assets'
import AssetImageGallery from '@/components/AssetImageGallery.vue'
import CardSkeleton from '@/components/CardSkeleton.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { AssetImage, CustomAsset, CustomAssetKind } from '@/types/api'

const route = useRoute()
const kindId = computed(() => route.params.kindId as string)

const kind = ref<CustomAssetKind | null>(null)
const loadingKind = ref(false)
const items = ref<CustomAsset[]>([])
const loading = ref(false)
const saving = ref(false)

const search = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
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

onMounted(loadKind)
watch(kindId, () => {
  search.value = ''
  loadKind()
})

async function loadKind() {
  loadingKind.value = true
  try {
    // No dedicated GET-one for kind in our current api, so we list and pick.
    // Acceptable since kind list is small (per-user).
    const resp = await assetKindsApi.list()
    kind.value = resp.results.find((k) => k.id === kindId.value) || null
    if (!kind.value) {
      ElMessage.warning('未找到该类目')
      return
    }
    await load()
  } finally {
    loadingKind.value = false
  }
}

async function load() {
  if (!kind.value) return
  loading.value = true
  try {
    const resp = await customAssetsApi.list({
      kind: kind.value.id,
      search: search.value || undefined,
    })
    items.value = resp.results
  } finally {
    loading.value = false
  }
}

function onSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 250)
}

function resetTextValues(payload: Record<string, unknown> = {}) {
  if (!kind.value) return
  for (const key of Object.keys(textValues)) delete textValues[key]
  for (const f of kind.value.schema) {
    const v = payload[f.key]
    textValues[f.key] = f.kind === 'lines' && Array.isArray(v)
      ? v.map((x) => String(x)).join('\n')
      : typeof v === 'string' ? v : ''
  }
}

function buildPayloadFromFields(): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  if (!kind.value) return out
  for (const f of kind.value.schema) {
    const raw = textValues[f.key] ?? ''
    if (f.kind === 'lines') {
      out[f.key] = raw.split('\n').map((s) => s.trim()).filter(Boolean)
    } else {
      out[f.key] = raw
    }
  }
  return out
}

function openCreate() {
  editingId.value = null
  form.name = ''
  resetTextValues()
  fixedTraitsList.value = []
  images.value = []
  dialogVisible.value = true
}

function openEdit(item: CustomAsset) {
  editingId.value = item.id
  form.name = item.name
  resetTextValues((item.payload as Record<string, unknown>) || {})
  fixedTraitsList.value = Array.isArray(item.fixed_traits)
    ? item.fixed_traits.map((x) => String(x))
    : []
  images.value = Array.isArray(item.images) ? [...item.images] : []
  dialogVisible.value = true
}

async function save() {
  if (!kind.value) return
  if (!form.name.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  saving.value = true
  try {
    const body = {
      kind: kind.value.id,
      name: form.name.trim(),
      payload: buildPayloadFromFields(),
      fixed_traits: [...fixedTraitsList.value],
      images: [...images.value],
    }
    if (editingId.value) {
      await customAssetsApi.patch(editingId.value, body)
      ElMessage.success('已更新')
    } else {
      await customAssetsApi.create(body)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

function buildAssetPrompt(): string {
  const lines: string[] = []
  if (form.name.trim()) lines.push(`资产名称:${form.name.trim()}`)
  if (kind.value) {
    lines.push(`资产类型:${kind.value.label}`)
    for (const field of kind.value.schema) {
      const raw = (textValues[field.key] || '').trim()
      if (raw) lines.push(`${field.label}:${raw}`)
    }
  }
  if (fixedTraitsList.value.length) {
    lines.push(`固定特征:${fixedTraitsList.value.join(' / ')}`)
  }
  lines.push('请基于以上设定生成一张高质量参考图,写实风格,主体清晰,白色或浅色背景,工作室柔光。')
  return lines.join('\n')
}

async function onDelete(item: CustomAsset) {
  await ElMessageBox.confirm(`确认删除「${item.name}」?`, '删除资产', { type: 'warning' })
  await customAssetsApi.remove(item.id)
  ElMessage.success('已删除')
  await load()
}

function coverOf(item: CustomAsset): AssetImage | undefined {
  return Array.isArray(item.images) && item.images.length ? item.images[0] : undefined
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.header-actions { display: flex; gap: 10px; align-items: center; }
.search { width: 240px; }

.asset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.asset-card {
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-lg);
  background: var(--vp-surface);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease;
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
  width: 100%;
  height: 148px;
  background: var(--vp-surface-alt);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}
.asset-cover img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  display: block;
}
.asset-cover--empty {
  display: flex; align-items: center; justify-content: center;
  color: var(--vp-text-4); font-size: 30px;
}
.asset-cover-count {
  position: absolute; right: 10px; bottom: 10px;
  padding: 2px 10px; border-radius: 999px;
  background: rgba(0, 0, 0, .55); color: #fff; font-size: 11.5px;
}
.asset-body { padding: 10px 12px 9px; display: flex; flex-direction: column; gap: 6px; flex: 1; }
.asset-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.asset-name {
  margin: 0; font-size: 15px; font-weight: 700;
  color: var(--vp-text-1); line-height: 1.3;
  letter-spacing: -0.005em;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
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
.asset-body footer {
  margin-top: auto;
  display: flex; gap: 6px; justify-content: flex-end;
  padding-top: 6px;
  border-top: 1px solid var(--vp-divider);
}
</style>
