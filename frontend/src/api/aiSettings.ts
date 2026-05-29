import { http } from './index'

export type AIProvider = 'openai' | 'anthropic'
export type StoredAIProvider = AIProvider | 'qwen'
export type AIProviderIcon = 'chatgpt' | 'anthropic'

export interface AISetting {
  provider: StoredAIProvider
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

export interface AIProviderPreset {
  label: string
  defaultModel: string
  defaultBaseUrl: string
  hint: string
  icon: AIProviderIcon
}

export const PROVIDER_PRESETS: Record<AIProvider, AIProviderPreset> = {
  openai: {
    label: 'ChatGPT',
    defaultModel: 'gpt-4o',
    defaultBaseUrl: '',
    hint: '使用 ChatGPT 官方接口。如使用代理可填 Base URL。',
    icon: 'chatgpt',
  },
  anthropic: {
    label: 'Anthropic',
    defaultModel: 'claude-3-5-sonnet-latest',
    defaultBaseUrl: '',
    hint: '使用 Anthropic Messages API。如使用代理可填 Base URL。',
    icon: 'anthropic',
  },
}
