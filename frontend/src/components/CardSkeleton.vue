<template>
  <!-- 卡片网格骨架 -->
  <div v-if="variant === 'card'" class="vp-card-grid">
    <div v-for="n in count" :key="n" class="sk-card">
      <div class="sk-bar" />
      <div class="vp-skeleton sk-line" style="width: 70%; height: 14px;" />
      <div class="sk-meta">
        <div class="vp-skeleton sk-line pill" />
        <div class="vp-skeleton sk-line pill" />
        <div class="vp-skeleton sk-line pill short" />
      </div>
      <div class="vp-skeleton sk-line" style="width: 100%; height: 10px;" />
      <div class="vp-skeleton sk-line" style="width: 80%; height: 10px; margin-top: 6px;" />
      <div class="sk-foot">
        <div class="vp-skeleton sk-line" style="width: 50px; height: 10px;" />
        <div class="vp-skeleton sk-line" style="width: 56px; height: 22px; border-radius: 999px;" />
      </div>
    </div>
  </div>

  <!-- 表格骨架 -->
  <div v-else-if="variant === 'table'" class="sk-table">
    <div class="sk-table-head">
      <div v-for="n in 4" :key="n" class="vp-skeleton sk-line" style="height: 10px; flex: 1;" />
    </div>
    <div v-for="n in count" :key="n" class="sk-table-row">
      <div v-for="m in 4" :key="m" class="vp-skeleton sk-line" :style="{ height: '12px', width: m === 1 ? '60%' : '40%', flex: 1 }" />
    </div>
  </div>

  <!-- 详情页骨架 -->
  <div v-else class="sk-detail">
    <div class="vp-skeleton sk-line" style="height: 22px; width: 40%;" />
    <div class="vp-skeleton sk-line" style="height: 14px; width: 60%; margin-top: 12px;" />
    <div class="sk-detail-grid">
      <div v-for="n in 4" :key="n" class="sk-card">
        <div class="vp-skeleton sk-line" style="width: 30%; height: 12px;" />
        <div class="vp-skeleton sk-line" style="width: 100%; height: 10px; margin-top: 12px;" />
        <div class="vp-skeleton sk-line" style="width: 70%; height: 10px; margin-top: 8px;" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  count?: number
  variant?: 'card' | 'table' | 'detail'
}>(), {
  count: 6,
  variant: 'card',
})
</script>

<style scoped>
.sk-card {
  background: var(--vp-surface);
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-lg);
  padding: 16px 16px 12px;
  height: 178px;
  display: flex; flex-direction: column;
  position: relative;
  overflow: hidden;
}
.sk-bar {
  position: absolute; inset: 0 0 auto;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--vp-border-strong) 50%, transparent);
  opacity: 0.4;
}
.sk-line { display: block; }
.sk-line.pill { height: 18px; width: 56px; border-radius: 999px; }
.sk-line.pill.short { width: 36px; }
.sk-meta { display: flex; gap: 6px; margin: 10px 0 12px; }
.sk-foot {
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--vp-divider);
  display: flex; justify-content: space-between; align-items: center;
}

/* Table */
.sk-table {
  background: var(--vp-surface);
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-lg);
  overflow: hidden;
}
.sk-table-head, .sk-table-row {
  display: flex; gap: 24px;
  padding: 14px 20px;
  align-items: center;
}
.sk-table-head { background: var(--vp-surface-alt); border-bottom: 1px solid var(--vp-divider); }
.sk-table-row + .sk-table-row { border-top: 1px solid var(--vp-divider); }

/* Detail */
.sk-detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
  margin-top: 24px;
}
</style>
