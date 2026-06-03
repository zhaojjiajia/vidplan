<template>
  <el-popover
    :visible="visible"
    :placement="placement"
    :width="popoverWidth"
    trigger="manual"
    popper-class="ai-rewrite-popper"
    :show-arrow="true"
    @hide="onHide"
  >
    <template #reference>
      <button
        type="button"
        class="ai-rewrite-btn"
        :class="{ active: visible, 'has-label': showLabel }"
        :title="title"
        @click.stop="toggle"
      >
        <el-icon><MagicStick /></el-icon>
        <span v-if="showLabel" class="ai-rewrite-label">AI 改写</span>
      </button>
    </template>

    <div class="ai-rewrite-popover">
      <div class="rw-head">
        <strong>AI 改写</strong>
        <span class="rw-path">{{ path }}</span>
      </div>

      <div class="rw-current">
        <span class="rw-tag">原文</span>
        <p>{{ currentValue || '(空)' }}</p>
      </div>

      <div class="rw-hint">
        <el-input
          v-model="hintDraft"
          type="textarea"
          :rows="2"
          :placeholder="hintPlaceholder"
          @keydown.enter.exact.prevent="run"
        />
        <div class="rw-actions">
          <span class="rw-count">候选:
            <el-input-number v-model="countDraft" :min="1" :max="5" size="small" />
          </span>
          <el-button :loading="loading" type="primary" size="small" @click="run">
            {{ candidates.length ? '重新生成' : '生成候选' }}
          </el-button>
        </div>
      </div>

      <div v-if="error" class="rw-error">{{ error }}</div>

      <div v-if="candidates.length" class="rw-candidates">
        <div
          v-for="(c, i) in candidates"
          :key="i"
          class="rw-candidate"
        >
          <div class="rw-candidate-head">
            <span class="rw-idx">候选 {{ i + 1 }}</span>
            <span v-if="c.reason" class="rw-reason">{{ c.reason }}</span>
          </div>
          <p class="rw-value">{{ c.value }}</p>
          <div class="rw-candidate-actions">
            <el-button text size="small" @click="copy(c.value)">复制</el-button>
            <el-button type="primary" size="small" @click="apply(c.value)">应用</el-button>
          </div>
        </div>
      </div>

      <div class="rw-foot">
        <el-button text size="small" @click="close">关闭</el-button>
      </div>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { MagicStick } from '@element-plus/icons-vue'

import { plansApi, type RewriteCandidate } from '@/api/plans'

const props = withDefaults(defineProps<{
  planId: string
  path: string
  currentValue: string
  /** Optional pre-filled hint, e.g. from a critique issue. */
  initialHint?: string
  /** Auto-run a generation when the popover first opens. */
  autoRun?: boolean
  /** Show "AI 改写" text next to the icon (defaults to icon-only). */
  showLabel?: boolean
  /** Override the popover placement (default: top). */
  placement?:
    | 'top' | 'top-start' | 'top-end'
    | 'bottom' | 'bottom-start' | 'bottom-end'
    | 'left' | 'left-start' | 'left-end'
    | 'right' | 'right-start' | 'right-end'
  /** Popover width in px. */
  popoverWidth?: number
}>(), {
  initialHint: '',
  autoRun: false,
  showLabel: false,
  placement: 'top',
  popoverWidth: 420,
})

const emit = defineEmits<{
  (e: 'apply', value: string): void
  (e: 'open'): void
  (e: 'close'): void
}>()

const visible = ref(false)
const loading = ref(false)
const error = ref('')
const hintDraft = ref('')
const countDraft = ref(3)
const candidates = ref<RewriteCandidate[]>([])

const title = computed(() => `AI 改写: ${props.path}`)
const hintPlaceholder = computed(() =>
  props.initialHint
    ? `审稿建议: ${props.initialHint}`
    : '可选: 告诉 AI 想改成什么风格 / 哪里要加强 (回车直接生成)',
)

watch(() => props.initialHint, (v) => {
  if (visible.value) hintDraft.value = v || ''
})

defineExpose({ open: openProgrammatically, close })

function toggle() {
  if (visible.value) close()
  else openProgrammatically()
}

function openProgrammatically(opts?: { hint?: string; autoRun?: boolean }) {
  visible.value = true
  hintDraft.value = opts?.hint ?? props.initialHint ?? ''
  candidates.value = []
  error.value = ''
  emit('open')
  if (opts?.autoRun ?? props.autoRun) run()
}

function close() {
  visible.value = false
}

function onHide() {
  emit('close')
}

async function run() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const resp = await plansApi.rewrite(props.planId, {
      path: props.path,
      hint: hintDraft.value.trim(),
      count: countDraft.value,
    })
    candidates.value = resp.candidates || []
    if (!candidates.value.length) {
      error.value = 'AI 没有返回候选,请换个 hint 重试'
    }
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || '改写失败'
    error.value = String(detail)
  } finally {
    loading.value = false
  }
}

function apply(value: string) {
  emit('apply', value)
  ElMessage.success('已应用')
  close()
}

async function copy(value: string) {
  try {
    await navigator.clipboard.writeText(value)
    ElMessage.success('已复制')
  } catch {
    ElMessage.warning('复制失败,请手动选择文本复制')
  }
}
</script>

<style scoped>
.ai-rewrite-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 2px;
  border: none;
  background: transparent;
  color: var(--vp-text-2, #6b7280);
  font-size: 13px;
  font-weight: 500;
  border-radius: 0;
  cursor: pointer;
  transition: color .15s ease;
  line-height: 24px;
  height: 24px;
}
.ai-rewrite-btn:hover,
.ai-rewrite-btn.active {
  color: var(--vp-primary, #4f46e5);
  background: transparent;
}
.ai-rewrite-btn :deep(.el-icon) { font-size: 14px; }
.ai-rewrite-btn.has-label {
  gap: 5px;
  padding: 5px 8px;
  font-size: 14px;
  line-height: 1;
}
.ai-rewrite-btn.has-label :deep(.el-icon) { font-size: 16px; }
.ai-rewrite-label { white-space: nowrap; }

@media (max-width: 720px) {
  .ai-rewrite-btn.has-label {
    padding: 4px 6px;
    font-size: 13.5px;
  }
  .ai-rewrite-btn.has-label :deep(.el-icon) { font-size: 15px; }
}
</style>

<style>
/* Unscoped because el-popover content is teleported outside this component. */
.ai-rewrite-popper {
  padding: 0 !important;
  max-width: calc(100vw - 24px) !important;
}

.ai-rewrite-popover {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 16px;
  font-size: 13px;
  color: var(--vp-text-1, #1f2937);
  max-height: 70vh;
  overflow-y: auto;
}

.ai-rewrite-popover .rw-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  border-bottom: 1px solid var(--vp-border, #f3f4f6);
  padding-bottom: 8px;
}
.ai-rewrite-popover .rw-head strong { font-size: 13px; }
.ai-rewrite-popover .rw-path {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11.5px;
  color: var(--vp-text-3, #9ca3af);
}

.ai-rewrite-popover .rw-current {
  background: var(--vp-surface-alt, #f9fafb);
  border-radius: 6px;
  padding: 8px 10px;
}
.ai-rewrite-popover .rw-tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 500;
  color: var(--vp-text-3, #9ca3af);
  margin-bottom: 4px;
}
.ai-rewrite-popover .rw-current p {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--vp-text-2, #4b5563);
}

.ai-rewrite-popover .rw-hint { display: flex; flex-direction: column; gap: 8px; }
.ai-rewrite-popover .rw-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.ai-rewrite-popover .rw-count {
  font-size: 12px;
  color: var(--vp-text-3, #9ca3af);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.ai-rewrite-popover .rw-error {
  font-size: 12.5px;
  color: #b91c1c;
  background: #fef2f2;
  padding: 6px 10px;
  border-radius: 4px;
}

.ai-rewrite-popover .rw-candidates {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ai-rewrite-popover .rw-candidate {
  border: 1px solid var(--vp-border, #e5e7eb);
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ai-rewrite-popover .rw-candidate-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.ai-rewrite-popover .rw-idx {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--vp-primary, #4f46e5);
}
.ai-rewrite-popover .rw-reason {
  font-size: 11.5px;
  color: var(--vp-text-3, #9ca3af);
  flex: 1;
}
.ai-rewrite-popover .rw-value {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}
.ai-rewrite-popover .rw-candidate-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
}

.ai-rewrite-popover .rw-foot {
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--vp-border, #f3f4f6);
  padding-top: 4px;
}

@media (max-width: 720px) {
  .ai-rewrite-popover {
    padding: 12px;
    max-height: 72vh;
  }
  .ai-rewrite-popover .rw-head,
  .ai-rewrite-popover .rw-candidate-head,
  .ai-rewrite-popover .rw-actions {
    align-items: flex-start;
    flex-wrap: wrap;
  }
  .ai-rewrite-popover .rw-actions {
    gap: 8px;
  }
  .ai-rewrite-popover .rw-path {
    width: 100%;
    word-break: break-all;
  }
  .ai-rewrite-popover .rw-candidate-actions {
    flex-wrap: wrap;
  }
  .ai-rewrite-popover .el-button {
    white-space: nowrap;
  }
}
</style>
