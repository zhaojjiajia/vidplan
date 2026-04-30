<template>
  <div class="shell" :class="{ collapsed }">
    <aside class="sidebar">
      <div class="sidebar-top">
        <router-link to="/" class="brand" aria-label="VidPlan AI">
          <span class="brand-name">VidPlan</span>
        </router-link>
        <el-tooltip :content="collapsed ? '展开' : '收起'" placement="right" :show-after="200">
          <button class="collapse-btn" @click="toggleCollapse" :aria-label="collapsed ? '展开侧边栏' : '收起侧边栏'">
            <el-icon><component :is="collapsed ? Expand : Fold" /></el-icon>
          </button>
        </el-tooltip>
      </div>

      <nav class="nav">
        <div class="nav-group">
          <button class="nav-cta" @click="router.push('/app/plan/new')">
            <el-icon><Plus /></el-icon>
            <span>创建方案</span>
          </button>
        </div>

        <div class="nav-group">
          <div class="nav-label">工作台</div>
          <NavItem
            v-for="item in primaryNav"
            :key="item.path"
            :path="item.path"
            :label="item.label"
            :icon="item.icon"
            :active="isActive(item.path)"
            :collapsed="collapsed"
          />
        </div>

        <div class="nav-group">
          <div class="nav-label">资产库</div>
          <NavItem
            v-for="item in assetNav"
            :key="item.path"
            :path="item.path"
            :label="item.label"
            :icon="item.icon"
            :active="isActive(item.path)"
            :collapsed="collapsed"
          />
        </div>

        <div class="nav-group">
          <div class="nav-label">系统</div>
          <NavItem
            path="/app/settings/ai"
            label="AI 设置"
            :icon="Setting"
            :active="isActive('/app/settings/ai')"
            :collapsed="collapsed"
          />
          <NavItem
            path="/app/garden"
            label="赏花"
            :icon="Cherry"
            :active="isActive('/app/garden')"
            :collapsed="collapsed"
          />
        </div>
      </nav>

      <div class="bottom">
        <div class="user-pod">
          <div class="user-info">
            <span class="vp-avatar">{{ initial }}</span>
            <div v-if="!collapsed" class="user-meta">
              <div class="user-name">{{ auth.user?.nickname || auth.user?.username || '未登录' }}</div>
            </div>
          </div>
          <el-tooltip content="退出登录" placement="top" :show-after="200">
            <button class="logout-btn" @click="onLogout" aria-label="退出登录">
              <el-icon><SwitchButton /></el-icon>
            </button>
          </el-tooltip>
        </div>
      </div>
    </aside>

    <main class="content">
      <header class="workspace-topbar">
        <div class="workspace-crumbs" aria-label="当前位置">
          <span class="crumb-section">{{ workspaceSection }}</span>
          <span class="crumb-sep" aria-hidden="true">›</span>
          <strong class="crumb-title">{{ workspaceTitle }}</strong>
        </div>
        <div class="workspace-actions">
          <span class="workspace-state" :title="auth.user?.username ? '会话有效' : '未登录'">
            <span class="state-dot" />
            {{ auth.user?.username ? '已登录' : '访客' }}
          </span>
        </div>
      </header>

      <div class="workspace-body">
        <router-view v-slot="{ Component }">
          <transition name="vp-page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>

  </div>
</template>

<script setup lang="ts">
import { computed, h, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Avatar,
  Box,
  Cherry,
  Collection,
  Compass,
  Document,
  Expand,
  Files,
  Fold,
  Plus,
  Setting,
  SwitchButton,
} from '@element-plus/icons-vue'

import { useAuthStore } from '@/stores/auth'

// 内联导航项，避免为一个小组件额外拆文件。
const NavItem = (props: {
  path: string
  label: string
  icon: any
  active: boolean
  collapsed: boolean
}) =>
  h(
    'a',
    {
      href: props.path,
      class: ['nav-item', { active: props.active }],
      onClick: (e: Event) => {
        e.preventDefault()
        router.push(props.path)
      },
      'aria-current': props.active ? 'page' : undefined,
    },
    [
      h('span', { class: 'nav-icon' }, [h(props.icon)]),
      props.collapsed ? null : h('span', { class: 'nav-text' }, props.label),
    ]
  )

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const COLLAPSE_KEY = 'vp.sidebar.collapsed'
const collapsed = ref(localStorage.getItem(COLLAPSE_KEY) === '1')

function toggleCollapse() {
  collapsed.value = !collapsed.value
  localStorage.setItem(COLLAPSE_KEY, collapsed.value ? '1' : '0')
}

const primaryNav = [
  { path: '/app/me/plans',  label: '我的方案', icon: Document },
  { path: '/app/me/series', label: '我的系列', icon: Files },
]

const assetNav = [
  { path: '/app/me/assets/characters', label: '人物', icon: Avatar },
  { path: '/app/me/assets/styles',     label: '风格', icon: Compass },
  { path: '/app/me/assets/worldviews', label: '世界观', icon: Box },
  { path: '/app/me/assets/columns',    label: '栏目', icon: Collection },
]

function isActive(path: string) {
  return route.path === path || route.path.startsWith(path + '/')
}

const initial = computed(() => {
  const name = auth.user?.nickname || auth.user?.username || '?'
  return name.trim().slice(0, 1).toUpperCase()
})

const workspaceSection = computed(() => {
  if (route.path.includes('/assets/')) return '资产库'
  if (route.path.includes('/settings/') || route.path.includes('/garden')) return '系统'
  if (route.path.includes('/series')) return '系列'
  return '工作台'
})
const workspaceTitle = computed(() => {
  if (route.name === 'my-plans') return '我的方案'
  if (route.name === 'my-series') return '我的系列'
  if (route.name === 'plan-new') return '创建方案'
  if (route.name === 'plan-edit') return '方案编辑器'
  if (route.name === 'series-new') return '新建系列'
  if (route.name === 'series-edit') return '系列编辑器'
  if (route.name === 'ai-settings') return 'AI 设置'
  if (route.name === 'flower-garden') return '赏花'
  if (route.name === 'asset-characters') return '人物资产'
  if (route.name === 'asset-styles') return '风格资产'
  if (route.name === 'asset-worldviews') return '世界观资产'
  if (route.name === 'asset-columns') return '栏目资产'
  return 'VidPlan'
})

function onLogout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: var(--vp-sidebar-w) 1fr;
  min-height: 100vh;
  background: transparent;
  font-size: 20px;
  transition: grid-template-columns .22s ease;
}
.shell.collapsed { grid-template-columns: 64px 1fr; }

/* ----- 侧边栏 ----- */
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--vp-divider);
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--vp-surface) 92%, transparent), color-mix(in srgb, var(--vp-surface-alt) 74%, transparent)),
    var(--vp-surface);
  padding: 14px 12px 12px;
  gap: 8px;
  overflow: hidden;
}
.shell.collapsed .sidebar { padding-left: 8px; padding-right: 8px; }

.sidebar-top {
  display: flex; align-items: center; justify-content: space-between;
  gap: 8px;
  padding: 4px 6px 14px;
  border-bottom: 1px solid var(--vp-divider);
}
.shell.collapsed .sidebar-top { gap: 2px; padding-left: 0; padding-right: 0; }
.brand {
  display: flex; align-items: center;
  text-decoration: none;
  color: var(--vp-text-1);
  min-width: 0;
}
.brand-name {
  font-family: var(--vp-font-display);
  font-weight: 700; font-size: 24px;
  letter-spacing: 0;
  white-space: nowrap;
  opacity: 1;
  transition: opacity .18s ease;
}
.shell.collapsed .brand { display: none; }

.collapse-btn {
  width: 48px; height: 34px;
  border: none; background: transparent;
  color: var(--vp-text-3);
  border-radius: var(--vp-r-sm);
  display: inline-flex; align-items: center; justify-content: center;
  cursor: pointer;
  transition: background .12s ease, color .12s ease;
}
.collapse-btn:hover { background: var(--vp-surface-alt); color: var(--vp-text-1); }
.collapse-btn :deep(svg) { width: 18px; height: 18px; }
.shell.collapsed .collapse-btn { width: 100%; height: 34px; }

.nav { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; padding-top: 4px; }
.nav-group { display: flex; flex-direction: column; gap: 2px; padding: 6px 0 8px; }
.nav-label {
  text-transform: uppercase;
  font-size: 14px;
  letter-spacing: 0;
  color: var(--vp-text-4);
  padding: 4px 10px 6px;
  font-weight: 600;
  white-space: nowrap;
  transition: opacity .18s ease;
}
.shell.collapsed .nav-label { opacity: 0; height: 8px; padding: 0; overflow: hidden; }

.nav-item {
  display: flex; align-items: center; gap: 10px;
  min-height: 40px;
  padding: 7px 10px;
  border-radius: var(--vp-r-sm);
  font-size: 18px;
  color: var(--vp-text-2);
  text-decoration: none;
  font-weight: 500;
  position: relative;
  transition: background .12s ease, color .12s ease;
}
.nav-item:hover { background: var(--vp-surface-alt); color: var(--vp-text-1); }
.nav-item.active {
  background: var(--vp-primary-soft);
  color: var(--vp-primary);
}
.nav-item.active::before {
  content: ""; position: absolute;
  left: -12px; top: 50%; transform: translateY(-50%);
  width: 3px; height: 16px;
  background: var(--vp-primary);
  border-radius: 0 3px 3px 0;
}
.nav-icon {
  width: 16px; height: 16px;
  display: inline-flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  color: var(--vp-text-3);
}
.nav-item.active .nav-icon { color: var(--vp-primary); }
.nav-icon :deep(svg) { width: 16px; height: 16px; }
.nav-text { white-space: nowrap; }

.nav-cta {
  width: 100%;
  display: flex; align-items: center; justify-content: flex-start; gap: 10px;
  padding: 11px 12px;
  background: var(--vp-primary);
  color: #fff;
  border: 1px solid var(--vp-primary);
  border-radius: var(--vp-r-sm);
  font-size: 18px;
  font-weight: 500;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: background .15s ease, transform .12s ease, box-shadow .15s ease;
  box-shadow:
    0 1px 2px rgba(141, 41, 54, 0.2),
    0 8px 20px rgba(181, 69, 88, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.10);
}
.nav-cta::before {
  /* 微妙顶部高光 */
  content: "";
  position: absolute;
  inset: 0 0 60% 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.10), transparent);
  pointer-events: none;
}
.nav-cta:hover {
  background: var(--vp-primary-hover);
  transform: translateY(-0.5px);
  box-shadow:
    0 10px 22px rgba(181, 69, 88, 0.22),
    inset 0 1px 0 rgba(255, 255, 255, 0.12);
}
.nav-cta:active { transform: translateY(0); box-shadow: 0 1px 2px rgba(141, 41, 54, 0.2); }
.nav-cta :deep(svg) { width: 14px; height: 14px; flex-shrink: 0; position: relative; z-index: 1; }
.nav-cta > span { position: relative; z-index: 1; flex: 1; text-align: left; }
.shell.collapsed .nav-cta span { display: none; }
.shell.collapsed .nav-cta { padding: 9px 0; justify-content: center; }

/* ----- 底部操作区 ----- */
.bottom { display: flex; flex-direction: column; gap: 6px; border-top: 1px solid var(--vp-divider); padding-top: 8px; }
.user-pod {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px;
  border-radius: var(--vp-r-sm);
  transition: background .12s ease;
}
.user-pod:hover { background: var(--vp-surface-alt); }
.user-info { display: flex; align-items: center; gap: 10px; min-width: 0; }
.user-meta { min-width: 0; }
.user-name {
  font-size: 18px; font-weight: 600;
  color: var(--vp-text-1);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  max-width: 130px;
}
.logout-btn {
  width: 24px; height: 24px;
  border: none; background: transparent;
  color: var(--vp-text-3); border-radius: var(--vp-r-sm);
  display: inline-flex; align-items: center; justify-content: center;
  cursor: pointer;
  transition: background .12s ease, color .12s ease;
}
.logout-btn:hover { background: var(--vp-surface-hover); color: var(--vp-text-1); }
.logout-btn :deep(svg) { width: 14px; height: 14px; }
.shell.collapsed .user-meta { display: none; }
.shell.collapsed .logout-btn { display: none; }

/* ----- 内容区 ----- */
.content {
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.workspace-topbar {
  position: sticky;
  top: 0;
  z-index: 12;
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 28px;
  border-bottom: 1px solid var(--vp-divider);
  background: color-mix(in srgb, var(--vp-bg) 88%, transparent);
  backdrop-filter: blur(14px);
}
.workspace-crumbs {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  overflow: hidden;
}
.crumb-section {
  color: var(--vp-text-3);
  font-weight: 500;
  white-space: nowrap;
}
.crumb-sep {
  color: var(--vp-text-4);
  font-size: 14px;
  user-select: none;
}
.crumb-title {
  color: var(--vp-text-1);
  font-weight: 600;
  letter-spacing: -0.005em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.workspace-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.workspace-state {
  height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 11px 0 9px;
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-pill);
  background: var(--vp-surface);
  color: var(--vp-text-2);
  font-size: 16px;
  font-weight: 500;
}
.state-dot {
  position: relative;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--vp-success);
}
.state-dot::after {
  content: "";
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  background: var(--vp-success);
  opacity: 0.25;
  animation: vp-state-halo 2.4s ease-in-out infinite;
}
@keyframes vp-state-halo {
  0%, 100% { transform: scale(1);   opacity: 0.0; }
  50%      { transform: scale(1.6); opacity: 0.4; }
}
.workspace-body {
  min-width: 0;
  flex: 1;
}
.content :deep(.vp-page) {
  font-size: 20px;
}
.content :deep(.vp-section-head h2) {
  font-size: 36px;
}
.content :deep(.vp-section-head p),
.content :deep(.hint),
.content :deep(.muted) {
  font-size: 18px;
}
.content :deep(.el-form-item__label),
.content :deep(.el-input__inner),
.content :deep(.el-textarea__inner),
.content :deep(.el-select__placeholder),
.content :deep(.el-select__selected-item),
.content :deep(.el-checkbox__label),
.content :deep(.el-table),
.content :deep(.el-dialog),
.content :deep(.el-button) {
  font-size: 18px;
}
.content :deep(.el-dialog__title) {
  font-size: 22px;
}
.content :deep(.el-tag) {
  font-size: 15px;
  min-height: 24px;
}
.content :deep(.el-step__title) {
  font-size: 16px;
}

/* ----- 响应式 ----- */
@media (max-width: 880px) {
  .shell, .shell.collapsed { grid-template-columns: 1fr; }
  .sidebar {
    position: relative; height: auto;
    flex-direction: row; flex-wrap: wrap;
    padding: 10px 16px;
    border-right: none; border-bottom: 1px solid var(--vp-divider);
  }
  .sidebar-top { border-bottom: none; padding: 0; margin: 0 12px 0 0; }
  .nav { flex-direction: row; overflow-x: auto; flex: 1; padding-top: 0; }
  .nav-group { flex-direction: row; padding: 0; }
  .nav-label, .nav-cta, .collapse-btn, .bottom { display: none; }
  .nav-item.active::before { display: none; }
  .workspace-topbar {
    padding: 10px 16px;
    position: static;
  }
  .workspace-state { display: none; }
}

@media (max-width: 560px) {
  .workspace-topbar {
    align-items: stretch;
    flex-direction: column;
  }
  .workspace-actions .el-button {
    width: 100%;
  }
}
</style>
