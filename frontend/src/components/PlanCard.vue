<template>
  <article
    class="plan-card"
    :data-status="plan.status"
    role="button"
    tabindex="0"
    @click="$emit('open', plan)"
    @keydown.enter.space.prevent="$emit('open', plan)"
  >
    <header class="row-1">
      <h4 class="title">{{ plan.title || '未命名方案' }}</h4>
      <span class="vp-status" :data-tone="statusTone" :class="{ 'is-pulsing': plan.status === 'optimizing' }">
        {{ statusLabel }}
      </span>
    </header>

    <div class="meta">
      <span class="meta-pill">{{ findDirectionLabel(plan.direction) }}</span>
      <span class="meta-pill subtle">{{ plan.target_platform || '未设平台' }}</span>
      <span class="meta-pill subtle">{{ plan.duration_seconds }}s</span>
    </div>

    <p class="summary">{{ plan.summary || '暂无简介' }}</p>

    <footer class="foot" @click.stop>
      <span class="time">{{ formatDate(plan.updated_at) }}</span>
      <div class="actions">
        <el-button text type="primary" size="small" :icon="Edit" @click="$emit('open', plan)">编辑</el-button>
        <el-dropdown trigger="click" @command="onCommand">
          <el-button text size="small">
            更多<el-icon class="el-icon--right"><MoreFilled /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="export">导出</el-dropdown-item>
              <el-dropdown-item command="duplicate">复制</el-dropdown-item>
              <el-dropdown-item command="remove" divided>
                <span class="danger">删除</span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Edit, MoreFilled } from '@element-plus/icons-vue'

import { findDirectionLabel } from '@/data/directions'
import type { VideoPlan } from '@/types/api'

const props = defineProps<{ plan: VideoPlan }>()
const emit = defineEmits<{
  (e: 'open' | 'duplicate' | 'remove' | 'export', plan: VideoPlan): void
}>()

const statusLabel = computed(() => {
  switch (props.plan.status) {
    case 'draft': return '草稿'
    case 'optimizing': return '优化中'
    case 'confirmed': return '已确认'
    case 'completed': return '已完成'
    default: return ''
  }
})
const statusTone = computed(() => {
  switch (props.plan.status) {
    case 'optimizing': return 'warning'
    case 'confirmed':
    case 'completed': return 'success'
    default: return 'info'
  }
})

function onCommand(cmd: 'export' | 'duplicate' | 'remove') {
  emit(cmd, props.plan)
}

function formatDate(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const that = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const diffDays = Math.round((today.getTime() - that.getTime()) / 86400000)
  if (diffDays === 0) return '今天 ' + d.toTimeString().slice(0, 5)
  if (diffDays === 1) return '昨天 ' + d.toTimeString().slice(0, 5)
  if (diffDays < 7) return `${diffDays} 天前`
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
</script>

<style scoped>
.plan-card {
  background: var(--vp-surface);
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-lg);
  padding: 16px 16px 12px;
  display: flex; flex-direction: column;
  cursor: pointer;
  transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease;
  height: 100%;
  min-height: 190px;
  position: relative;
  overflow: hidden;
  animation: vp-fade-up .35s ease both;
}
.plan-card::before {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--vp-border-strong) 30%, var(--vp-border-strong) 70%, transparent);
  opacity: 0.55;
}
.plan-card[data-status="optimizing"]::before {
  background: linear-gradient(90deg, transparent, var(--vp-warning) 30%, var(--vp-warning) 70%, transparent);
  opacity: 0.7;
}
.plan-card[data-status="confirmed"]::before,
.plan-card[data-status="completed"]::before {
  background: linear-gradient(90deg, transparent, var(--vp-success) 30%, var(--vp-success) 70%, transparent);
  opacity: 0.7;
}
.plan-card[data-status="draft"]::before {
  background: linear-gradient(90deg, transparent, var(--vp-accent) 30%, var(--vp-accent) 70%, transparent);
  opacity: 0.55;
}
.plan-card:hover::before { opacity: 1; }
.plan-card:hover {
  border-color: var(--vp-border-strong);
  box-shadow: var(--vp-shadow-md);
  transform: translateY(-2px);
}
.plan-card:active { transform: translateY(-1px); }
.plan-card:focus-visible {
  outline: 2px solid var(--vp-primary);
  outline-offset: 2px;
}

.row-1 { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.title {
  margin: 0; flex: 1;
  font-size: 15px; font-weight: 600;
  color: var(--vp-text-1);
  line-height: 1.4;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  min-height: 42px;
}

.vp-status { flex-shrink: 0; }

.meta { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 10px; }
.meta-pill {
  font-size: 11.5px; font-weight: 500;
  padding: 2px 8px; border-radius: var(--vp-r-pill);
  background: var(--vp-primary-soft); color: var(--vp-primary);
}
.meta-pill.subtle { background: var(--vp-info-soft); color: var(--vp-text-2); }

.summary {
  color: var(--vp-text-3); font-size: 13px; line-height: 1.5;
  margin: 0 0 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 39px;
}

.foot {
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--vp-divider);
  display: flex; justify-content: space-between; align-items: center;
}
.time { font-size: 12px; color: var(--vp-text-3); }
.actions { display: flex; gap: 2px; align-items: center; }
.danger { color: var(--vp-danger); }

@media (max-width: 560px) {
  .plan-card { min-height: auto; }
}
</style>
