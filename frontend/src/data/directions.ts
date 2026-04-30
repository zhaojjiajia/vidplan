export type Category = 'real' | 'ai_generated'

export interface DirectionOption {
  key: string
  label: string
  desc: string
}

export const CATEGORIES: { key: Category; label: string; desc: string }[] = [
  { key: 'real', label: '真实拍摄 / 口播', desc: 'Vlog、教程、探店、测评等,AI 负责规划与脚本' },
  { key: 'ai_generated', label: 'AI 生成视频', desc: '虚拟人物、短剧、动画、文生视频、图生视频等' },
]

export const DIRECTIONS: Record<Category, DirectionOption[]> = {
  real: [
    { key: 'vlog', label: '生活 Vlog', desc: '日常、城市、旅行记录' },
    { key: 'tutorial', label: '教程类', desc: '软件/AI/编程/剪辑教程' },
    { key: 'spoken', label: '口播', desc: '观点输出、副业分享' },
    { key: 'knowledge', label: '知识分享', desc: '科普、解读、经验' },
    { key: 'store_visit', label: '探店', desc: '餐饮、店铺体验' },
    { key: 'review', label: '测评', desc: '商品、数码、工具' },
    { key: 'sales', label: '带货', desc: '种草、转化引导' },
    { key: 'daily', label: '日常记录', desc: '工作、情绪、片段' },
  ],
  ai_generated: [
    { key: 'ai_beauty', label: 'AI 美女', desc: '虚拟人物、写真、口播' },
    { key: 'ai_drama', label: 'AI 剧情', desc: '复仇、逆袭、情感' },
    { key: 'ai_animation', label: 'AI 动画', desc: '卡通、儿童、IP 动画' },
    { key: 'ai_short_drama', label: 'AI 短剧', desc: '霸总、女频、悬疑反转' },
    { key: 'ai_kichiku', label: 'AI 鬼畜', desc: '魔性循环、热梗二创' },
    { key: 'text_to_video', label: '文生视频', desc: '场景短片、概念片' },
    { key: 'image_to_video', label: '图生视频', desc: '从图扩展到视频' },
    { key: 'virtual_ip', label: '虚拟 IP', desc: '连续角色账号' },
  ],
}

export function findDirectionLabel(direction: string): string {
  for (const list of Object.values(DIRECTIONS)) {
    const hit = list.find((d) => d.key === direction)
    if (hit) return hit.label
  }
  return direction
}
