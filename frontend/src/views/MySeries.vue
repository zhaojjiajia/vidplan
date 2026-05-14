<template>
  <div class="vp-page">
    <header class="vp-section-head">
      <div>
        <h2>我的系列</h2>
        <p>管理系列定位、更新节奏、关联资产和选题池。</p>
      </div>
      <div class="actions">
        <el-button type="primary" :icon="Plus" @click="createManualSeries">
          新建系列
        </el-button>
        <el-input
          v-model="search"
          class="search"
          clearable
          placeholder="搜索系列标题、简介"
          :prefix-icon="Search"
        />
      </div>
    </header>

    <CardSkeleton v-if="loading && list.length === 0" :count="6" />

    <EmptyState
      v-else-if="list.length === 0"
      title="还没有系列方案"
      description="可以手工新建系列,也可以从创建页使用 AI 生成。"
    />

    <EmptyState
      v-else-if="filteredSeries.length === 0"
      title="没有匹配的系列"
      description="调整搜索词或筛选状态后再试。"
    />

    <div v-else class="vp-card-grid">
      <article
        v-for="series in filteredSeries"
        :key="series.id"
        class="series-card"
        :data-status="series.status"
        role="button"
        tabindex="0"
        @click="open(series.id)"
        @keydown.enter.space.prevent="open(series.id)"
      >
        <header class="row-1">
          <h4 class="title">{{ series.title || '未命名系列' }}</h4>
          <span class="vp-status" :data-tone="statusTone(series.status)">{{ statusLabel(series.status) }}</span>
        </header>

        <div class="meta">
          <span class="meta-pill">{{ findDirectionLabel(series.direction) }}</span>
          <span class="meta-pill subtle">{{ series.episode_count }} 集</span>
        </div>

        <p class="summary">{{ series.summary || '暂无简介' }}</p>

        <footer class="foot" @click.stop>
          <span class="time">{{ formatDate(series.updated_at) }}</span>
          <div class="row-actions">
            <el-dropdown trigger="click" @command="(cmd: 'export' | 'remove') => onCommand(cmd, series)">
              <el-button text size="small">
                更多<el-icon class="el-icon--right"><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="export">导出</el-dropdown-item>
                  <el-dropdown-item command="remove" divided>
                    <span class="danger">删除</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </footer>
      </article>
    </div>

    <el-dialog v-model="exportDialogOpen" title="导出系列" width="420px" :close-on-click-modal="false">
      <p class="dialog-hint">导出系列总案 (含定位、单集模板、关联资产)。</p>
      <el-radio-group v-model="exportFormat" class="export-options">
        <el-radio-button label="md">Markdown</el-radio-button>
        <el-radio-button label="docx">Word</el-radio-button>
      </el-radio-group>
      <template #footer>
        <el-button @click="exportDialogOpen = false" :disabled="exporting">取消</el-button>
        <el-button type="primary" :loading="exporting" @click="confirmExport">导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { MoreFilled, Plus, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { seriesApi, type SeriesExportFormat } from '@/api/series'
import CardSkeleton from '@/components/CardSkeleton.vue'
import EmptyState from '@/components/EmptyState.vue'
import { findDirectionLabel } from '@/data/directions'
import type { SeriesPlan } from '@/types/api'

const router = useRouter()
const loading = ref(false)
const list = ref<SeriesPlan[]>([])
const search = ref('')
const exportDialogOpen = ref(false)
const exporting = ref(false)
const exportTarget = ref<SeriesPlan | null>(null)
const exportFormat = ref<SeriesExportFormat>('md')

const filteredSeries = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  const matched = list.value.filter((series) => {
    if (!keyword) return true
    const haystack = [
      series.title,
      series.summary,
      findDirectionLabel(series.direction),
    ].join(' ').toLowerCase()
    return haystack.includes(keyword)
  })
  return [...matched].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
})

onMounted(load)

async function load() {
  loading.value = true
  try {
    const data = await seriesApi.list()
    list.value = data.results
  } finally {
    loading.value = false
  }
}

function open(id: string) {
  router.push(`/app/series/${id}`)
}

function createManualSeries() {
  router.push('/app/series/new')
}

function onCommand(cmd: 'export' | 'remove', series: SeriesPlan) {
  if (cmd === 'export') openExport(series)
  if (cmd === 'remove') void remove(series)
}

async function remove(series: SeriesPlan) {
  await ElMessageBox.confirm(`确认删除「${series.title}」?`, '删除系列', { type: 'warning' })
  await seriesApi.remove(series.id)
  ElMessage.success('已删除')
  await load()
}

function openExport(series: SeriesPlan) {
  exportTarget.value = series
  exportFormat.value = 'md'
  exportDialogOpen.value = true
}

async function confirmExport() {
  if (!exportTarget.value) return
  exporting.value = true
  try {
    await seriesApi.exportSeries(exportTarget.value.id, exportFormat.value, exportTarget.value.title || 'series')
    ElMessage.success('已开始下载')
    exportDialogOpen.value = false
  } finally {
    exporting.value = false
  }
}

function statusLabel(status: SeriesPlan['status']) {
  return ({ draft: '草稿', ongoing: '连载中', paused: '已暂停', completed: '已完成' })[status]
}

function statusTone(status: SeriesPlan['status']) {
  if (status === 'ongoing') return 'success'
  if (status === 'paused') return 'warning'
  if (status === 'completed') return 'primary'
  return 'info'
}

function formatDate(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const that = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const diff = Math.round((today.getTime() - that.getTime()) / 86400000)
  if (diff === 0) return '今天 ' + d.toTimeString().slice(0, 5)
  if (diff === 1) return '昨天 ' + d.toTimeString().slice(0, 5)
  if (diff < 7) return `${diff} 天前`
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
</script>

<style scoped>
.actions { display: flex; gap: 10px; align-items: center; }
.search { width: 240px; }

.series-card {
  background: rgba(255, 255, 255, .48);
  border: 1px solid rgba(94, 78, 70, .11);
  border-radius: var(--vp-r-lg);
  padding: 16px 16px 12px;
  display: flex; flex-direction: column;
  cursor: pointer;
  transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease;
  height: 100%;
  min-height: 160px;
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(18px) saturate(138%);
  animation: vp-fade-up .35s ease both;
}
.series-card::before {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--vp-border-strong) 30%, var(--vp-border-strong) 70%, transparent);
  opacity: 0.55;
  transition: opacity .18s ease;
}
.series-card[data-status="ongoing"]::before {
  background: linear-gradient(90deg, transparent, var(--vp-success) 30%, var(--vp-success) 70%, transparent);
  opacity: 0.7;
}
.series-card[data-status="paused"]::before {
  background: linear-gradient(90deg, transparent, var(--vp-warning) 30%, var(--vp-warning) 70%, transparent);
  opacity: 0.7;
}
.series-card[data-status="completed"]::before {
  background: linear-gradient(90deg, transparent, var(--vp-primary) 30%, var(--vp-primary) 70%, transparent);
  opacity: 0.7;
}
.series-card[data-status="draft"]::before {
  background: linear-gradient(90deg, transparent, var(--vp-accent) 30%, var(--vp-accent) 70%, transparent);
  opacity: 0.55;
}
.series-card:hover::before { opacity: 1; }
.series-card:hover {
  border-color: color-mix(in srgb, var(--vp-primary) 32%, rgba(94, 78, 70, .11));
  box-shadow: 0 18px 42px rgba(84, 40, 36, .10);
  transform: translateY(-2px);
}
.series-card:active { transform: translateY(-1px); }

.row-1 { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.title {
  margin: 0; flex: 1;
  font-size: 15px; font-weight: 600;
  line-height: 1.4;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  min-height: 42px;
}

.vp-status { flex-shrink: 0; }

.meta { display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0 10px; }
.meta-pill {
  font-size: 11.5px; font-weight: 500;
  padding: 2px 8px; border-radius: var(--vp-r-pill);
  background: var(--vp-primary-soft); color: var(--vp-primary);
}
.meta-pill.subtle { background: var(--vp-info-soft); color: var(--vp-text-2); }

.summary {
  color: var(--vp-text-3); font-size: 13px; line-height: 1.5;
  margin: 0 0 12px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  min-height: 39px;
}

.foot {
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--vp-divider);
  display: flex; justify-content: space-between; align-items: center;
}
.time { font-size: 12px; color: var(--vp-text-3); }
.row-actions { display: flex; gap: 2px; }
.danger { color: var(--vp-danger); }

.dialog-hint { color: var(--vp-text-3); font-size: 13px; margin-bottom: 16px; }
.export-options { width: 100%; display: flex; justify-content: center; }

@media (max-width: 820px) {
  .actions {
    flex-direction: column;
    align-items: stretch;
  }
  .search { width: 100%; }
}

@media (max-width: 560px) {
  .series-card { min-height: auto; }
}
</style>
