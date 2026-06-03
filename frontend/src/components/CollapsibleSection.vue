<template>
  <section class="csec" :class="{ 'is-open': open }" :id="anchorId">
    <header class="csec-head" @click="toggle">
      <div class="csec-head-text">
        <h3 class="csec-title">{{ title }}</h3>
        <p v-if="subtitle" class="csec-subtitle">{{ subtitle }}</p>
      </div>
      <div class="csec-head-actions" :class="{ 'has-extra-actions': hasExtraActions }" @click.stop>
        <slot name="actions" />
        <el-icon class="csec-toggle" :class="{ open }"><ArrowDown /></el-icon>
      </div>
    </header>
    <!-- v-if (not v-show) so collapsed sections do NOT mount their inputs.
         For a plan with 6 sections + 20 shots, this is the difference between
         ~120 reactive textarea bindings and the current visible subset. -->
    <div v-if="open" class="csec-body">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'

const props = defineProps<{
  title: string
  subtitle?: string
  open: boolean
  /** Optional anchor for in-page scroll links. */
  anchorId?: string
}>()

const emit = defineEmits<{
  (e: 'update:open', open: boolean): void
}>()

const slots = useSlots()
const hasExtraActions = computed(() => !!slots.actions)

function toggle() {
  emit('update:open', !props.open)
}
</script>

<style scoped>
.csec {
  background: var(--vp-surface, #fff);
  border: 1px solid var(--vp-border, #e5e7eb);
  border-radius: 12px;
  margin-bottom: 14px;
  scroll-margin-top: 90px;
  transition: border-color .15s ease;
}
.csec.is-open {
  border-color: var(--vp-border-strong, #d1d5db);
}
.csec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  cursor: pointer;
  user-select: none;
}
.csec.is-open .csec-head {
  border-bottom: 1px solid var(--vp-border, #f0f0f0);
}
.csec-head-text {
  flex: 1;
  min-width: 0;
}
.csec-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--vp-text-1, #1f2937);
  line-height: 1.35;
}
.csec-subtitle {
  margin: 3px 0 0;
  font-size: 12.5px;
  line-height: 1.45;
  color: var(--vp-text-3, #9ca3af);
  word-break: normal;
  overflow-wrap: normal;
}
.csec-head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.csec-head-actions :deep(.el-button) {
  margin-left: 0;
  white-space: nowrap;
  flex-shrink: 0;
}
.csec-toggle {
  font-size: 14px;
  color: var(--vp-text-3, #9ca3af);
  transition: transform .18s ease;
}
.csec-toggle.open {
  transform: rotate(180deg);
  color: var(--vp-primary, #4f46e5);
}
.csec-body {
  padding: 18px 22px 22px;
}

@media (max-width: 720px) {
  .csec {
    border-radius: 10px;
    margin-bottom: 12px;
  }
  .csec-head {
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 10px;
    padding: 12px 14px;
  }
  .csec-head-text {
    flex: 1 1 auto;
    width: auto;
  }
  .csec-title {
    font-size: 14.5px;
  }
  .csec-subtitle {
    font-size: 12px;
    max-width: 100%;
  }
  .csec-head-actions.has-extra-actions {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
    gap: 6px 8px;
  }
  .csec-head-actions.has-extra-actions .csec-toggle {
    margin-left: auto;
  }
  .csec-body {
    padding: 14px;
  }
}
</style>
