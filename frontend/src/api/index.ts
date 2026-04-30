import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

import { useAuthStore } from '@/stores/auth'

export const http = axios.create({
  baseURL: '/api/v1',
  timeout: 240_000,
})

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const auth = useAuthStore()
  if (auth.accessToken) {
    config.headers.Authorization = `Bearer ${auth.accessToken}`
  }
  return config
})

http.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError<{ detail?: string } | Blob>) => {
    if (error.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
      window.location.href = '/login'
    } else {
      const msg = await getErrorMessage(error)
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  }
)

async function getErrorMessage(error: AxiosError<{ detail?: string } | Blob>): Promise<string> {
  const data = error.response?.data
  if (data instanceof Blob) {
    try {
      const text = await data.text()
      const parsed = JSON.parse(text) as { detail?: string }
      if (parsed.detail) return parsed.detail
    } catch {
      // 不是 JSON 错误体时沿用 Axios 错误文案。
    }
  } else if (data?.detail) {
    return data.detail
  }
  return error.message
}
