<template>
  <div class="vp-page vp-page--narrow ai-settings">
    <header class="vp-section-head">
      <div>
        <h2>AI 设置</h2>
        <p>配置自己的大模型 API Key,所有 AI 生成与优化都会用你这里填写的密钥调用。</p>
      </div>
    </header>

    <section v-loading="loading" class="card">
      <div class="settings-grid">
        <aside class="provider-panel">
          <button
            v-for="(p, key) in PROVIDER_PRESETS"
            :key="key"
            :class="['provider-card', { active: form.provider === key }]"
            type="button"
            @click="setProvider(key)"
          >
            <span class="provider-mark">{{ providerInitial(p.label) }}</span>
            <span>
              <strong>{{ p.label }}</strong>
              <small>{{ p.defaultModel }}</small>
            </span>
          </button>
        </aside>

        <div class="card-body">
          <div class="provider-copy">
            <span class="vp-status" :data-tone="serverData.has_api_key ? 'success' : 'warning'">
              {{ serverData.has_api_key ? '已配置密钥' : '未配置密钥' }}
            </span>
            <p class="hint">{{ currentPreset.hint }}</p>
          </div>

          <el-form :model="form" label-position="top">
            <el-form-item label="API Key">
              <el-input
                v-model="form.api_key"
                type="password"
                show-password
                :placeholder="apiKeyPlaceholder"
                autocomplete="off"
                size="large"
              />
              <p v-if="serverData.has_api_key && !form.api_key" class="hint">
                已保存:<span class="vp-mono">{{ serverData.api_key_masked }}</span> · 留空保持不变
              </p>
            </el-form-item>

            <div class="form-row">
              <el-form-item label="模型">
                <el-input v-model="form.model" :placeholder="`默认 ${currentPreset.defaultModel}`" />
              </el-form-item>
              <el-form-item label="Base URL · 可选">
                <el-input
                  v-model="form.base_url"
                  :placeholder="currentPreset.defaultBaseUrl || 'https://api.openai.com/v1'"
                />
              </el-form-item>
            </div>
          </el-form>
        </div>
      </div>

      <footer class="card-foot">
        <div class="footnote">
          当前模型:
          <span class="vp-mono">{{ form.model || currentPreset.defaultModel }}</span>
        </div>
        <div class="actions">
          <el-button :icon="Connection" :loading="testing" @click="onTest">测试连接</el-button>
          <el-button type="primary" :icon="Check" :loading="saving" @click="onSave">保存</el-button>
        </div>
      </footer>

      <el-alert
        v-if="testResult"
        :type="testResult.ok ? 'success' : 'error'"
        :title="testResult.ok ? `连接成功 · 模型 ${testResult.model}` : `连接失败:${testResult.error}`"
        :description="testResult.ok ? `示例输出:${testResult.sample}` : ''"
        :closable="true"
        @close="testResult = null"
        class="result"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Connection } from '@element-plus/icons-vue'

import {
  aiSettingsApi,
  PROVIDER_PRESETS,
  type AIProvider,
  type AISetting,
  type AISettingTestResult,
} from '@/api/aiSettings'

const loading = ref(true)
const saving = ref(false)
const testing = ref(false)
const testResult = ref<AISettingTestResult | null>(null)

const serverData = reactive<AISetting>({
  provider: 'openai',
  model: '',
  base_url: '',
  api_key_masked: '',
  has_api_key: false,
  resolved_model: '',
  resolved_base_url: '',
})

const form = reactive({
  provider: 'openai' as AIProvider,
  api_key: '',
  model: '',
  base_url: '',
})

const currentPreset = computed(() => PROVIDER_PRESETS[form.provider])

const apiKeyPlaceholder = computed(() =>
  serverData.has_api_key ? '留空保持现有 Key 不变' : '请输入 API Key,例如 sk-xxx 或 dashscope key'
)

function applyServer(d: AISetting) {
  Object.assign(serverData, d)
  form.provider = d.provider
  form.model = d.model
  form.base_url = d.base_url
  form.api_key = ''
}

function setProvider(provider: AIProvider) {
  form.provider = provider
  testResult.value = null
}

function providerInitial(label: string) {
  return label.trim().slice(0, 1).toUpperCase()
}

async function load() {
  loading.value = true
  try {
    const d = await aiSettingsApi.get()
    applyServer(d)
  } finally {
    loading.value = false
  }
}

async function onSave() {
  saving.value = true
  try {
    const payload = {
      provider: form.provider,
      model: form.model,
      base_url: form.base_url,
      ...(form.api_key ? { api_key: form.api_key } : {}),
    }
    const d = await aiSettingsApi.update(payload)
    applyServer(d)
    ElMessage.success('已保存')
  } finally {
    saving.value = false
  }
}

async function onTest() {
  testing.value = true
  testResult.value = null
  try {
    const r = await aiSettingsApi.test({
      provider: form.provider,
      model: form.model || undefined,
      base_url: form.base_url || undefined,
      ...(form.api_key ? { api_key: form.api_key } : {}),
    })
    testResult.value = r
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.ai-settings { padding-top: 32px; }
.card {
  background: var(--vp-surface);
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-xl);
  overflow: hidden;
  box-shadow: var(--vp-shadow-xs);
}
.settings-grid {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
}
.provider-panel {
  padding: 20px;
  border-right: 1px solid var(--vp-divider);
  background: var(--vp-surface-alt);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.provider-card {
  width: 100%;
  min-height: 64px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-md);
  background: var(--vp-surface);
  color: var(--vp-text-2);
  text-align: left;
  cursor: pointer;
  position: relative;
  transition: border-color .15s ease, background .15s ease, transform .12s ease;
}
.provider-card:hover {
  border-color: var(--vp-border-strong);
  transform: translateY(-1px);
}
.provider-card.active {
  border-color: var(--vp-primary);
  background: var(--vp-primary-soft);
  color: var(--vp-text-1);
  box-shadow: 0 0 0 1px var(--vp-primary) inset;
  transform: none;
}
.provider-card.active::after {
  /* 选中右上角对勾 */
  content: "✓";
  position: absolute;
  top: 8px; right: 10px;
  width: 16px; height: 16px;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 50%;
  background: var(--vp-primary);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
}
.provider-mark {
  width: 36px;
  height: 36px;
  border-radius: var(--vp-r-md);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--vp-text-1), var(--vp-text-2));
  color: var(--vp-bg);
  font-weight: 800;
  font-size: 15px;
  flex-shrink: 0;
}
.provider-card.active .provider-mark {
  background: linear-gradient(135deg, #e78b9a, var(--vp-primary) 58%, #8d2936);
  color: #fff;
}
.provider-card strong {
  display: block;
  font-size: 13.5px;
  font-weight: 600;
  margin-bottom: 2px;
  color: inherit;
}
.provider-card small {
  color: var(--vp-text-3);
  font-size: 11.5px;
  font-family: var(--vp-mono);
}
.card-body { padding: 24px 28px; }
.provider-copy {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}
.card-foot {
  padding: 14px 28px;
  background: var(--vp-surface-alt);
  border-top: 1px solid var(--vp-divider);
  display: flex; justify-content: space-between; align-items: center;
  gap: 16px;
}
.footnote { font-size: 12.5px; color: var(--vp-text-3); }
.actions { display: flex; gap: 10px; }

.hint { color: var(--vp-text-3); font-size: 12.5px; margin-top: 6px; line-height: 1.5; }
.form-row {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 16px;
}
.result { margin: 16px 28px 24px; }

@media (max-width: 720px) {
  .settings-grid { grid-template-columns: 1fr; }
  .provider-panel {
    border-right: none;
    border-bottom: 1px solid var(--vp-divider);
  }
  .provider-copy { flex-direction: column; }
  .form-row { grid-template-columns: 1fr; }
  .card-body { padding: 20px; }
  .card-foot { flex-direction: column; align-items: stretch; padding: 16px 20px; }
  .actions { flex-direction: column; }
}
</style>
