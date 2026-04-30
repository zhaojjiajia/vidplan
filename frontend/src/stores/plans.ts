import { defineStore } from 'pinia'

import { plansApi } from '@/api/plans'
import { isAITaskResponse } from '@/api/aiTasks'
import type { VideoPlan } from '@/types/api'

interface State {
  list: VideoPlan[]
  current: VideoPlan | null
  loading: boolean
}

export const usePlansStore = defineStore('plans', {
  state: (): State => ({ list: [], current: null, loading: false }),

  actions: {
    async fetchList() {
      this.loading = true
      try {
        const data = await plansApi.list()
        this.list = data.results
      } finally {
        this.loading = false
      }
    },

    async fetch(id: string) {
      this.loading = true
      try {
        this.current = await plansApi.get(id)
      } finally {
        this.loading = false
      }
    },

    async save(id: string, patch: Partial<VideoPlan>) {
      const updated = await plansApi.patch(id, patch)
      this.current = updated
      const idx = this.list.findIndex((p) => p.id === id)
      if (idx >= 0) this.list[idx] = updated
      return updated
    },

    async optimize(id: string, scope: 'full' | 'title' | 'hook' | 'storyboard' | 'editing' | 'ai_prompt' = 'full') {
      const updated = await plansApi.optimize(id, scope)
      if (isAITaskResponse(updated)) return updated
      this.current = updated
      return updated
    },

    async remove(id: string) {
      await plansApi.remove(id)
      this.list = this.list.filter((p) => p.id !== id)
    },
  },
})
