import { http } from './index'
import type { User } from '@/types/api'

export interface TokenPair {
  access: string
  refresh: string
}

export const authApi = {
  login: (username: string, password: string) =>
    http.post<TokenPair>('/auth/login/', { username, password }).then((r) => r.data),

  register: (username: string, password: string, nickname?: string) =>
    http.post<User>('/auth/register/', { username, password, nickname }).then((r) => r.data),

  refresh: (refresh: string) =>
    http.post<{ access: string }>('/auth/refresh/', { refresh }).then((r) => r.data),

  me: () => http.get<User>('/auth/me/').then((r) => r.data),
}
