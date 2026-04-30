import { http } from './index'

export type AIProvider = 'openai' | 'qwen'

export interface AISetting {
  provider: AIProvider
  model: string
  base_url: string
  api_key_masked: string
  has_api_key: boolean
  resolved_model: string
  resolved_base_url: string
}

export interface AISettingUpdate {
  provider?: AIProvider
  model?: string
  base_url?: string
  api_key?: string
}

export interface AISettingTestPayload {
  provider?: AIProvider
  api_key?: string
  model?: string
  base_url?: string
}

export interface AISettingTestResult {
  ok: boolean
  model?: string
  sample?: string
  error?: string
}

export const aiSettingsApi = {
  async get(): Promise<AISetting> {
    const { data } = await http.get<AISetting>('/ai-settings/')
    return data
  },
  async update(payload: AISettingUpdate): Promise<AISetting> {
    const { data } = await http.put<AISetting>('/ai-settings/', payload)
    return data
  },
  async test(payload: AISettingTestPayload = {}): Promise<AISettingTestResult> {
    const { data } = await http.post<AISettingTestResult>('/ai-settings/test/', payload)
    return data
  },
}

export const PROVIDER_PRESETS: Record<AIProvider, { label: string; defaultModel: string; defaultBaseUrl: string; hint: string }> = {
  openai: {
    label: 'OpenAI',
    defaultModel: 'gpt-4o',
    defaultBaseUrl: '',
    hint: '使用官方 OpenAI 接口。如使用代理可填 Base URL。',
  },
  qwen: {
    label: '通义千问 (Qwen / 阿里云百炼)',
    defaultModel: 'qwen-plus',
    defaultBaseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    hint: '通过阿里云百炼 OpenAI 兼容模式调用。常用模型: qwen-plus / qwen-max / qwen-turbo。',
  },
}
