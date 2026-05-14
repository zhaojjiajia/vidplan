<template>
  <div class="vp-page">
    <header class="vp-section-head">
      <div>
        <h2>自定义资产类目</h2>
        <p>除了内置的人物 / 风格 / 世界观 / 栏目,你可以自己加新类(BGM / 道具 / 台词金句…)。</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">新建类目</el-button>
    </header>

    <CardSkeleton v-if="loading && items.length === 0" :count="3" />

    <EmptyState
      v-else-if="items.length === 0"
      title="还没有自定义类目"
      description="把内置 4 类没覆盖到的资产(BGM、道具、金句库 …)加进来,统一沉淀。"
    >
      <template #action>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建类目</el-button>
      </template>
    </EmptyState>

    <div v-else class="kind-grid">
      <article v-for="kind in items" :key="kind.id" class="kind-card">
        <button type="button" class="kind-cover" @click="openKind(kind)">
          <span class="kind-icon">{{ kind.icon || '📦' }}</span>
        </button>
        <div class="kind-body">
          <header class="kind-head">
            <h3>{{ kind.label }}</h3>
            <span class="kind-count">{{ kind.asset_count || 0 }} 项</span>
          </header>
          <p class="kind-name">key · {{ kind.name }}</p>
          <p v-if="kind.description" class="kind-desc">{{ kind.description }}</p>
          <p v-else class="muted">未填写描述</p>
          <footer class="kind-actions">
            <el-button text type="primary" @click="openKind(kind)">进入</el-button>
            <el-button text @click="openEdit(kind)">编辑</el-button>
            <el-button text type="danger" @click="onDelete(kind)">删除</el-button>
          </footer>
        </div>
      </article>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑类目' : '新建类目'"
      width="560px"
      :close-on-click-modal="false"
    >
      <el-form label-position="top" :model="form">
        <el-form-item label="类目名称">
          <el-input v-model="form.label" placeholder="例如 BGM 音乐 / 常用道具 / 台词金句" />
        </el-form-item>
        <el-form-item label="key (URL 用,英文小写,字母 / 数字 / 短横线)">
          <el-input v-model="form.name" placeholder="例如 bgm" />
        </el-form-item>
        <el-form-item label="图标 (emoji 或留空)">
          <el-input v-model="form.icon" placeholder="📦 🎵 🪄" maxlength="4" />
        </el-form-item>
        <el-form-item label="字段 (每行一个,格式: 字段名|类型(text/textarea/lines))">
          <el-input
            v-model="schemaText"
            type="textarea"
            :autosize="{ minRows: 4 }"
            placeholder="名称|text&#10;时长|text&#10;情绪|text&#10;备注|textarea"
          />
          <div class="hint muted">类型默认 text,可省略 |type 后缀。lines = 多行列表。</div>
        </el-form-item>
        <el-form-item label="图片标签 (每行一个)">
          <el-input
            v-model="imageLabelsText"
            type="textarea"
            :autosize="{ minRows: 2 }"
            placeholder="封面&#10;详情图&#10;其他"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :autosize="{ minRows: 2 }"
            placeholder="可选 — 这个类目用来存什么"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">
          {{ editingId ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { assetKindsApi } from '@/api/assets'
import CardSkeleton from '@/components/CardSkeleton.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { AssetSchemaField, CustomAssetKind } from '@/types/api'

const router = useRouter()
const items = ref<CustomAssetKind[]>([])
const loading = ref(false)
const saving = ref(false)

const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({ name: '', label: '', icon: '📦', description: '' })
const schemaText = ref('')
const imageLabelsText = ref('')

onMounted(load)

async function load() {
  loading.value = true
  try {
    const resp = await assetKindsApi.list()
    items.value = resp.results
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.name = ''
  form.label = ''
  form.icon = '📦'
  form.description = ''
  schemaText.value = '名称|text\n描述|textarea\n备注|textarea'
  imageLabelsText.value = '封面\n其他'
  dialogVisible.value = true
}

function openEdit(kind: CustomAssetKind) {
  editingId.value = kind.id
  form.name = kind.name
  form.label = kind.label
  form.icon = kind.icon || '📦'
  form.description = kind.description || ''
  schemaText.value = (kind.schema || [])
    .map((f) => `${f.label}|${f.kind}`)
    .join('\n')
  imageLabelsText.value = (kind.image_labels || []).join('\n')
  dialogVisible.value = true
}

function openKind(kind: CustomAssetKind) {
  router.push({ name: 'asset-custom', params: { kindId: kind.id } })
}

function parseSchemaText(text: string): AssetSchemaField[] {
  const out: AssetSchemaField[] = []
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    const [label, kindRaw] = line.split('|').map((p) => p.trim())
    if (!label) continue
    const kind = (['text', 'textarea', 'lines'].includes(kindRaw) ? kindRaw : 'text') as AssetSchemaField['kind']
    const key = slugify(label) || `f${out.length + 1}`
    out.push({ key, label, kind })
  }
  return out
}

function slugify(text: string): string {
  // Light slugifier: keep ASCII letters/digits, drop the rest. Chinese-only
  // labels lose all chars, in which case we fall back to f1/f2/... above.
  return text.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '')
}

async function save() {
  if (!form.label.trim()) {
    ElMessage.warning('请填写类目名称')
    return
  }
  if (!form.name.trim()) {
    ElMessage.warning('请填写 key')
    return
  }
  if (!/^[a-z][a-z0-9_-]*$/.test(form.name.trim())) {
    ElMessage.warning('key 只能用小写字母、数字、下划线、短横线,且字母开头')
    return
  }

  const payload = {
    name: form.name.trim(),
    label: form.label.trim(),
    icon: form.icon.trim(),
    description: form.description.trim(),
    schema: parseSchemaText(schemaText.value),
    image_labels: imageLabelsText.value.split('\n').map((l) => l.trim()).filter(Boolean),
  }

  saving.value = true
  try {
    if (editingId.value) {
      await assetKindsApi.patch(editingId.value, payload)
      ElMessage.success('已更新类目')
    } else {
      await assetKindsApi.create(payload)
      ElMessage.success('已创建类目')
    }
    dialogVisible.value = false
    await load()
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.response?.data?.name?.[0] || err?.message || '保存失败'
    ElMessage.error(String(detail))
  } finally {
    saving.value = false
  }
}

async function onDelete(kind: CustomAssetKind) {
  await ElMessageBox.confirm(
    `确认删除「${kind.label}」?该类目下的所有资产也会一并删除。`,
    '删除类目',
    { type: 'warning' },
  )
  await assetKindsApi.remove(kind.id)
  ElMessage.success('已删除')
  await load()
}
</script>

<style scoped>
.kind-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.kind-card {
  display: flex;
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-lg);
  background: var(--vp-surface);
  overflow: hidden;
  transition: border-color .15s, box-shadow .15s;
}
.kind-card:hover {
  border-color: var(--vp-border-strong);
  box-shadow: var(--vp-shadow-md);
}
.kind-cover {
  width: 90px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: var(--vp-primary-soft, #eef2ff);
  cursor: pointer;
  font-size: 38px;
}
.kind-icon { line-height: 1; }
.kind-body {
  flex: 1;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.kind-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.kind-head h3 { margin: 0; font-size: 16px; color: var(--vp-text-1); }
.kind-count { font-size: 12px; color: var(--vp-text-3); }
.kind-name {
  margin: 0;
  font-size: 11.5px;
  color: var(--vp-text-3);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.kind-desc {
  margin: 0;
  font-size: 13px;
  color: var(--vp-text-2);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.muted { color: var(--vp-text-3); font-size: 13px; }
.kind-actions {
  margin-top: auto;
  display: flex;
  gap: 4px;
  padding-top: 8px;
  border-top: 1px solid var(--vp-divider);
}
.hint { font-size: 11.5px; margin-top: 4px; }
</style>
