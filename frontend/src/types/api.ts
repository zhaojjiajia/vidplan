export interface User {
  id: string
  username: string
  nickname: string
  avatar_url: string
  created_at: string
}

export interface VideoPlan {
  id: string
  user: string
  series: string | null
  title: string
  direction: string
  category: 'real' | 'ai_generated'
  is_ai_generated_video: boolean
  target_platform: string
  target_audience: string
  duration_seconds: number
  style: string
  summary: string
  content: Record<string, unknown>
  storyboard: StoryboardShot[]
  editing_advice: Record<string, unknown>
  ai_prompts: Record<string, unknown>
  episode_order: number
  status: 'draft' | 'optimizing' | 'confirmed' | 'completed'
  created_at: string
  updated_at: string
}

export interface StoryboardShot {
  idx: number
  duration: number
  /**
   * Single-field shot body (V2). Self-contained paragraph: 画面 → 台词 →
   * 剪辑/运镜/字幕。Older plans may have empty `description` plus the legacy
   * `visual` / `line` / `editing` / `ai_prompt` fields filled in — the editor
   * stitches those together on load.
   */
  description?: string
  visual?: string
  line?: string
  editing?: string
  ai_prompt?: string
}

export interface PlanSection {
  title?: string
  name?: string
  summary?: string
  goal?: string
  duration?: number | string
  storyboard?: StoryboardShot[]
}

export interface SeriesPlan {
  id: string
  user: string
  title: string
  direction: string
  summary: string
  target_platform: string
  target_audience: string
  update_frequency: string
  episode_duration_seconds: number
  planned_episodes: number
  positioning: Record<string, unknown>
  episode_template: Record<string, unknown>
  visual_style: Record<string, unknown>
  title_style: Record<string, unknown>
  initial_topics: unknown[]
  characters: string[]
  styles: string[]
  worldviews: string[]
  columns: string[]
  status: 'draft' | 'ongoing' | 'paused' | 'completed'
  episode_count: number
  episodes: EpisodeSummary[]
  created_at: string
  updated_at: string
}

export interface EpisodeSummary {
  id: string
  title: string
  status: VideoPlan['status']
  duration_seconds: number
  episode_order: number
  updated_at: string
}

export interface AssetImage {
  url: string
  thumb_url: string
  /** Canonical English key for routing (front/side/back/...). */
  kind?: string
  /** User-visible Chinese label (正面 / 侧面 / ...). Optional. */
  label?: string
  width?: number
  height?: number
  size?: number
  uploaded_at?: string
  /** Free-form note for power users. */
  note?: string
}

export interface AssetBase {
  id: string
  user: string
  name: string
  payload: Record<string, unknown>
  fixed_traits: unknown[]
  images: AssetImage[]
  created_at: string
  updated_at: string
}

export type AssetType = 'characters' | 'styles' | 'worldviews' | 'columns'

export interface AssetSchemaField {
  key: string
  label: string
  kind: 'text' | 'textarea' | 'lines'
  placeholder?: string
}

export interface CustomAssetKind {
  id: string
  user: string
  /** Slug-style key for URL paths, e.g. 'bgm'. */
  name: string
  /** Display name, e.g. 'BGM 音乐'. */
  label: string
  icon: string
  description: string
  schema: AssetSchemaField[]
  image_labels: string[]
  asset_count: number
  created_at: string
  updated_at: string
}

export interface CustomAsset extends AssetBase {
  kind: string
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export type AITaskType =
  | 'generate_plan'
  | 'optimize_plan'
  | 'generate_series'
  | 'generate_episode'
  | 'check_consistency'

export type AITaskStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'canceled'

export interface AITask {
  id: string
  task_type: AITaskType
  task_type_label: string
  status: AITaskStatus
  status_label: string
  title: string
  progress: number
  input_payload: Record<string, unknown>
  result_payload: Record<string, unknown>
  error: string
  started_at: string | null
  finished_at: string | null
  created_at: string
  updated_at: string
}

export type TaskAware<T> = T & { task_id?: string }

export interface AICritiqueAxis {
  name: string
  score: number
  comment: string
}

export interface AICritiqueIssue {
  severity: 'critical' | 'major' | 'minor' | string
  field: string
  comment: string
}

export interface AICritique {
  score: number
  axes: AICritiqueAxis[]
  issues: AICritiqueIssue[]
  summary: string
}
