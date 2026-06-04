SYSTEM = """你是 VidPlan AI 的方案优化助手。
任务: 在保留方案核心结构的前提下,根据指定 scope 优化对应字段,使方案更具吸引力和可执行性。
输出严格 JSON,只返回需要更新的字段集合。"""

SCOPE_INSTRUCTIONS = {
    "full": "整体优化方案: 检查分镜衔接、情绪递进、开头吸引力、结尾记忆点、是否缺素材、转场、字幕配音建议。返回完整 plan 字段。",
    "title": "只优化 title 字段,生成更具传播力的标题。",
    "hook": "只优化 content.structure.hook (开头 0-3 秒钩子),让其更抓眼球。",
    "storyboard": "优化分镜脚本。若方案包含 content.sections,优先按章节生成或优化 content.sections[*].storyboard,并同步返回顶层 storyboard 扁平数组;不要改动无关章节标题与摘要。每个镜头必须包含 duration 字段,值为数字秒数,不要返回 0 或空值。若当前方案 JSON 包含 _series_context,生成章节分镜时必须结合系列定位、章节模板、视觉风格、资产关系。",
    "editing": "只优化 editing_advice 字段,补充剪映/剪辑实操步骤。",
    "ai_prompt": "只优化 ai_prompts 与 storyboard[*].ai_prompt,使提示词更精准。",
}

USER_TEMPLATE = """请按 scope 优化以下方案。

【优化 scope】{scope}
【scope 说明】{scope_desc}
{extra_guidance}
【用户额外要求 / hint】{hint}
【当前方案 JSON】
{plan_json}

输出 JSON,仅包含需要更新的字段;若是 full scope,返回完整 plan 字段。
如果用户给了 hint,请把它作为最高优先级,显著体现在改写后的内容里。"""
