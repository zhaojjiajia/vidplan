<template>
  <article
    class="shot-card"
    :class="{ 'is-expanded': expanded }"
    :data-shot-idx="index"
  >
    <header class="shot-card-head" @click="toggle">
      <div class="shot-card-head-left">
        <span class="shot-num">镜头 {{ index + 1 }}</span>
        <span class="shot-dur">· {{ shotDuration }}s</span>
        <p v-if="!expanded" class="shot-summary">{{ summaryLine || '(未填写)' }}</p>
      </div>
      <div class="shot-card-head-right" @click.stop>
        <AIRewriteButton
          v-if="expanded"
          :ref="bindDescriptionRef"
          :plan-id="planId"
          :path="`storyboard[${index}].description`"
          :current-value="shot.description || ''"
          show-label
          placement="bottom-end"
          @apply="(v: string) => emit('rewrite', `storyboard[${index}].description`, v)"
        />
        <el-button
          v-if="expanded"
          text
          type="danger"
          size="small"
          :icon="Delete"
          @click="emit('remove', index)"
        >
          删除
        </el-button>
        <el-icon class="shot-toggle-icon" :class="{ open: expanded }"><ArrowDown /></el-icon>
      </div>
    </header>

    <!-- v-if so collapsed cards do not mount the textarea — for long
         storyboards this saves the bulk of reactive bindings on the page. -->
    <div v-if="expanded" class="shot-body">
      <el-input
        :model-value="shot.description"
        type="textarea"
        :rows="6"
        :autosize="{ minRows: 5, maxRows: 14 }"
        placeholder="一段完整描述: 画面(主体/动作/表情/构图/光线) → 台词(用引号) → 剪辑/运镜/字幕提示"
        @update:model-value="(v: string) => onUpdate('description', v)"
      />
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowDown, Delete } from '@element-plus/icons-vue'

import AIRewriteButton from './AIRewriteButton.vue'
import type { StoryboardShot } from '@/types/api'

type RewriteAPI = { open: (opts?: { hint?: string; autoRun?: boolean }) => void; close: () => void }

const props = defineProps<{
  planId: string
  index: number
  shot: StoryboardShot
  /** When false, only the header row + a one-line summary render. Massively
   * cuts DOM nodes and reactive subscriptions for long storyboards. */
  expanded: boolean
}>()

const emit = defineEmits<{
  (e: 'update', field: keyof StoryboardShot, value: string | number): void
  (e: 'remove', index: number): void
  (e: 'rewrite', path: string, value: string): void
  (e: 'register-rewrite-ref', path: string, api: RewriteAPI | null): void
  (e: 'toggle', expanded: boolean): void
}>()

const summaryLine = computed(() => {
  const text = (props.shot.description || '').trim()
  if (!text) return ''
  return text.length > 56 ? `${text.slice(0, 56)}…` : text
})

const shotDuration = computed(() => {
  const duration = Number(props.shot.duration)
  if (Number.isFinite(duration) && duration > 0) return Math.round(duration)
  return 3
})

function toggle() {
  emit('toggle', !props.expanded)
}

function onUpdate(field: keyof StoryboardShot, value: unknown) {
  emit('update', field, value as string)
}

function bindDescriptionRef(el: unknown) {
  const path = `storyboard[${props.index}].description`
  const api = el as RewriteAPI | null
  emit('register-rewrite-ref', path, api && typeof api.open === 'function' ? api : null)
}
</script>

<style scoped>
.shot-card {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--vp-border, #e5e7eb);
  border-radius: 10px;
  background: var(--vp-surface, #fff);
  transition: border-color .15s ease, box-shadow .15s ease;
}
.shot-card:hover {
  border-color: var(--vp-border-strong, #d1d5db);
}
.shot-card.is-expanded {
  border-color: var(--vp-primary, #4f46e5);
  box-shadow: 0 1px 3px rgba(79, 70, 229, .08);
}

.shot-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  cursor: pointer;
  user-select: none;
  min-width: 0;
}
.shot-card.is-expanded .shot-card-head {
  border-bottom: 1px solid var(--vp-border, #f0f0f0);
  background: var(--vp-surface-alt, #fafafa);
  border-top-left-radius: 10px;
  border-top-right-radius: 10px;
}

.shot-card-head-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.shot-num {
  font-size: 13px;
  font-weight: 600;
  color: var(--vp-text-1, #1f2937);
  flex-shrink: 0;
  white-space: nowrap;
}
.shot-dur {
  font-size: 12px;
  color: var(--vp-text-3, #9ca3af);
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.shot-summary {
  margin: 0;
  font-size: 12.5px;
  color: var(--vp-text-3, #6b7280);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.shot-card-head-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  min-width: 0;
}
.shot-toggle-icon {
  font-size: 14px;
  color: var(--vp-text-3, #9ca3af);
  transition: transform .18s ease;
}
.shot-toggle-icon.open {
  transform: rotate(180deg);
  color: var(--vp-primary, #4f46e5);
}

.shot-body {
  padding: 16px 18px 18px;
  min-width: 0;
}
.shot-body :deep(.el-textarea) {
  display: block;
  width: 100%;
  max-width: 100%;
}
/* Borderless textarea — sits flush in the card's white area, big readable
   font, no chrome competing with the content. el-input's default border /
   shadow / background are all overridden via :deep so the user sees just
   their text in a clean white panel. */
.shot-body :deep(.el-textarea__inner) {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  padding: 0;
  font-size: 16px;
  line-height: 1.8;
  color: var(--vp-text-1);
  resize: none;
  font-family: inherit;
}
.shot-body :deep(.el-textarea__inner:hover),
.shot-body :deep(.el-textarea__inner:focus) {
  border: none !important;
  box-shadow: none !important;
  outline: none;
}
.shot-body :deep(.el-textarea__inner::placeholder) {
  color: var(--vp-text-4, #d1d5db);
  font-size: 14.5px;
}
</style>
