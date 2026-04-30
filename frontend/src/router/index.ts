import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: () => import('@/views/Home.vue') },
  { path: '/login', name: 'login', component: () => import('@/views/Login.vue'), meta: { guest: true } },
  { path: '/register', name: 'register', component: () => import('@/views/Register.vue'), meta: { guest: true } },
  {
    path: '/app',
    component: () => import('@/layouts/DefaultLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: { name: 'my-plans' } },
      { path: 'me/plans', name: 'my-plans', component: () => import('@/views/MyPlans.vue') },
      { path: 'me/series', name: 'my-series', component: () => import('@/views/MySeries.vue') },
      { path: 'me/assets/characters', name: 'asset-characters', component: () => import('@/views/AssetLibrary.vue'), meta: { assetType: 'characters' } },
      { path: 'me/assets/styles', name: 'asset-styles', component: () => import('@/views/AssetLibrary.vue'), meta: { assetType: 'styles' } },
      { path: 'me/assets/worldviews', name: 'asset-worldviews', component: () => import('@/views/AssetLibrary.vue'), meta: { assetType: 'worldviews' } },
      { path: 'me/assets/columns', name: 'asset-columns', component: () => import('@/views/AssetLibrary.vue'), meta: { assetType: 'columns' } },
      { path: 'plan/new', name: 'plan-new', component: () => import('@/views/PlanWizard.vue') },
      { path: 'plan/:id', name: 'plan-edit', component: () => import('@/views/PlanEditor.vue') },
      { path: 'series/new', name: 'series-new', component: () => import('@/views/SeriesEditor.vue') },
      { path: 'series/:id', name: 'series-edit', component: () => import('@/views/SeriesEditor.vue') },
      { path: 'settings/ai', name: 'ai-settings', component: () => import('@/views/AISettings.vue') },
      { path: 'garden', name: 'flower-garden', component: () => import('@/views/FlowerGarden.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (auth.isLoggedIn && !auth.user) {
    try { await auth.fetchMe() } catch { /* token expired; let request interceptor handle */ }
  }
  if (to.meta.guest && auth.isLoggedIn) {
    return { name: 'my-plans' }
  }
})

export default router
