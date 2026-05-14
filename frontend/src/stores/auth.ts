import { defineStore } from 'pinia'

import { authApi } from '@/api/auth'
import type { User } from '@/types/api'

const ACCESS_KEY = 'vidplan_access'
const REFRESH_KEY = 'vidplan_refresh'

interface State {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
}

export const useAuthStore = defineStore('auth', {
  state: (): State => ({
    accessToken: localStorage.getItem(ACCESS_KEY),
    refreshToken: localStorage.getItem(REFRESH_KEY),
    user: null,
  }),

  getters: {
    isLoggedIn: (s) => !!s.refreshToken,
  },

  actions: {
    async login(username: string, password: string) {
      const tokens = await authApi.login(username, password)
      this.accessToken = tokens.access
      this.refreshToken = tokens.refresh
      localStorage.setItem(ACCESS_KEY, tokens.access)
      localStorage.setItem(REFRESH_KEY, tokens.refresh)
      await this.fetchMe()
    },

    async fetchMe() {
      try {
        this.user = await authApi.me()
      } catch (err) {
        if (!this.refreshToken) throw err
        await this.refreshAccessToken()
        this.user = await authApi.me()
      }
    },

    setAccessToken(access: string) {
      this.accessToken = access
      localStorage.setItem(ACCESS_KEY, access)
    },

    async refreshAccessToken() {
      if (!this.refreshToken) throw new Error('缺少刷新令牌')
      const tokens = await authApi.refresh(this.refreshToken)
      this.setAccessToken(tokens.access)
      return tokens.access
    },

    logout() {
      this.accessToken = null
      this.refreshToken = null
      this.user = null
      localStorage.removeItem(ACCESS_KEY)
      localStorage.removeItem(REFRESH_KEY)
    },
  },
})
