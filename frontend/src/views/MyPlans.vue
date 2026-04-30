<template>
  <div class="vp-page">
    <header class="vp-section-head">
      <div>
        <h2>我的方案</h2>
        <p>所有由你创作或 AI 生成的视频方案。</p>
      </div>
      <div class="header-actions">
        <el-input
          v-model="search"
          class="search"
          clearable
          placeholder="搜索标题、摘要、方向"
          :prefix-icon="Search"
        />
        <el-button type="primary" :icon="Plus" @click="$router.push('/app/plan/new')">新建方案</el-button>
      </div>
    </header>

    <div v-if="store.list.length > 0" class="list-toolbar vp-toolbar">
      <el-radio-group v-model="statusFilter" size="small">
        <el-radio-button v-for="item in statusOptions" :key="item.value" :label="item.value">
          {{ item.label }}
        </el-radio-button>
      </el-radio-group>
      <div class="toolbar-right">
        <el-select v-model="sortBy" size="small" class="sort-select">
          <el-option label="最近更新" value="updated" />
          <el-option label="标题 A-Z" value="title" />
          <el-option label="时长最长" value="duration" />
        </el-select>
        <span class="result-count">显示 {{ filteredPlans.length }} / {{ store.list.length }} 个方案</span>
      </div>
    </div>

    <CardSkeleton v-if="store.loading && store.list.length === 0" :count="6" />

    <EmptyState
      v-else-if="store.list.length === 0"
      title="还没有方案"
      description="用 AI 一句话生成完整方案,从此告别 0 分镜的空白稿。"
    >
      <template #action>
        <el-button type="primary" :icon="Plus" @click="$router.push('/app/plan/new')">创建第一个方案</el-button>
      </template>
    </EmptyState>

    <EmptyState
      v-else-if="filteredPlans.length === 0"
      title="没有匹配的方案"
      description="调整搜索词或筛选状态后再试。"
    />

    <div v-else class="vp-card-grid">
      <PlanCard
        v-for="plan in filteredPlans"
        :key="plan.id"
        :plan="plan"
        @open="onOpen"
        @duplicate="onDuplicate"
        @remove="onRemove"
        @export="onExport"
      />
    </div>

    <el-dialog v-model="exportDialogOpen" title="导出方案" width="420px" :close-on-click-modal="false">
      <p class="dialog-hint">选择导出格式,文件会自动下载到你本地。</p>
      <el-radio-group v-model="exportFormat" class="export-options">
        <el-radio-button label="md">Markdown</el-radio-button>
        <el-radio-button label="pdf">PDF</el-radio-button>
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
import { Plus, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import CardSkeleton from '@/components/CardSkeleton.vue'
import EmptyState from '@/components/EmptyState.vue'
import PlanCard from '@/components/PlanCard.vue'
import { plansApi, type PlanExportFormat } from '@/api/plans'
import { usePlansStore } from '@/stores/plans'
import { findDirectionLabel } from '@/data/directions'
import type { VideoPlan } from '@/types/api'

const store = usePlansStore()
const router = useRouter()
const search = ref('')
const statusFilter = ref<'all' | VideoPlan['status']>('all')
const sortBy = ref<'updated' | 'title' | 'duration'>('updated')
const exportDialogOpen = ref(false)
const exporting = ref(false)
const exportTarget = ref<VideoPlan | null>(null)
const exportFormat = ref<PlanExportFormat>('md')

const statusOptions = [
  { label: '全部', value: 'all' },
  { label: '草稿', value: 'draft' },
  { label: '优化中', value: 'optimizing' },
  { label: '已确认', value: 'confirmed' },
  { label: '已完成', value: 'completed' },
] as const

const filteredPlans = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  const matched = store.list.filter((plan) => {
    const statusMatched = statusFilter.value === 'all' || plan.status === statusFilter.value
    if (!statusMatched) return false
    if (!keyword) return true
    const haystack = [
      plan.title,
      plan.summary,
      plan.target_platform,
      findDirectionLabel(plan.direction),
    ].join(' ').toLowerCase()
    return haystack.includes(keyword)
  })
  return [...matched].sort((a, b) => {
    if (sortBy.value === 'title') return (a.title || '').localeCompare(b.title || '', 'zh-Hans-CN')
    if (sortBy.value === 'duration') return (b.duration_seconds || 0) - (a.duration_seconds || 0)
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  })
})

onMounted(() => store.fetchList())

function onOpen(plan: VideoPlan) {
  router.push(`/app/plan/${plan.id}`)
}

async function onDuplicate(plan: VideoPlan) {
  const copy = await plansApi.duplicate(plan.id)
  ElMessage.success('已复制')
  router.push(`/app/plan/${copy.id}`)
}

async function onRemove(plan: VideoPlan) {
  await ElMessageBox.confirm(`确认删除「${plan.title}」?`, '删除方案', { type: 'warning' })
  await store.remove(plan.id)
  ElMessage.success('已删除')
}

function onExport(plan: VideoPlan) {
  exportTarget.value = plan
  exportFormat.value = 'md'
  exportDialogOpen.value = true
}

async function confirmExport() {
  if (!exportTarget.value) return
  exporting.value = true
  try {
    await plansApi.exportPlan(exportTarget.value.id, exportFormat.value, exportTarget.value.title || 'plan')
    ElMessage.success('已开始下载')
    exportDialogOpen.value = false
  } finally {
    exporting.value = false
  }
}
</script>

<style scoped>
.header-actions { display: flex; align-items: center; gap: 10px; }
.search { width: 260px; }
.list-toolbar {
  margin: -2px 0 18px;
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.sort-select { width: 120px; }
.result-count { color: var(--vp-text-3); font-size: 12.5px; white-space: nowrap; }
.dialog-hint { color: var(--vp-text-3); font-size: 13px; margin-bottom: 16px; }
.export-options { width: 100%; display: flex; justify-content: center; }

@media (max-width: 720px) {
  .header-actions,
  .toolbar-right,
  .list-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .search { width: 100%; }
  .sort-select { width: 100%; }
  .result-count { white-space: normal; }
}
</style>
