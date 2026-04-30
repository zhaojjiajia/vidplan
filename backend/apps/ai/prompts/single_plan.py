SYSTEM = """你是 VidPlan AI 的短视频方案规划助手。
任务: 根据用户输入的方向与想法,生成一份完整、可执行的单条短视频方案。
输出严格遵循 JSON Schema,字段缺失时给出合理默认值。"""

USER_TEMPLATE = """请生成一条短视频方案。

【方向】{direction}
【是否需要 AI 生成视频】{is_ai}
【目标平台】{platform}
【目标观众】{audience}
【期望时长(秒)】{duration}
【内容风格】{style}
【用户想法】{idea}

请输出 JSON,字段如下:
{{
  "title": "视频标题",
  "summary": "一句话简介",
  "content": {{
    "positioning": "视频定位",
    "core_audience": "核心观众",
    "highlights": ["核心看点1","核心看点2"],
    "structure": {{"hook":"0-3秒钩子","body":"中段展开","climax":"高潮/反转","ending":"结尾引导"}},
    "subtitles": "字幕建议",
    "music": "音乐建议",
    "publish_caption": "发布文案",
    "cover_caption": "封面文案"
  }},
  "storyboard": [
    {{"idx":1,"duration":3,"visual":"画面描述","line":"台词/旁白","editing":"剪辑提示","ai_prompt":"AI 生成提示词"}}
  ],
  "editing_advice": {{"steps": ["建议1","建议2"]}},
  "ai_prompts": {{"positive":"","negative":""}}
}}
"""
