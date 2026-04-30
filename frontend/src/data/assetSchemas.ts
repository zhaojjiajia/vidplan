import type { AssetType } from '@/types/api'

export type AssetFieldKind = 'text' | 'textarea' | 'lines'

export interface AssetField {
  key: string
  label: string
  kind: AssetFieldKind
  placeholder?: string
}

export interface AssetSchema {
  title: string
  desc: string
  fields: AssetField[]
}

export const ASSET_SCHEMAS: Record<AssetType, AssetSchema> = {
  characters: {
    title: '人物资产',
    desc: '沉淀可复用的人物设定、性格、外形和禁改特征。',
    fields: [
      { key: 'role', label: '身份 / 定位', kind: 'text', placeholder: '例如:学生、博主、虚拟主播' },
      { key: 'appearance', label: '外形描写', kind: 'textarea', placeholder: '发色、身形、服装、表情习惯…' },
      { key: 'personality', label: '性格', kind: 'textarea', placeholder: '关键人格关键词、说话风格' },
      { key: 'voice', label: '声音 / 语气', kind: 'text', placeholder: '声线、口头禅、语速' },
    ],
  },
  styles: {
    title: '风格资产',
    desc: '保存画面、剪辑、音乐、镜头语言等统一风格。',
    fields: [
      { key: 'visual', label: '画面风格', kind: 'textarea', placeholder: '色调、光线、构图' },
      { key: 'editing', label: '剪辑风格', kind: 'textarea', placeholder: '节奏、转场、字幕样式' },
      { key: 'music', label: '音乐风格', kind: 'text', placeholder: '类型、BPM、参考曲目' },
      { key: 'color', label: '色彩 / 调色', kind: 'text', placeholder: '主色调、滤镜参考' },
    ],
  },
  worldviews: {
    title: '世界观资产',
    desc: '保存故事背景、规则、地点、时间线和核心冲突。',
    fields: [
      { key: 'background', label: '故事背景', kind: 'textarea', placeholder: '世界设定、时间、核心矛盾' },
      { key: 'rules', label: '世界规则 (每行一条)', kind: 'lines', placeholder: '魔法守则、能力上限、禁忌…' },
      { key: 'locations', label: '关键地点 (每行一条)', kind: 'lines', placeholder: '主城、秘境、日常场景…' },
    ],
  },
  columns: {
    title: '栏目资产',
    desc: '保存栏目结构、固定环节、标题套路和发布节奏。',
    fields: [
      { key: 'structure', label: '固定结构段落 (每行一条)', kind: 'lines', placeholder: '开场提问 / 情景模拟 / 收束总结' },
      { key: 'title_formula', label: '标题套路', kind: 'textarea', placeholder: '例如:数字 + 痛点 + 反转' },
      { key: 'cadence', label: '发布节奏', kind: 'text', placeholder: '日更 / 周三五更 / 每月 8 条' },
    ],
  },
}
