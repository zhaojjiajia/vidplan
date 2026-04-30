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
  status: 'draft' | 'optimizing' | 'confirmed' | 'completed'
  created_at: string
  updated_at: string
}

export interface StoryboardShot {
  idx: number
  duration: number
  visual: string
  line: string
  editing: string
  ai_prompt: string
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
  updated_at: string
}

export interface AssetBase {
  id: string
  user: string
  name: string
  payload: Record<string, unknown>
  fixed_traits: unknown[]
  created_at: string
  updated_at: string
}

export type AssetType = 'characters' | 'styles' | 'worldviews' | 'columns'

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
