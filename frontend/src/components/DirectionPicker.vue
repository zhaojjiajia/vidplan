<template>
  <div class="picker">
    <div class="block">
      <h3>选择创作方向</h3>
      <p class="hint">先选大类,再选具体方向。</p>

      <div class="cat-grid">
        <div
          v-for="cat in CATEGORIES"
          :key="cat.key"
          :class="['cat-card', { active: category === cat.key }]"
          role="button"
          tabindex="0"
          @click="category = cat.key"
          @keydown.enter.space.prevent="category = cat.key"
        >
          <div class="cat-head">
            <h4>{{ cat.label }}</h4>
            <span v-if="category === cat.key" class="check">
              <el-icon><Check /></el-icon>
            </span>
          </div>
          <p class="hint">{{ cat.desc }}</p>
          <span class="cat-count">{{ DIRECTIONS[cat.key].length }} 个方向</span>
        </div>
      </div>
    </div>

    <div v-if="category" class="block">
      <h4>具体方向</h4>
      <p class="hint">选择和你的创作内容最接近的方向。</p>
      <div class="dir-grid">
        <div
          v-for="d in DIRECTIONS[category]"
          :key="d.key"
          :class="['dir-card', { active: direction === d.key }]"
          role="button"
          tabindex="0"
          @click="direction = d.key"
          @keydown.enter.space.prevent="direction = d.key"
        >
          <strong>{{ d.label }}</strong>
          <span class="hint">{{ d.desc }}</span>
        </div>
      </div>
    </div>

    <div v-if="direction" class="selected-summary">
      <span>已选择</span>
      <strong>{{ selectedLabel }}</strong>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check } from '@element-plus/icons-vue'

import { CATEGORIES, DIRECTIONS, type Category } from '@/data/directions'

const props = defineProps<{ category: Category | ''; direction: string }>()
const emit = defineEmits<{
  (e: 'update:category', v: Category | ''): void
  (e: 'update:direction', v: string): void
}>()

const category = computed({
  get: () => props.category,
  set: (v) => {
    emit('update:category', v)
    emit('update:direction', '')
  },
})
const direction = computed({
  get: () => props.direction,
  set: (v) => emit('update:direction', v),
})
const selectedLabel = computed(() => {
  if (!props.category || !props.direction) return ''
  return DIRECTIONS[props.category].find((item) => item.key === props.direction)?.label || props.direction
})
</script>

<style scoped>
.picker { display: flex; flex-direction: column; gap: 28px; }
.block h3, .block h4 { margin-bottom: 6px; }
.hint { color: var(--vp-text-3); font-size: 13px; margin-bottom: 14px; line-height: 1.5; }

.cat-grid {
  display: grid; gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}
.cat-card {
  cursor: pointer;
  background: var(--vp-surface);
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-lg);
  padding: 18px;
  transition: border-color .15s ease, box-shadow .15s ease, background .15s ease, transform .15s ease;
}
.cat-card:hover { border-color: var(--vp-border-strong); transform: translateY(-1px); }
.cat-card.active {
  border-color: var(--vp-primary);
  background: var(--vp-primary-soft);
  box-shadow: 0 0 0 1px var(--vp-primary) inset;
  transform: none;
}
.cat-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.cat-head h4 { margin: 0; }
.cat-count {
  display: inline-flex;
  margin-top: 2px;
  color: var(--vp-text-3);
  font-size: 12px;
  font-weight: 500;
}
.check {
  width: 22px; height: 22px;
  border-radius: 50%;
  background: var(--vp-primary); color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
}
.check :deep(svg) { width: 14px; height: 14px; }

.dir-grid {
  display: grid; gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}
.dir-card {
  cursor: pointer;
  background: var(--vp-surface);
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-md);
  padding: 12px 14px;
  transition: border-color .15s ease, background .15s ease, transform .15s ease;
  display: flex; flex-direction: column; gap: 2px;
  min-height: 64px;
}
.dir-card:hover { border-color: var(--vp-border-strong); transform: translateY(-1px); }
.dir-card.active {
  border-color: var(--vp-primary);
  background: var(--vp-primary-soft);
  box-shadow: 0 0 0 1px var(--vp-primary) inset;
  transform: none;
}
.dir-card strong { font-size: 14px; font-weight: 600; color: var(--vp-text-1); }
.dir-card .hint { font-size: 12.5px; margin: 0; }
.selected-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-md);
  background: var(--vp-surface-alt);
}
.selected-summary span {
  color: var(--vp-text-3);
  font-size: 12.5px;
}
.selected-summary strong {
  color: var(--vp-primary);
  font-size: 13.5px;
}
</style>
