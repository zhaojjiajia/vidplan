<template>
  <el-dialog v-model="visible" title="AI 生成系列方案" width="640px" :close-on-click-modal="false">
    <el-form :model="form" label-position="top">
      <el-form-item label="方向">
        <el-select v-model="form.direction" filterable style="width:100%">
          <el-option-group v-for="group in directionGroups" :key="group.label" :label="group.label">
            <el-option v-for="item in group.options" :key="item.key" :label="item.label" :value="item.key" />
          </el-option-group>
        </el-select>
      </el-form-item>
      <el-form-item label="系列想法">
        <el-input
          v-model="form.idea"
          type="textarea"
          :rows="4"
          placeholder="例如:校园悬疑短剧,主角是转校生,每集留下一个谜题"
        />
      </el-form-item>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="目标平台">
            <el-input v-model="form.target_platform" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="更新频率">
            <el-input v-model="form.update_frequency" placeholder="日更 / 周更" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="单集时长 (秒)">
            <el-input-number v-model="form.episode_duration_seconds" :min="5" :max="3600" style="width:100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="计划集数">
            <el-input-number v-model="form.planned_episodes" :min="1" :max="999" style="width:100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="目标观众">
            <el-input v-model="form.target_audience" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="风格关键词">
        <el-input v-model="form.style" placeholder="例如:悬疑、快节奏、强反转" />
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="form.auto_create_assets">同时自动创建人物/风格/世界观/栏目资产</el-checkbox>
      </el-form-item>
    </el-form>
    <el-alert v-if="taskMessage" type="info" show-icon :closable="false" class="task-alert">
      <template #title>
        <div class="task-title">
          <span>{{ taskMessage }}</span>
          <el-progress :percentage="taskProgress" :stroke-width="6" class="task-progress" />
        </div>
      </template>
    </el-alert>
    <template #footer>
      <el-button @click="visible = false" :disabled="loading">取消</el-button>
      <el-button type="primary" :loading="loading" @click="onSubmit">生成</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { isAITaskResponse } from '@/api/aiTasks'
import { seriesApi, type SeriesGenerateInput } from '@/api/series'
import { CATEGORIES, DIRECTIONS } from '@/data/directions'
import type { AITask, SeriesPlan } from '@/types/api'
import {
  findActiveAITask,
  removeActiveAITask,
  saveActiveAITask,
  waitForAITask,
} from '@/utils/aiTaskRecovery'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'created', series: SeriesPlan): void
}>()

const visible = ref(props.modelValue)
watch(() => props.modelValue, (v) => { visible.value = v })
watch(visible, (v) => emit('update:modelValue', v))

const directionGroups = CATEGORIES.map((cat) => ({
  label: cat.label,
  options: DIRECTIONS[cat.key],
}))

const loading = ref(false)
const taskMessage = ref('')
const taskProgress = ref(0)
let taskAbortController: AbortController | null = null
const form = reactive<SeriesGenerateInput>({
  direction: 'ai_short_drama',
  idea: '',
  target_platform: '抖音',
  target_audience: '',
  update_frequency: '周更',
  episode_duration_seconds: 60,
  planned_episodes: 10,
  style: '',
  auto_create_assets: true,
})

async function onSubmit() {
  if (!form.idea.trim()) {
    ElMessage.warning('请填写系列想法')
    return
  }
  loading.value = true
  taskMessage.value = 'AI 正在生成系列方案…'
  taskProgress.value = 10
  try {
    const result = await seriesApi.generate(form)
    if (isAITaskResponse(result)) {
      saveActiveAITask({
        taskId: result.id,
        taskType: 'generate_series',
        label: '生成系列方案',
        createdAt: new Date().toISOString(),
      })
      await followSeriesTask(result)
      return
    }
    const series = result
    ElMessage.success('已生成系列方案')
    emit('created', series)
    visible.value = false
  } finally {
    loading.value = false
    taskMessage.value = ''
    taskProgress.value = 0
  }
}

async function followSeriesTask(task: AITask) {
  taskAbortController?.abort()
  taskAbortController = new AbortController()
  taskProgress.value = Math.max(task.progress || 0, 10)
  taskMessage.value = task.status === 'queued' ? 'AI 生成系列任务已排队…' : 'AI 正在生成系列方案…'
  try {
    const finished = await waitForAITask(task.id, {
      signal: taskAbortController.signal,
      onUpdate: (latest) => {
        taskProgress.value = Math.max(latest.progress || 0, 10)
        taskMessage.value = latest.status === 'queued' ? 'AI 生成系列任务已排队…' : 'AI 正在生成系列方案…'
      },
    })
    removeActiveAITask(task.id)
    const seriesId = typeof finished.result_payload.series_id === 'string' ? finished.result_payload.series_id : ''
    if (!seriesId) throw new Error('AI 任务已完成,但未返回系列 ID')
    const series = await seriesApi.get(seriesId)
    ElMessage.success('已生成系列方案')
    emit('created', series)
    visible.value = false
  } catch (err) {
    if (!isAbortError(err)) {
      removeActiveAITask(task.id)
      ElMessage.error(err instanceof Error ? err.message : 'AI 生成系列失败')
    }
  }
}

onMounted(() => {
  const active = findActiveAITask('generate_series')
  if (!active) return
  visible.value = true
  loading.value = true
  void followSeriesTask({
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
  }).finally(() => {
    loading.value = false
    taskMessage.value = ''
    taskProgress.value = 0
  })
})

onBeforeUnmount(() => {
  taskAbortController?.abort()
})

function isAbortError(err: unknown) {
  return err instanceof DOMException && err.name === 'AbortError'
}
</script>

<style scoped>
.task-alert { margin-top: 16px; }
.task-title { display: flex; align-items: center; gap: 12px; width: 100%; }
.task-progress { width: 220px; flex-shrink: 0; }

@media (max-width: 640px) {
  :deep(.el-dialog) {
    width: calc(100vw - 24px) !important;
  }
  :deep(.el-col) {
    max-width: 100%;
    flex: 0 0 100%;
  }
  .task-title {
    flex-direction: column;
    align-items: stretch;
  }
  .task-progress { width: 100%; }
}
</style>
