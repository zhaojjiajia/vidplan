<template>
  <el-dialog
    v-model="visible"
    :width="dialogWidth"
    :show-close="false"
    :close-on-click-modal="false"
    :destroy-on-close="true"
    align-center
    class="critique-dialog"
    @closed="emit('closed')"
  >
    <template #header>
      <div class="cd-head">
        <div class="cd-head-text">
          <h2>AI 审稿结果</h2>
          <p class="cd-head-sub">用于在确认前看一眼方案的整体质量与待办</p>
        </div>
        <el-button text :icon="Close" @click="visible = false" />
      </div>
    </template>

    <div class="cd-body">
      <div v-if="loading" class="cd-loading">
        <el-icon class="is-loading" size="20"><Loading /></el-icon>
        <span>AI 正在审稿…</span>
      </div>

      <AICritiquePanel
        v-else-if="critique"
        :critique="critique"
        :default-collapsed="false"
        :issue-done="issueDone"
        class="cd-panel"
        @fix="(path: string, hint: string) => emit('fix', path, hint)"
        @mark-done="(idx: number, state: 'fixed' | 'skipped') => emit('mark-done', idx, state)"
      />

      <div v-else class="cd-empty">
        <p>暂无审稿数据。</p>
      </div>
    </div>

    <template #footer>
      <div class="cd-foot">
        <el-button @click="emit('back')" :disabled="loading">返回继续修改</el-button>
        <el-button @click="emit('refresh')" :disabled="loading" :loading="loading">
          重新审稿
        </el-button>
        <el-button type="primary" @click="emit('confirm')" :disabled="loading">
          继续确认方案
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { Close, Loading } from '@element-plus/icons-vue'

import AICritiquePanel from './AICritiquePanel.vue'
import type { AICritique } from '@/types/api'

const props = defineProps<{
  modelValue: boolean
  loading?: boolean
  critique?: AICritique | null
  /** Per-issue handled state from the parent — survives dialog open/close. */
  issueDone?: Record<number, 'fixed' | 'skipped' | undefined>
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', open: boolean): void
  (e: 'back'): void
  (e: 'confirm'): void
  (e: 'refresh'): void
  (e: 'fix', path: string, hint: string): void
  (e: 'mark-done', idx: number, state: 'fixed' | 'skipped'): void
  (e: 'closed'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

// Dialog width adapts: tablet+ uses a comfortable 720px modal; phones go
// full-width because the critique panel has lots of vertical content.
const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1280)
function onResize() { viewportWidth.value = window.innerWidth }
if (typeof window !== 'undefined') {
  window.addEventListener('resize', onResize)
}
onBeforeUnmount(() => {
  if (typeof window !== 'undefined') window.removeEventListener('resize', onResize)
})

const dialogWidth = computed<string>(() => {
  if (viewportWidth.value < 600) return '94%'
  if (viewportWidth.value < 1000) return '600px'
  return '720px'
})
</script>

<style scoped>
.cd-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.cd-head-text h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--vp-text-1);
}
.cd-head-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--vp-text-3);
}

.cd-body {
  font-size: 14px;
  min-height: 120px;
}

.cd-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px 0;
  color: var(--vp-text-2);
}
.cd-loading .is-loading { animation: rotating 2s linear infinite; }
@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.cd-empty {
  padding: 40px 0;
  text-align: center;
  color: var(--vp-text-3);
}

.cd-panel :deep(.el-card__header) {
  padding: 12px 18px !important;
}
.cd-panel :deep(.el-card__body) {
  padding: 16px 18px 18px !important;
}
/* Bump readability inside the dialog — drawer/scoped panel ran 11.5-12px,
   the user said it was tight; here we use 13.5-14px throughout. */
.cd-panel :deep(.critique-summary p),
.cd-panel :deep(.axis-name),
.cd-panel :deep(.axis-comment),
.cd-panel :deep(.issue-text) {
  font-size: 14px;
}
.cd-panel :deep(.issue-meta) {
  font-size: 13px;
}
.cd-panel :deep(.head-line) {
  font-size: 14px;
}

.cd-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
