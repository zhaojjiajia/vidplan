<template>
  <div class="empty">
    <div class="illu" aria-hidden="true">
      <slot name="icon">
        <svg viewBox="0 0 96 96" fill="none">
          <defs>
            <linearGradient id="vp-empty-grad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" :stop-color="primary" stop-opacity="0.3" />
              <stop offset="100%" :stop-color="primary" stop-opacity="0.06" />
            </linearGradient>
          </defs>
          <rect x="14" y="22" width="56" height="44" rx="8" fill="url(#vp-empty-grad)" />
          <rect x="14" y="22" width="56" height="44" rx="8"
                stroke="currentColor" stroke-opacity="0.25" stroke-width="1.5" />
          <path d="M22 32h28M22 40h22M22 48h26M22 56h18" stroke="currentColor" stroke-opacity="0.3"
                stroke-width="1.5" stroke-linecap="round" />
          <circle cx="68" cy="60" r="14" fill="white" :stroke="primary" stroke-width="1.6" />
          <path d="M62 60h12M68 54v12" :stroke="primary" stroke-width="1.6" stroke-linecap="round" />
        </svg>
      </slot>
    </div>
    <h3 v-if="title" class="title">{{ title }}</h3>
    <p v-if="description" class="desc">{{ description }}</p>
    <div v-if="$slots.action" class="action">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
  description?: string
}>()
// 使用 currentColor 的辅助色:从 CSS 变量解析,此处直接读取 primary 主色
// 由于 SVG 内 stop-color 不支持 var(),我们读取 computed style
import { computed } from 'vue'
const primary = computed(() => {
  if (typeof document === 'undefined') return '#b54558'
  return getComputedStyle(document.documentElement).getPropertyValue('--vp-primary').trim() || '#b54558'
})
</script>

<style scoped>
.empty {
  display: flex; flex-direction: column; align-items: center;
  text-align: center;
  padding: 64px 24px;
  color: var(--vp-text-2);
  animation: vp-fade-up .35s ease both;
}
.illu {
  width: 96px; height: 96px;
  display: inline-flex; align-items: center; justify-content: center;
  color: var(--vp-text-3);
  margin-bottom: 22px;
  position: relative;
}
.illu::before {
  /* 柔和光晕 */
  content: "";
  position: absolute;
  inset: 8px;
  border-radius: 50%;
  background: radial-gradient(closest-side, color-mix(in srgb, var(--vp-primary) 14%, transparent), transparent 75%);
  filter: blur(4px);
  z-index: -1;
}
.illu svg { width: 96px; height: 96px; }
.title { font-size: 16px; font-weight: 700; color: var(--vp-text-1); margin-bottom: 6px; letter-spacing: -0.005em; }
.desc { font-size: 13.5px; color: var(--vp-text-3); line-height: 1.6; max-width: 360px; }
.action { margin-top: 22px; }
</style>
