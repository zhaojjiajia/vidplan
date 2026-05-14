<template>
  <div class="vp-page">
    <header class="vp-section-head">
      <div>
        <h2>我的方案</h2>
        <p>所有由你创作或 AI 生成的视频方案。</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" :loading="creatingPlan" @click="createManualPlan">
          新建方案
        </el-button>
        <el-input
          v-model="search"
          class="search"
          clearable
          placeholder="搜索标题、摘要、方向"
          :prefix-icon="Search"
        />
      </div>
    </header>

    <CardSkeleton v-if="store.loading && store.list.length === 0" :count="6" />

    <EmptyState
      v-else-if="singlePlans.length === 0"
      title="还没有方案"
      description="可以手工新建方案,也可以从创建页使用 AI 生成。"
    />

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
import { resolveDirectionDisplay } from '@/data/directions'
import type { VideoPlan } from '@/types/api'

const store = usePlansStore()
const router = useRouter()
const search = ref('')
const exportDialogOpen = ref(false)
const exporting = ref(false)
const exportTarget = ref<VideoPlan | null>(null)
const exportFormat = ref<PlanExportFormat>('md')
const creatingPlan = ref(false)

const singlePlans = computed(() => store.list.filter((plan) => !plan.series))

const filteredPlans = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  const matched = singlePlans.value.filter((plan) => {
    if (!keyword) return true
    const haystack = [
      plan.title,
      plan.summary,
      resolveDirectionDisplay(plan),
    ].join(' ').toLowerCase()
    return haystack.includes(keyword)
  })
  return [...matched].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
})

onMounted(() => store.fetchList())

function onOpen(plan: VideoPlan) {
  router.push(`/app/plan/${plan.id}`)
}

async function createManualPlan() {
  creatingPlan.value = true
  try {
    const plan = await plansApi.create({
      title: '未命名方案',
      direction: '',
      category: 'real',
      is_ai_generated_video: false,
      series: null,
      target_platform: '',
      target_audience: '',
      duration_seconds: 30,
      style: '',
      summary: '',
      content: {},
      storyboard: [],
      editing_advice: {},
      ai_prompts: {},
      status: 'draft',
    })
    store.list = [plan, ...store.list.filter((item) => item.id !== plan.id)]
    router.push(`/app/plan/${plan.id}`)
  } finally {
    creatingPlan.value = false
  }
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
.dialog-hint { color: var(--vp-text-3); font-size: 13px; margin-bottom: 16px; }
.export-options { width: 100%; display: flex; justify-content: center; }

@media (max-width: 720px) {
  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }
  .search { width: 100%; }
}
</style>
