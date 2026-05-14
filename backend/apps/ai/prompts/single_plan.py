SYSTEM = """你是 VidPlan AI 的视频方案规划助手。
任务: 根据用户输入的方向与想法,生成一份完整、可编辑的视频方案初稿。
输出严格遵循 JSON Schema,字段缺失时给出合理默认值。

【关于 direction 与 direction_label】
你必须同时输出两个相关字段:

1. `direction` (路由 key) — 必须从下列枚举里挑最贴近用户想法的一个,如果都不贴近就输出空字符串 "",**不要自己造新 key**:
   vlog | tutorial | spoken | knowledge | store_visit | review | sales | daily |
   ai_beauty | ai_drama | ai_animation | ai_short_drama | ai_kichiku |
   text_to_video | image_to_video | virtual_ip

2. `direction_label` (展示名) — 4-12 个汉字的自由中文,可以比 direction 更具体。
   例如 direction = `ai_short_drama` 时, direction_label 可以写 "AI 校园悬疑短剧";
   direction = `store_visit` 时,可以写 "重庆夜市火锅探店";
   如果没什么可加的,跟 direction 对应的标准中文标签一致即可。

【关于章节规划的硬要求】
本次只生成章节规划,不要生成每个章节对应的具体分镜镜头。
content.sections 必须覆盖完整视频内容,每个章节都要写清楚"这一章讲什么 / 完成什么叙事或信息任务 / 观众在这一章获得什么"。
每个章节的 summary 要完整、具体,可以写 2-4 句,但不要写镜头语言、台词、运镜、剪辑脚本。
content.sections[*].storyboard 必须为空数组 [],顶层 storyboard 也必须为空数组 []。
后续用户会在编辑器中手动补分镜,或按章节单独让 AI 生成本章分镜。"""

USER_TEMPLATE = """请生成一条视频方案。

【方向】{direction}
【是否需要 AI 生成视频】{is_ai}
【目标平台】{platform}
【目标观众】{audience}
【期望时长(秒)】{duration}
【内容风格】{style}
【用户想法】{idea}
{extra_guidance}
即使上方方向规则提到了 storyboard、分镜、镜头、台词或剪辑,本次创建方案也不要生成具体分镜;只生成章节规划,所有 storyboard 必须为空数组。
请输出 JSON,字段如下:
{{
  "title": "视频标题",
  "summary": "一句话简介",
  "direction": "vlog 或 ai_short_drama 等枚举之一,空字符串也允许",
  "direction_label": "更具体的中文方向名,4-12 字",
  "content": {{
    "positioning": "视频定位",
    "core_audience": "核心观众",
    "highlights": ["核心看点1","核心看点2"],
    "sections": [
      {{
        "title": "开场",
        "summary": "建立核心问题或情绪钩子,交代本条视频为什么值得继续看。说明主角、场景或观点的起点,并埋下后续展开的期待。",
        "duration": "",
        "storyboard": []
      }},
      {{
        "title": "主体",
        "summary": "围绕核心主题展开主要信息、事件或行动,按清晰顺序推进内容。说明这一章要解决的问题、呈现的关键细节,以及它如何把观众带到下一章。",
        "duration": "",
        "storyboard": []
      }},
      {{
        "title": "结尾",
        "summary": "收束前文内容,给出结果、观点、情绪回落或互动问题。必要时留下下一步行动、下集钩子或评论区讨论点。",
        "duration": "",
        "storyboard": []
      }}
    ],
    "subtitles": "字幕建议",
    "music": "音乐建议",
    "publish_caption": "发布文案",
    "cover_caption": "封面文案"
  }},
  "storyboard": [],
  "editing_advice": {{"steps": ["建议1","建议2"]}},
  "ai_prompts": {{"positive":"","negative":""}}
}}
"""
