<template>
  <div class="shot-insert" @click="emit('click')">
    <div class="shot-insert-line"></div>
    <button class="shot-insert-btn" type="button" :title="`在第 ${position} 个位置插入新镜头`">
      <el-icon><Plus /></el-icon>
      <span>在此处插入镜头</span>
    </button>
    <div class="shot-insert-line"></div>
  </div>
</template>

<script setup lang="ts">
import { Plus } from '@element-plus/icons-vue'

defineProps<{
  /** 1-indexed position the new shot would occupy after insert. Used for the
   * tooltip — "在第 3 个位置插入新镜头" reads more naturally than the array
   * index. */
  position: number
}>()

const emit = defineEmits<{
  (e: 'click'): void
}>()
</script>

<style scoped>
.shot-insert {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 14px;
  margin: 4px 0;
  cursor: pointer;
  opacity: 0;
  transition: opacity .12s ease;
}
.shot-insert:hover { opacity: 1; }
/* When user hovers the gap, also reveal the line; the button uses its own
   hover style below. */
.shot-insert-line {
  flex: 1;
  height: 1px;
  background: var(--vp-primary, #4f46e5);
  opacity: .35;
}
.shot-insert-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 999px;
  border: 1px solid var(--vp-primary, #4f46e5);
  background: var(--vp-surface, #fff);
  color: var(--vp-primary, #4f46e5);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  line-height: 1.6;
  transition: background .12s ease, transform .12s ease;
}
.shot-insert-btn:hover {
  background: var(--vp-primary, #4f46e5);
  color: #fff;
  transform: scale(1.02);
}
.shot-insert-btn :deep(.el-icon) { font-size: 12px; }
</style>
