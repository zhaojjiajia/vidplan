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

如果【方向】为空,请根据【系列想法】自行从这些枚举中选择最贴近的 direction:
vlog | tutorial | spoken | knowledge | store_visit | review | sales | daily |
ai_beauty | ai_drama | ai_animation | ai_short_drama | ai_kichiku |
text_to_video | image_to_video | virtual_ip
如果都不贴近,输出空字符串。

请输出严格 JSON,字段如下:
{{
  "title": "系列标题",
  "summary": "系列一句话简介",
  "direction": "从枚举里推断最贴近的方向 key,如果无法判断则空字符串",
  "direction_label": "更具体的中文方向名,4-12 字",
  "positioning": {{
    "core_concept": "系列核心概念",
    "target_user": "目标用户画像",
    "promise": "对观众的承诺",
    "big_environment": {{
      "name": "大环境名称,如未来校园/海边小镇/都市职场",
      "description": "所有角色共同所处的总体环境,必须生成",
      "tone_color": "整体影调与色彩,用于画布背景",
      "rules": ["这个世界或场域的固定规则"],
      "locations": ["代表性地点"],
      "images": []
    }}
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
  "relationships": [
    {{"from":"人物 A","from_type":"characters","to":"小环境 A","to_type":"worldviews","label":"关系,如居住/工作/敌人/师徒/家人","description":"可选补充"}}
  ],
  "assets": {{
    "characters": [
      {{"name":"主要人物","payload":{{"role":"","appearance":"","personality":"","voice":""}},"fixed_traits":["发色","性格"]}}
    ],
    "styles": [
      {{"name":"统一风格","payload":{{"visual":"","editing":"","music":"","color":""}},"fixed_traits":[]}}
    ],
    "worldviews": [
      {{"name":"小环境名称","payload":{{"tone_color":"","purpose":"","fixed_details":[]}},"fixed_traits":[]}}
    ],
    "columns": [
      {{"name":"栏目结构","payload":{{"structure":[],"title_formula":"","cadence":""}},"fixed_traits":[]}}
    ]
  }}
}}

如果系列想法是剧情、短剧、动画、虚拟 IP、连载叙事或明确出现人物/角色名,assets.characters 必须输出主要角色;至少包含主角、核心对手和重要配角,不要只生成大环境或风格资产。
关系只在输入明确写出或可以强推断出两个资产之间关系时输出;不要为了让画布好看把所有人物两两相连。
relationships 可连接人物与人物、人物与小环境、小环境与小环境;from_type/to_type 只能填 characters 或 worldviews。
如果输入中写明某个角色的居住环境、家、住处、房间、宿舍、基地、办公室、实验室、小店等,必须在 assets.worldviews 生成对应小环境资产,并在 relationships 中连接该角色与该小环境,不要只把它写进人物 payload。
如果输入中已有角色名,必须沿用输入中的角色名生成 characters,不要把角色合并进大环境、世界观或栏目。
大环境必须输出到 positioning.big_environment,它不是资产,不要放入 assets.worldviews。
assets.worldviews 只用于小环境资产,例如某个角色的居住环境、工作间、常去地点等;如果系列想法或大纲内容没有明确标注这类具体小环境,worldviews 必须输出空数组 []。
资产建议也只输出对系列复用有帮助的内容,不要为了填满字段编造角色关系或小环境资产。
"""
