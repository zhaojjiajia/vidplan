from __future__ import annotations

from typing import Any

from apps.plans.models import VideoPlan


def _first_value(data: dict, keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return ""


def _kv_section(title: str, data: dict | None) -> list[str]:
    if not data:
        return []
    out = [f"## {title}", ""]
    for k, v in data.items():
        if isinstance(v, list):
            out.append(f"- **{k}**:")
            for item in v:
                out.append(f"  - {item}")
        elif isinstance(v, dict):
            out.append(f"- **{k}**:")
            for kk, vv in v.items():
                out.append(f"  - {kk}: {vv}")
        else:
            out.append(f"- **{k}**: {v}")
    out.append("")
    return out


def _storyboard_section(shots: list[dict]) -> list[str]:
    if not shots:
        return []
    out = ["## 分镜脚本", ""]
    headers = ["#", "时长", "画面 / 场景", "台词 / 旁白", "运镜", "AI Prompt"]
    out.append("| " + " | ".join(headers) + " |")
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for i, s in enumerate(shots, 1):
        row = [
            str(i),
            _md_cell(_first_value(s, ("duration", "seconds"))),
            _md_cell(_first_value(s, ("visual", "scene", "description"))),
            _md_cell(_first_value(s, ("line", "voiceover", "dialogue", "narration"))),
            _md_cell(_first_value(s, ("editing", "camera", "shot"))),
            _md_cell(_first_value(s, ("ai_prompt", "prompt"))),
        ]
        out.append("| " + " | ".join(row) + " |")
    out.append("")
    return out


def _md_cell(value: Any) -> str:
    s = str(value) if value is not None else ""
    return s.replace("|", "\\|").replace("\n", "<br/>")


def plan_to_markdown(plan: VideoPlan) -> str:
    lines: list[str] = []
    lines.append(f"# {plan.title or '未命名方案'}")
    lines.append("")
    lines.append(f"> {plan.summary}" if plan.summary else "> _暂无简介_")
    lines.append("")

    lines.append("## 基本信息")
    lines.append("")
    info = [
        ("方向", plan.direction),
        ("分类", plan.get_category_display()),
        ("AI 生成视频", "是" if plan.is_ai_generated_video else "否"),
        ("目标平台", plan.target_platform or "—"),
        ("目标观众", plan.target_audience or "—"),
        ("时长 (秒)", plan.duration_seconds),
        ("风格", plan.style or "—"),
        ("状态", plan.get_status_display()),
        ("最后更新", plan.updated_at.strftime("%Y-%m-%d %H:%M")),
    ]
    for k, v in info:
        lines.append(f"- **{k}**: {v}")
    lines.append("")

    lines.extend(_kv_section("内容设定", plan.content or {}))
    lines.extend(_storyboard_section(plan.storyboard or []))
    lines.extend(_kv_section("剪辑建议", plan.editing_advice or {}))
    lines.extend(_kv_section("AI Prompt", plan.ai_prompts or {}))

    return "\n".join(lines).rstrip() + "\n"
