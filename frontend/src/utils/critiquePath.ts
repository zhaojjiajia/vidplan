/**
 * Helpers for the AI 审稿 UI: convert raw plan field paths (e.g.
 * `storyboard[5].line`, `content.structure.hook`) into Chinese labels users
 * actually understand, and normalize legacy paths to their V2 equivalent so
 * the "去修复" jump can find the right input.
 */

const TOP_LEVEL_LABELS: Record<string, string> = {
  title: '标题',
  summary: '一句话简介',
}

const CONTENT_LABELS: Record<string, string> = {
  positioning: '核心定位',
  subtitles: '字幕建议',
  music: '音乐建议',
  publish_caption: '发布文案',
  cover_caption: '封面字',
}

const STRUCTURE_LABELS: Record<string, string> = {
  hook: '开头钩子',
  body: '中段',
  climax: '高潮 / 反转',
  ending: '结尾',
  // V2 sub-segment names a few directions emit:
  evidence: '论据',
  claim: '观点',
  action: '行动',
  phenomenon: '现象',
  cause: '原因',
  mechanism: '机制',
  application: '应用',
  escalation: '矛盾升级',
  twist: '反转',
  payoff: '收束',
}

const STORYBOARD_FIELD_LABELS: Record<string, string> = {
  description: '镜头描述',
  visual: '画面',
  line: '台词 / 旁白',
  editing: '剪辑',
  ai_prompt: 'AI 提示词',
  camera: '运镜',
}

/**
 * Convert a raw critique field path to a human label like
 * "镜头 6 · 台词 / 旁白" or "视频结构 · 开头钩子".
 * Returns the original string if no rule matches — better than swallowing.
 */
export function humanizePath(path: string): string {
  if (!path) return ''
  if (path in TOP_LEVEL_LABELS) return TOP_LEVEL_LABELS[path]

  if (path.startsWith('content.structure.')) {
    const key = path.split('.').pop() || ''
    return `视频结构 · ${STRUCTURE_LABELS[key] || key}`
  }
  if (path.startsWith('content.')) {
    const key = path.split('.').slice(1).join('.')
    return CONTENT_LABELS[key] || key
  }

  const m = path.match(/^storyboard\[(\d+)\]\.(\w+)$/)
  if (m) {
    const idx = Number(m[1]) + 1
    const field = m[2]
    return `镜头 ${idx} · ${STORYBOARD_FIELD_LABELS[field] || field}`
  }

  // Top-level storyboard reference without index (rare, but possible).
  if (path === 'storyboard') return '分镜脚本'

  return path
}

/**
 * Normalize legacy storyboard field paths (visual/line/editing/ai_prompt) to
 * `description` since the V2 editor only renders the unified field. Other
 * paths pass through unchanged.
 */
export function normalizeFixPath(path: string): string {
  const m = path.match(/^storyboard\[(\d+)\]\.(visual|line|editing|ai_prompt|camera)$/)
  if (m) return `storyboard[${m[1]}].description`
  return path
}
