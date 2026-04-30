SYSTEM = """你是 VidPlan AI 的系列短视频规划助手。
任务: 根据用户输入的方向、想法和约束,生成一个可连载的系列方案,并附带可复用的人物、风格、世界观、栏目资产建议。
输出严格 JSON,字段缺失时给出合理默认值,不要返回 markdown 或代码块。"""

USER_TEMPLATE = """请生成一个系列方案。

【方向】{direction}
【目标平台】{platform}
【目标观众】{audience}
【更新频率】{frequency}
【单集时长(秒)】{episode_duration}
【计划集数】{planned_episodes}
【风格】{style}
【系列想法】{idea}

请输出严格 JSON,字段如下:
{{
  "title": "系列标题",
  "summary": "系列一句话简介",
  "positioning": {{
    "core_concept": "系列核心概念",
    "target_user": "目标用户画像",
    "differentiation": "差异化",
    "promise": "对观众的承诺"
  }},
  "episode_template": {{
    "sections": [
      {{"name":"开场钩子","duration":"0-3s","goal":"3 秒抓人"}},
      {{"name":"主体内容","duration":"主要时长","goal":"输出价值/推动剧情"}},
      {{"name":"收束 CTA","duration":"末尾","goal":"互动/留悬念"}}
    ],
    "must_have": ["每集必出现的元素 1","必备元素 2"]
  }},
  "visual_style": {{"tone":"","color":"","lighting":"","camera":""}},
  "title_style": {{"pattern":"","examples":["示例标题 1","示例标题 2"],"length":"建议字数"}},
  "initial_topics": ["选题 1","选题 2","选题 3","选题 4","选题 5"],
  "assets": {{
    "characters": [
      {{"name":"主要人物","payload":{{"role":"","appearance":"","personality":"","voice":""}},"fixed_traits":["发色","性格"]}}
    ],
    "styles": [
      {{"name":"统一风格","payload":{{"visual":"","editing":"","music":"","color":""}},"fixed_traits":[]}}
    ],
    "worldviews": [
      {{"name":"故事背景","payload":{{"background":"","rules":[],"locations":[]}},"fixed_traits":[]}}
    ],
    "columns": [
      {{"name":"栏目结构","payload":{{"structure":[],"title_formula":"","cadence":""}},"fixed_traits":[]}}
    ]
  }}
}}
"""
