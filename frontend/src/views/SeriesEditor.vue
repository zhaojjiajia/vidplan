<template>
  <div class="series-editor" v-loading="loading">
    <div class="head">
      <div>
        <h2>{{ isNew ? '新建系列方案' : '编辑系列方案' }}</h2>
        <p class="muted">维护系列定位、单集模板、视觉风格和可复用资产。</p>
      </div>
      <div class="head-actions">
        <el-button @click="router.push('/app/me/series')">返回</el-button>
        <el-button type="primary" :icon="DocumentChecked" :loading="saving" @click="save">保存</el-button>
      </div>
    </div>

    <el-alert v-if="taskMessage" type="info" show-icon :closable="false" class="task-alert">
      <template #title>
        <div class="task-title">
          <span>{{ taskMessage }}</span>
          <el-progress :percentage="taskProgress" :stroke-width="6" class="task-progress" />
        </div>
      </template>
    </el-alert>

    <el-tabs>
      <el-tab-pane v-if="!isNew" label="概览">
        <div class="overview">
          <div class="overview-stats">
            <div v-for="item in overviewStats" :key="item.label" class="stat-tile">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>

          <el-row :gutter="16">
            <el-col :span="14">
              <el-card>
                <template #header>系列定位</template>
                <el-descriptions :column="1" border>
                  <el-descriptions-item v-for="item in positioningOverview" :key="item.label" :label="item.label">
                    {{ item.value || '未填写' }}
                  </el-descriptions-item>
                </el-descriptions>
              </el-card>

              <el-card class="mt">
                <template #header>单集模板</template>
                <el-table v-if="episodeTemplate.sections.length" :data="episodeTemplate.sections" stripe>
                  <el-table-column label="段落" prop="name" min-width="140" />
                  <el-table-column label="时长" prop="duration" width="120" />
                  <el-table-column label="目标" prop="goal" min-width="220" />
                </el-table>
                <div v-else class="muted">暂无结构段落</div>
                <div v-if="episodeTemplate.must_have.length" class="must-have">
                  <div class="sub-title">必备元素</div>
                  <el-tag v-for="item in episodeTemplate.must_have" :key="item" effect="plain" class="tag">
                    {{ item }}
                  </el-tag>
                </div>
              </el-card>

              <el-card class="mt">
                <template #header>最近单集</template>
                <el-table v-if="recentEpisodes.length" :data="recentEpisodes" stripe>
                  <el-table-column label="标题" prop="title" min-width="220" />
                  <el-table-column label="状态" width="100">
                    <template #default="{ row }">
                      <el-tag size="small" :type="episodeTagType(row.status)">{{ episodeStatusLabel(row.status) }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="时长" width="90">
                    <template #default="{ row }">{{ row.duration_seconds }}s</template>
                  </el-table-column>
                  <el-table-column label="操作" width="90">
                    <template #default="{ row }">
                      <el-button text type="primary" size="small" @click="router.push(`/app/plan/${row.id}`)">编辑</el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <div v-else class="muted">暂无单集</div>
              </el-card>
            </el-col>

            <el-col :span="10">
              <el-card>
                <template #header>资产引用</template>
                <div v-for="group in assetGroups" :key="group.type" class="asset-overview">
                  <div class="asset-overview-head">
                    <strong>{{ group.label }}</strong>
                    <span class="muted">{{ selectedAssetsMap[group.type].length }} 个</span>
                  </div>
                  <div v-if="selectedAssetsMap[group.type].length" class="asset-tags">
                    <el-tag v-for="item in selectedAssetsMap[group.type]" :key="item.id" effect="plain" class="tag">
                      {{ item.name }}
                    </el-tag>
                  </div>
                  <div v-else class="muted">未关联</div>
                </div>
              </el-card>

              <el-card class="mt">
                <template #header>初始选题</template>
                <ol v-if="initialTopicsList.length" class="topic-list">
                  <li v-for="topic in initialTopicsList.slice(0, 8)" :key="topic">{{ topic }}</li>
                </ol>
                <div v-else class="muted">暂无选题</div>
              </el-card>

              <el-card class="mt">
                <template #header>风格摘要</template>
                <div class="json-summary">
                  <div>
                    <div class="sub-title">视觉风格</div>
                    <pre>{{ compactJson(form.visual_style) }}</pre>
                  </div>
                  <div class="mt-sm">
                    <div class="sub-title">标题风格</div>
                    <pre>{{ compactJson(form.title_style) }}</pre>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>

      <el-tab-pane label="基础信息">
        <el-card>
          <el-form :model="form" label-position="top">
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="系列标题">
                  <el-input v-model="form.title" placeholder="例如: 30 天 AI 写真账号起号系列" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="方向">
                  <el-select v-model="form.direction" filterable style="width:100%">
                    <el-option-group v-for="group in directionGroups" :key="group.label" :label="group.label">
                      <el-option v-for="item in group.options" :key="item.key" :label="item.label" :value="item.key" />
                    </el-option-group>
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="系列简介">
              <el-input v-model="form.summary" type="textarea" :rows="4" />
            </el-form-item>

            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="目标平台">
                  <el-input v-model="form.target_platform" placeholder="抖音 / 小红书 / B站" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="更新频率">
                  <el-input v-model="form.update_frequency" placeholder="日更 / 周更 / 每周 3 条" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="状态">
                  <el-select v-model="form.status" style="width:100%">
                    <el-option label="草稿" value="draft" />
                    <el-option label="连载中" value="ongoing" />
                    <el-option label="已暂停" value="paused" />
                    <el-option label="已完成" value="completed" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="目标观众">
                  <el-input v-model="form.target_audience" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="单集时长 (秒)">
                  <el-input-number v-model="form.episode_duration_seconds" :min="5" :max="3600" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="计划集数">
                  <el-input-number v-model="form.planned_episodes" :min="0" :max="999" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="系列定位">
        <el-card>
          <el-form label-position="top">
            <el-form-item label="核心概念">
              <el-input v-model="positioning.core_concept" type="textarea" :rows="2" placeholder="一句话说清这个系列做什么、解决什么" />
            </el-form-item>
            <el-form-item label="目标用户">
              <el-input v-model="positioning.target_user" type="textarea" :rows="2" placeholder="是谁、有什么诉求" />
            </el-form-item>
            <el-form-item label="差异化">
              <el-input v-model="positioning.differentiation" type="textarea" :rows="2" placeholder="和同类账号比有什么不一样" />
            </el-form-item>
            <el-form-item label="给观众的承诺">
              <el-input v-model="positioning.promise" type="textarea" :rows="2" placeholder="看完这个系列他们能得到什么" />
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="单集模板">
        <el-card>
          <div class="card-header-row mb">
            <strong>结构段落</strong>
            <el-button text type="primary" @click="addSection">+ 添加段落</el-button>
          </div>
          <div v-if="episodeTemplate.sections.length === 0" class="muted">
            暂无段落,点击右上方添加。例如「开场钩子 / 主体内容 / 收束 CTA」。
          </div>
          <div v-for="(section, idx) in episodeTemplate.sections" :key="idx" class="section-row">
            <div class="section-head">
              <strong>段落 {{ idx + 1 }}</strong>
              <el-button text type="danger" size="small" @click="removeSection(idx)">删除</el-button>
            </div>
            <el-row :gutter="12">
              <el-col :span="8">
                <el-input v-model="section.name" placeholder="段落名,例如 开场钩子" />
              </el-col>
              <el-col :span="6">
                <el-input v-model="section.duration" placeholder="时长,例如 0-3s 或 8s" />
              </el-col>
              <el-col :span="10">
                <el-input v-model="section.goal" placeholder="目标 / 要达成的效果" />
              </el-col>
            </el-row>
          </div>

          <el-divider />

          <el-form-item label="必备元素 (每行一条)">
            <el-input
              v-model="mustHaveText"
              type="textarea"
              :rows="5"
              placeholder="例如:&#10;主角必须出现在前 3 秒&#10;每集结尾留悬念"
            />
          </el-form-item>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="视觉与选题">
        <el-card>
          <el-form label-position="top">
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="视觉风格 (JSON)">
                  <el-input v-model="jsonText.visual_style" type="textarea" :rows="8" />
                  <div class="hint muted">建议字段: tone, color, lighting, camera</div>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="标题风格 (JSON)">
                  <el-input v-model="jsonText.title_style" type="textarea" :rows="8" />
                  <div class="hint muted">建议字段: pattern, examples, length</div>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="初始选题 (每行一条)">
              <el-input
                v-model="initialTopicsText"
                type="textarea"
                :rows="6"
                placeholder="一行一个选题,可以先列 5-20 条"
              />
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="资产引用">
        <el-card>
          <el-form label-position="top">
            <el-form-item v-for="group in assetGroups" :key="group.type">
              <template #label>
                <div class="asset-label">
                  <span>{{ group.label }}</span>
                  <el-button text type="primary" :icon="Plus" @click="openQuickAsset(group.type)">新建并关联</el-button>
                </div>
              </template>
              <el-select v-model="form[group.type]" multiple filterable style="width:100%">
                <el-option v-for="item in assets[group.type]" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane v-if="!isNew" :label="`单集 (${episodes.length})`">
        <el-card>
          <div class="card-header-row mb">
            <strong>单集列表</strong>
            <div class="row-actions">
              <el-button :icon="MagicStick" type="success" @click="episodeDialogOpen = true">AI 生成单集</el-button>
              <el-button :loading="checking" @click="onCheckConsistency">一致性检查</el-button>
            </div>
          </div>
          <div v-if="episodes.length === 0" class="muted">
            还没有关联到本系列的单集方案。点击「AI 生成单集」让 AI 基于系列上下文生成,或在「编辑视频方案」页手动关联。
          </div>
          <el-table v-else :data="episodes" stripe>
            <el-table-column label="标题" prop="title" min-width="220" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="episodeTagType(row.status)">{{ episodeStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="时长" width="100">
              <template #default="{ row }">{{ row.duration_seconds }}s</template>
            </el-table-column>
            <el-table-column label="更新时间" width="200">
              <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click="router.push(`/app/plan/${row.id}`)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="episodeDialogOpen" title="AI 生成单集" width="560px" :close-on-click-modal="false">
      <el-form :model="episodeForm" label-position="top">
        <el-form-item label="本集主题">
          <el-input v-model="episodeForm.topic" placeholder="例如:第 1 集 转校生收到匿名纸条" />
        </el-form-item>
        <el-form-item label="本集目标">
          <el-input v-model="episodeForm.episode_goal" type="textarea" :rows="2" placeholder="例如:建立主角形象,埋下悬念" />
        </el-form-item>
        <el-form-item label="额外要求">
          <el-input v-model="episodeForm.extra_requirements" type="textarea" :rows="3" placeholder="例如:结尾必须反转,主角不能改变发色" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="episodeDialogOpen = false" :disabled="generatingEpisode">取消</el-button>
        <el-button type="primary" :loading="generatingEpisode" @click="onGenerateEpisode">生成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="reportDialogOpen" title="一致性检查报告" width="640px">
      <div v-if="report" class="report">
        <div class="report-head">
          <div class="score-block">
            <div class="score" :class="scoreClass">{{ report.score }}</div>
            <div class="muted">总分</div>
          </div>
          <div class="muted">共发现 {{ report.issues.length }} 项问题</div>
        </div>
        <div v-if="report.issues.length === 0" class="empty">系列与单集设定一致,未发现冲突。</div>
        <div v-for="(issue, idx) in report.issues" :key="idx" class="issue-row">
          <div class="issue-head">
            <el-tag :type="levelTag(issue.level)" size="small">{{ issue.level }}</el-tag>
            <span v-if="issue.asset_type" class="muted">{{ issue.asset_type }}{{ issue.field ? ` / ${issue.field}` : '' }}</span>
          </div>
          <div class="issue-msg">{{ issue.message }}</div>
          <div v-if="issue.suggestion" class="issue-fix muted">建议: {{ issue.suggestion }}</div>
        </div>
      </div>
    </el-dialog>

    <el-dialog
      v-model="assetDialogOpen"
      :title="`新建${activeAssetSchema.title}`"
      width="720px"
      :close-on-click-modal="false"
    >
      <el-form label-position="top">
        <el-form-item label="名称">
          <el-input v-model="assetForm.name" :placeholder="`例如: ${activeAssetSchema.title}`" />
        </el-form-item>

        <el-form-item v-for="field in activeAssetSchema.fields" :key="field.key" :label="field.label">
          <el-input
            v-if="field.kind === 'text'"
            v-model="assetTextValues[field.key]"
            :placeholder="field.placeholder"
          />
          <el-input
            v-else
            v-model="assetTextValues[field.key]"
            type="textarea"
            :rows="field.kind === 'lines' ? 5 : 3"
            :placeholder="field.placeholder"
          />
        </el-form-item>

        <el-form-item label="固定特征 (每行一条)">
          <el-input
            v-model="assetFixedTraitsText"
            type="textarea"
            :rows="3"
            placeholder="发色&#10;性格&#10;口头禅"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assetDialogOpen = false" :disabled="assetSaving">取消</el-button>
        <el-button type="primary" :loading="assetSaving" @click="saveQuickAsset">保存并关联</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DocumentChecked, MagicStick, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { isAITaskResponse } from '@/api/aiTasks'
import { assetsApi } from '@/api/assets'
import { plansApi } from '@/api/plans'
import { seriesApi, type ConsistencyReport, type SeriesPayload } from '@/api/series'
import { ASSET_SCHEMAS } from '@/data/assetSchemas'
import { CATEGORIES, DIRECTIONS, findDirectionLabel } from '@/data/directions'
import type { AITask, AssetBase, AssetType, EpisodeSummary, VideoPlan } from '@/types/api'
import {
  type ActiveAITask,
  findActiveAITask,
  removeActiveAITask,
  saveActiveAITask,
  waitForAITask,
} from '@/utils/aiTaskRecovery'

const route = useRoute()
const router = useRouter()
const isNew = computed(() => route.name === 'series-new')
const loading = ref(false)
const saving = ref(false)

const directionGroups = CATEGORIES.map((cat) => ({
  label: cat.label,
  options: DIRECTIONS[cat.key],
}))

const form = reactive<SeriesPayload>(defaultPayload())

const assetGroups: { type: AssetType; label: string }[] = [
  { type: 'characters', label: '人物资产' },
  { type: 'styles', label: '风格资产' },
  { type: 'worldviews', label: '世界观资产' },
  { type: 'columns', label: '栏目资产' },
]

interface Positioning {
  core_concept: string
  target_user: string
  differentiation: string
  promise: string
}

interface EpisodeSection {
  name: string
  duration: string
  goal: string
}

interface EpisodeTemplate {
  sections: EpisodeSection[]
  must_have: string[]
}

const positioning = reactive<Positioning>({
  core_concept: '',
  target_user: '',
  differentiation: '',
  promise: '',
})

const episodeTemplate = reactive<EpisodeTemplate>({
  sections: [],
  must_have: [],
})

const initialTopicsList = ref<string[]>([])

const jsonText = reactive({
  visual_style: '{}',
  title_style: '{}',
})

const assets = reactive<Record<AssetType, AssetBase[]>>({
  characters: [],
  styles: [],
  worldviews: [],
  columns: [],
})

const episodes = ref<EpisodeSummary[]>([])

const episodeDialogOpen = ref(false)
const generatingEpisode = ref(false)
const episodeForm = reactive({ topic: '', episode_goal: '', extra_requirements: '' })

const reportDialogOpen = ref(false)
const checking = ref(false)
const report = ref<ConsistencyReport | null>(null)
const taskMessage = ref('')
const taskProgress = ref(0)
let taskAbortController: AbortController | null = null
const assetDialogOpen = ref(false)
const assetSaving = ref(false)
const activeAssetType = ref<AssetType>('characters')
const activeAssetSchema = computed(() => ASSET_SCHEMAS[activeAssetType.value])
const assetForm = reactive({ name: '' })
const assetTextValues = reactive<Record<string, string>>({})
const assetFixedTraitsList = ref<string[]>([])
const scoreClass = computed(() => {
  if (!report.value) return ''
  if (report.value.score >= 90) return 'score-good'
  if (report.value.score >= 70) return 'score-warn'
  return 'score-bad'
})

const mustHaveText = computed({
  get: () => episodeTemplate.must_have.join('\n'),
  set: (v) => {
    episodeTemplate.must_have = v.split('\n').map((s) => s.trim()).filter(Boolean)
  },
})

const initialTopicsText = computed({
  get: () => initialTopicsList.value.join('\n'),
  set: (v) => {
    initialTopicsList.value = v.split('\n').map((s) => s.trim()).filter(Boolean)
  },
})

const assetFixedTraitsText = computed({
  get: () => assetFixedTraitsList.value.join('\n'),
  set: (v) => {
    assetFixedTraitsList.value = v.split('\n').map((s) => s.trim()).filter(Boolean)
  },
})

const selectedAssetsMap = computed<Record<AssetType, AssetBase[]>>(() => {
  const out = {} as Record<AssetType, AssetBase[]>
  for (const group of assetGroups) {
    const selected = new Set(form[group.type])
    out[group.type] = assets[group.type].filter((item) => selected.has(item.id))
  }
  return out
})

const overviewStats = computed(() => [
  { label: '方向', value: findDirectionLabel(form.direction) },
  { label: '状态', value: seriesStatusLabel(form.status) },
  { label: '单集进度', value: `${episodes.value.length}/${form.planned_episodes || 0}` },
  { label: '单集时长', value: `${form.episode_duration_seconds || 0}s` },
  { label: '关联资产', value: String(assetGroups.reduce((sum, group) => sum + form[group.type].length, 0)) },
])

const positioningOverview = computed(() => [
  { label: '核心概念', value: positioning.core_concept },
  { label: '目标用户', value: positioning.target_user },
  { label: '差异化', value: positioning.differentiation },
  { label: '观众承诺', value: positioning.promise },
])

const recentEpisodes = computed(() => episodes.value.slice(0, 5))

onMounted(async () => {
  loading.value = true
  try {
    await loadAssets()
    if (!isNew.value) {
      const data = await seriesApi.get(route.params.id as string)
      hydrateFromServer(data)
      resumeSeriesTasks(data.id)
    } else {
      syncJsonText()
    }
  } finally {
    loading.value = false
  }
})

async function loadAssets() {
  const types: AssetType[] = ['characters', 'styles', 'worldviews', 'columns']
  const results = await Promise.all(types.map((type) => assetsApi.list(type)))
  types.forEach((type, index) => {
    assets[type] = results[index].results
  })
}

function hydrateFromServer(data: import('@/types/api').SeriesPlan) {
  Object.assign(form, {
    title: data.title,
    direction: data.direction,
    summary: data.summary,
    target_platform: data.target_platform,
    target_audience: data.target_audience,
    update_frequency: data.update_frequency,
    episode_duration_seconds: data.episode_duration_seconds,
    planned_episodes: data.planned_episodes,
    positioning: data.positioning,
    episode_template: data.episode_template,
    visual_style: data.visual_style,
    title_style: data.title_style,
    initial_topics: data.initial_topics,
    characters: data.characters,
    styles: data.styles,
    worldviews: data.worldviews,
    columns: data.columns,
    status: data.status,
  })

  const p = (data.positioning as Partial<Positioning>) || {}
  positioning.core_concept = p.core_concept || ''
  positioning.target_user = p.target_user || ''
  positioning.differentiation = p.differentiation || ''
  positioning.promise = p.promise || ''

  const tpl = (data.episode_template as Partial<EpisodeTemplate>) || {}
  episodeTemplate.sections = Array.isArray(tpl.sections)
    ? tpl.sections.map((s) => ({
        name: s?.name || '',
        duration: s?.duration ? String(s.duration) : '',
        goal: s?.goal || '',
      }))
    : []
  episodeTemplate.must_have = Array.isArray(tpl.must_have)
    ? tpl.must_have.map((x) => String(x)).filter(Boolean)
    : []

  initialTopicsList.value = Array.isArray(data.initial_topics)
    ? data.initial_topics.map((x) => (typeof x === 'string' ? x : JSON.stringify(x)))
    : []

  episodes.value = Array.isArray(data.episodes) ? data.episodes : []
  syncJsonText()
}

function syncJsonText() {
  jsonText.visual_style = JSON.stringify(form.visual_style || {}, null, 2)
  jsonText.title_style = JSON.stringify(form.title_style || {}, null, 2)
}

function addSection() {
  episodeTemplate.sections.push({ name: '', duration: '', goal: '' })
}
function removeSection(idx: number) {
  episodeTemplate.sections.splice(idx, 1)
}

async function save() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写系列标题')
    return
  }
  const payload = buildPayload()
  if (!payload) return

  saving.value = true
  try {
    if (isNew.value) {
      const created = await seriesApi.create(payload)
      ElMessage.success('已创建系列')
      router.replace(`/app/series/${created.id}`)
    } else {
      const updated = await seriesApi.patch(route.params.id as string, payload)
      ElMessage.success('已保存')
      hydrateFromServer(updated)
    }
  } finally {
    saving.value = false
  }
}

function buildPayload(): SeriesPayload | null {
  const visualStyle = parseObject(jsonText.visual_style, '视觉风格 JSON')
  const titleStyle = parseObject(jsonText.title_style, '标题风格 JSON')
  if (!visualStyle || !titleStyle) return null

  return {
    ...form,
    positioning: { ...positioning },
    episode_template: {
      sections: episodeTemplate.sections
        .filter((s) => s.name.trim() || s.goal.trim() || s.duration.trim())
        .map((s) => ({ name: s.name, duration: s.duration, goal: s.goal })),
      must_have: [...episodeTemplate.must_have],
    },
    visual_style: visualStyle,
    title_style: titleStyle,
    initial_topics: [...initialTopicsList.value],
  }
}

function parseObject(text: string, label: string): Record<string, unknown> | null {
  try {
    const value = JSON.parse(text)
    if (value && typeof value === 'object' && !Array.isArray(value)) return value
  } catch {
    // fallthrough
  }
  ElMessage.error(`${label} 必须是 JSON 对象`)
  return null
}

function openQuickAsset(type: AssetType) {
  activeAssetType.value = type
  assetForm.name = ''
  assetFixedTraitsList.value = []
  resetAssetTextValues()
  assetDialogOpen.value = true
}

function resetAssetTextValues() {
  for (const key of Object.keys(assetTextValues)) delete assetTextValues[key]
  for (const field of activeAssetSchema.value.fields) {
    assetTextValues[field.key] = ''
  }
}

function buildAssetPayloadFromFields(): Record<string, unknown> {
  const payload: Record<string, unknown> = {}
  for (const field of activeAssetSchema.value.fields) {
    const raw = assetTextValues[field.key] ?? ''
    payload[field.key] = field.kind === 'lines'
      ? raw.split('\n').map((s) => s.trim()).filter(Boolean)
      : raw
  }
  return payload
}

async function saveQuickAsset() {
  if (!assetForm.name.trim()) {
    ElMessage.warning('请填写资产名称')
    return
  }
  assetSaving.value = true
  try {
    const type = activeAssetType.value
    const created = await assetsApi.create(type, {
      name: assetForm.name.trim(),
      payload: buildAssetPayloadFromFields(),
      fixed_traits: [...assetFixedTraitsList.value],
    })
    assets[type] = [created, ...assets[type].filter((item) => item.id !== created.id)]
    if (!form[type].includes(created.id)) {
      form[type] = [...form[type], created.id]
    }
    assetDialogOpen.value = false
    ElMessage.success('已创建并关联资产')
  } finally {
    assetSaving.value = false
  }
}

function defaultPayload(): SeriesPayload {
  return {
    title: '',
    direction: 'vlog',
    summary: '',
    target_platform: '抖音',
    target_audience: '',
    update_frequency: '',
    episode_duration_seconds: 60,
    planned_episodes: 0,
    positioning: {},
    episode_template: {},
    visual_style: {},
    title_style: {},
    initial_topics: [],
    characters: [],
    styles: [],
    worldviews: [],
    columns: [],
    status: 'draft',
  }
}

function seriesStatusLabel(s: SeriesPayload['status']) {
  return { draft: '草稿', ongoing: '连载中', paused: '已暂停', completed: '已完成' }[s] || s
}

function episodeStatusLabel(s: VideoPlan['status']) {
  return { draft: '草稿', optimizing: '优化中', confirmed: '已确认', completed: '已完成' }[s] || s
}
function episodeTagType(s: VideoPlan['status']): 'info' | 'warning' | 'success' {
  if (s === 'optimizing') return 'warning'
  if (s === 'confirmed' || s === 'completed') return 'success'
  return 'info'
}
function formatTime(iso: string) {
  try { return new Date(iso).toLocaleString() } catch { return iso }
}

function compactJson(value: Record<string, unknown>) {
  if (!value || Object.keys(value).length === 0) return '未填写'
  return JSON.stringify(value, null, 2)
}

async function onGenerateEpisode() {
  if (!episodeForm.topic.trim()) {
    ElMessage.warning('请填写本集主题')
    return
  }
  generatingEpisode.value = true
  taskMessage.value = 'AI 正在生成单集方案…'
  taskProgress.value = 10
  try {
    const seriesId = route.params.id as string
    const result = await seriesApi.generateEpisode(seriesId, { ...episodeForm })
    if (isAITaskResponse(result)) {
      saveActiveAITask({
        taskId: result.id,
        taskType: 'generate_episode',
        label: '生成单集方案',
        targetId: seriesId,
        createdAt: new Date().toISOString(),
      })
      await followEpisodeTask(result, seriesId)
      return
    }
    addEpisodeToList(result)
    resetEpisodeDialog()
    ElMessage.success('已生成单集方案')
  } finally {
    generatingEpisode.value = false
    clearTaskUi()
  }
}

async function onCheckConsistency() {
  checking.value = true
  taskMessage.value = 'AI 正在检查系列一致性…'
  taskProgress.value = 10
  try {
    const seriesId = route.params.id as string
    const result = await seriesApi.checkConsistency(seriesId)
    if (isAITaskResponse(result)) {
      saveActiveAITask({
        taskId: result.id,
        taskType: 'check_consistency',
        label: '一致性检查',
        targetId: seriesId,
        createdAt: new Date().toISOString(),
      })
      await followConsistencyTask(result, seriesId)
      return
    }
    report.value = result
    reportDialogOpen.value = true
  } finally {
    checking.value = false
    clearTaskUi()
  }
}

function levelTag(level: string): 'info' | 'warning' | 'danger' | 'success' {
  if (level === 'error') return 'danger'
  if (level === 'warning') return 'warning'
  if (level === 'info') return 'info'
  return 'success'
}

async function followEpisodeTask(task: AITask, seriesId: string) {
  startTaskPolling()
  taskProgress.value = Math.max(task.progress || 0, 10)
  taskMessage.value = task.status === 'queued' ? 'AI 生成单集任务已排队…' : 'AI 正在生成单集方案…'
  try {
    const finished = await waitForAITask(task.id, {
      signal: taskAbortController?.signal,
      onUpdate: (latest) => {
        taskProgress.value = Math.max(latest.progress || 0, 10)
        taskMessage.value = latest.status === 'queued' ? 'AI 生成单集任务已排队…' : 'AI 正在生成单集方案…'
      },
    })
    removeActiveAITask(task.id)
    const planId = typeof finished.result_payload.plan_id === 'string' ? finished.result_payload.plan_id : ''
    if (!planId) throw new Error('AI 任务已完成,但未返回单集方案 ID')
    const newEpisode = await plansApi.get(planId)
    if (newEpisode.series !== seriesId) throw new Error('生成的单集未关联到当前系列')
    addEpisodeToList(newEpisode)
    resetEpisodeDialog()
    ElMessage.success('已生成单集方案')
  } catch (err) {
    if (!isAbortError(err)) {
      removeActiveAITask(task.id)
      ElMessage.error(err instanceof Error ? err.message : 'AI 生成单集失败')
    }
  }
}

async function followConsistencyTask(task: AITask, _seriesId: string) {
  startTaskPolling()
  taskProgress.value = Math.max(task.progress || 0, 10)
  taskMessage.value = task.status === 'queued' ? '一致性检查任务已排队…' : 'AI 正在检查系列一致性…'
  try {
    const finished = await waitForAITask(task.id, {
      signal: taskAbortController?.signal,
      onUpdate: (latest) => {
        taskProgress.value = Math.max(latest.progress || 0, 10)
        taskMessage.value = latest.status === 'queued' ? '一致性检查任务已排队…' : 'AI 正在检查系列一致性…'
      },
    })
    removeActiveAITask(task.id)
    report.value = normalizeConsistencyReport(finished.result_payload)
    reportDialogOpen.value = true
  } catch (err) {
    if (!isAbortError(err)) {
      removeActiveAITask(task.id)
      ElMessage.error(err instanceof Error ? err.message : '一致性检查失败')
    }
  }
}

function resumeSeriesTasks(seriesId: string) {
  const episodeTask = findActiveAITask('generate_episode', (task) => task.targetId === seriesId)
  if (episodeTask && !generatingEpisode.value) {
    generatingEpisode.value = true
    episodeDialogOpen.value = true
    void followEpisodeTask(makeTaskStub(episodeTask), seriesId).finally(() => {
      generatingEpisode.value = false
      clearTaskUi()
    })
    return
  }

  const consistencyTask = findActiveAITask('check_consistency', (task) => task.targetId === seriesId)
  if (consistencyTask && !checking.value) {
    checking.value = true
    void followConsistencyTask(makeTaskStub(consistencyTask), seriesId).finally(() => {
      checking.value = false
      clearTaskUi()
    })
  }
}

function makeTaskStub(active: ActiveAITask): AITask {
  return {
    id: active.taskId,
    task_type: active.taskType,
    task_type_label: active.label,
    status: 'queued',
    status_label: '排队中',
    title: active.label,
    progress: 0,
    input_payload: active.targetId ? { series_id: active.targetId } : {},
    result_payload: {},
    error: '',
    started_at: null,
    finished_at: null,
    created_at: active.createdAt,
    updated_at: active.createdAt,
  }
}

function addEpisodeToList(newEpisode: VideoPlan) {
  episodes.value = [
    {
      id: newEpisode.id,
      title: newEpisode.title,
      status: newEpisode.status,
      duration_seconds: newEpisode.duration_seconds,
      updated_at: newEpisode.updated_at,
    },
    ...episodes.value.filter((episode) => episode.id !== newEpisode.id),
  ]
}

function resetEpisodeDialog() {
  episodeDialogOpen.value = false
  episodeForm.topic = ''
  episodeForm.episode_goal = ''
  episodeForm.extra_requirements = ''
}

function normalizeConsistencyReport(payload: Record<string, unknown>): ConsistencyReport {
  return {
    score: typeof payload.score === 'number' ? payload.score : 100,
    issues: Array.isArray(payload.issues) ? payload.issues as ConsistencyReport['issues'] : [],
  }
}

function startTaskPolling() {
  taskAbortController?.abort()
  taskAbortController = new AbortController()
}

function clearTaskUi() {
  taskMessage.value = ''
  taskProgress.value = 0
}

onBeforeUnmount(() => {
  taskAbortController?.abort()
})

function isAbortError(err: unknown) {
  return err instanceof DOMException && err.name === 'AbortError'
}
</script>

<style scoped>
.series-editor { padding: 28px 32px 36px; max-width: 1280px; margin: 0 auto; }
.head {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 16px; margin-bottom: 20px;
  padding: 12px 0 16px;
  border-bottom: 1px solid var(--vp-divider);
  position: sticky;
  top: var(--vp-topbar-h);
  z-index: 8;
  background: color-mix(in srgb, var(--vp-bg) 92%, transparent);
  backdrop-filter: blur(12px);
}
.head h2 { margin: 0 0 4px; }
.head-actions { display: flex; gap: 10px; }
.task-alert { margin-bottom: 16px; }
.task-title { display: flex; align-items: center; gap: 12px; width: 100%; }
.task-progress { width: 220px; }
.muted { color: var(--vp-text-3); font-size: 13px; }

/* Overview stats */
.overview-stats {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.stat-tile {
  background: var(--vp-surface);
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-md);
  padding: 14px 16px;
  transition: border-color .12s ease;
}
.stat-tile:hover { border-color: var(--vp-border-strong); }
.stat-tile span {
  display: block;
  color: var(--vp-text-3);
  font-size: 12px;
  margin-bottom: 4px;
  font-weight: 500;
  letter-spacing: 0;
}
.stat-tile strong { font-size: 20px; font-weight: 600; color: var(--vp-text-1); letter-spacing: 0; }

.card-header-row {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 14px; font-weight: 600;
}
.mb { margin-bottom: 12px; }
.mt { margin-top: 16px; }
.mt-sm { margin-top: 8px; }

.section-row {
  padding: 12px 14px;
  background: var(--vp-surface-alt);
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-md);
  margin-bottom: 8px;
}
.section-row:last-of-type { margin-bottom: 0; }
.section-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.section-head strong { font-size: 12.5px; color: var(--vp-text-2); font-weight: 600; }

.asset-label { display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 12px; }
.asset-overview { padding: 14px 0; border-bottom: 1px solid var(--vp-divider); }
.asset-overview:last-child { border-bottom: none; padding-bottom: 0; }
.asset-overview:first-child { padding-top: 0; }
.asset-overview-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.asset-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.tag { margin-right: 4px; margin-bottom: 4px; }

.must-have { margin-top: 16px; }
.sub-title {
  color: var(--vp-text-3); font-size: 11.5px;
  font-weight: 600; letter-spacing: 0;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.topic-list { margin: 0; padding-left: 20px; line-height: 1.8; font-size: 13.5px; }
.topic-list li { color: var(--vp-text-2); }

.json-summary pre {
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-sm);
  background: var(--vp-surface-alt);
  font-family: var(--vp-mono);
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.55;
  max-height: 180px;
  overflow: auto;
  color: var(--vp-text-2);
}

.hint { margin-top: 4px; }
.row-actions { display: flex; gap: 8px; }

/* Consistency report */
.report-head {
  display: flex; align-items: center; gap: 24px;
  padding: 16px;
  background: var(--vp-surface-alt);
  border-radius: var(--vp-r-md);
  margin-bottom: 16px;
}
.score-block { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.score { font-size: 36px; font-weight: 700; line-height: 1; letter-spacing: 0; }
.score-good { color: var(--vp-success); }
.score-warn { color: var(--vp-warning); }
.score-bad  { color: var(--vp-danger); }
.empty { color: var(--vp-text-3); padding: 24px 0; text-align: center; }

.issue-row {
  padding: 14px;
  background: var(--vp-surface);
  border: 1px solid var(--vp-border);
  border-radius: var(--vp-r-md);
  margin-bottom: 8px;
}
.issue-row:last-child { margin-bottom: 0; }
.issue-head { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.issue-msg { font-size: 13.5px; color: var(--vp-text-1); line-height: 1.5; }
.issue-fix { font-size: 12.5px; margin-top: 6px; line-height: 1.5; }

@media (max-width: 960px) {
  .overview-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .series-editor :deep(.el-col) {
    max-width: 100%;
    flex: 0 0 100%;
  }
}

@media (max-width: 720px) {
  .series-editor { padding: 18px 16px 28px; }
  .head {
    position: static;
    flex-direction: column;
    align-items: stretch;
  }
  .head-actions,
  .row-actions,
  .card-header-row {
    flex-wrap: wrap;
  }
}

@media (max-width: 560px) {
  .overview-stats { grid-template-columns: 1fr; }
  .task-title {
    flex-direction: column;
    align-items: stretch;
  }
  .task-progress { width: 100%; }
}
</style>
