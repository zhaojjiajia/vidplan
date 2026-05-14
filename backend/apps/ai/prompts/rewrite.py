"""Inline rewrite prompts.

Used by the editor's ✨ AI 改写 button: rewrite a single leaf field of a plan
(e.g. storyboard[2].line) without touching the rest of the plan, returning
multiple candidates so the user can pick. The direction-specific spec's
`generate_system` is reused as the base persona to keep style consistent.
"""
from __future__ import annotations


SYSTEM_TEMPLATE = """{generate_system}

接下来你将进入"字段精修"模式。你只对方案中的一个指定字段做改写,严禁改动其他字段。

硬性要求:
1. 候选数量必须等于用户指定的 count,各候选措辞必须明显不同,禁止近义复述。
2. 候选必须保持原方向的语气与风格(短剧要冲突、口播要密度、知识要案例化等)。
3. 候选长度与原字段相当(±30%);标题候选不超过 20 个字。
4. 候选必须遵循用户给的 "改写方向 / hint";如果 hint 为空,则改进原版的最弱点。
5. 输出严格 JSON,字段如下:
{{
  "candidates": [
    {{"value": "改写后的内容", "reason": "一句话讲这版凭什么更好,不超过 20 字"}}
  ]
}}
不要解释,不要 markdown,不要代码块。"""


USER_TEMPLATE = """请针对方案的 {path} 字段,给出 {count} 个改写候选。

【方向】{direction_label}
【目标平台】{platform}
【期望时长(秒)】{duration}

【字段路径】{path}
【字段说明】{field_kind}

【字段当前值】
{current_value}

【上下文(供你保持一致,不要修改)】
{context}

【改写方向 / hint】
{hint}

请直接输出 candidates JSON。"""
