import { computed, readonly, ref } from 'vue'

export type AppTheme = 'white' | 'warm'

const THEME_KEY = 'vp.theme'
const currentTheme = ref<AppTheme>('white')

function normalizeTheme(value: string | null): AppTheme {
  return value === 'warm' ? 'warm' : 'white'
}

function applyTheme(theme: AppTheme) {
  document.documentElement.dataset.theme = theme
  document.documentElement.classList.remove('dark')
}

export function initTheme() {
  const theme = normalizeTheme(localStorage.getItem(THEME_KEY))
  currentTheme.value = theme
  localStorage.setItem(THEME_KEY, theme)
  applyTheme(theme)
}

export function setTheme(theme: AppTheme) {
  currentTheme.value = theme
  localStorage.setItem(THEME_KEY, theme)
  applyTheme(theme)
}

export function toggleTheme() {
  setTheme(currentTheme.value === 'white' ? 'warm' : 'white')
}

export function useTheme() {
  return {
    currentTheme: readonly(currentTheme),
    isWhiteTheme: computed(() => currentTheme.value === 'white'),
    setTheme,
    toggleTheme,
  }
}
