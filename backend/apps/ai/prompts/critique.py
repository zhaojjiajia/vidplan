"""Self-critique prompts.

The critic reads the generated plan against a direction-specific rubric and
returns a structured score + issue list. If the score is below the spec's
revision_threshold, services.py runs one revision pass with the critic notes.
"""
from __future__ import annotations


SYSTEM_TEMPLATE = """{focus}

你必须按以下评分轴给出 0-100 的总分和分轴评分:
{rubric}

你的输出格式严格为 JSON,字段如下:
{{
  "score": 总分 0-100,
  "axes": [
    {{"name": "轴名","score": 0-100,"comment": "一句话指出问题或可改进点"}}
  ],
  "issues": [
    {{"severity": "critical|major|minor","field": "content.structure 或 storyboard[2].line 等定位","comment": "问题描述与可执行修改建议"}}
  ],
  "summary": "用一句话给出整体评价,不许夸奖"
}}

只返回 JSON,不要解释,不要 markdown,不要代码块。"""


USER_TEMPLATE = """请审稿以下短视频方案。

【方向】{direction_label}
【目标平台】{platform}
【目标观众】{audience}
【期望时长(秒)】{duration}
【用户原始想法】{idea}

【方案 JSON】
{plan_json}

请直接输出审稿 JSON,严格按照系统消息中的格式。"""


REVISION_SYSTEM_TEMPLATE = """{generate_system}

接下来你将收到一份你之前生成的方案,以及一份审稿意见。
你的任务是: 在保留原方案合理部分的前提下,针对审稿意见中的每一个 critical/major issue 做出具体修改,输出一份完整的修订版方案。

修订原则:
1. 优先修复 critical 与 major 等级的问题。
2. 对于审稿提到的 "字段定位" (例如 storyboard[2].line),必须明确改写该位置内容。
3. 不要把已经合格的部分推倒重来,保持稳定。
4. 修订后必须仍然符合最初的 JSON Schema 与方向专属约束。

只返回完整方案 JSON,不要解释,不要 markdown。"""


REVISION_USER_TEMPLATE = """请修订以下方案。

【原始用户输入】
{original_user_prompt}

【上一版方案 JSON】
{plan_json}

【审稿意见 JSON】
{critique_json}

请输出修订后的完整方案 JSON,字段必须齐全。"""


def render_rubric(axes) -> str:
    """Render a list[CritiqueAxis] as plain-text bullets for the system prompt."""
    if not axes:
        return "- 综合质量 (权重 100): 整体可执行性、吸引力、与用户输入的契合度。"
    lines = []
    for axis in axes:
        lines.append(f"- {axis.name} (权重 {axis.weight}): {axis.description}")
    return "\n".join(lines)
