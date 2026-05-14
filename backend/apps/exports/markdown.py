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
        # 跳过内部字段，例如旧版 `_ai_critique`，避免导出给用户看。
        if isinstance(k, str) and k.startswith("_"):
            continue
        if isinstance(v, list):
            out.append(f"- **{k}**:")
            for item in v:
                out.append(f"  - {item}")
        elif isinstance(v, dict):
            out.append(f"- **{k}**:")
            for kk, vv in v.items():
                if isinstance(kk, str) and kk.startswith("_"):
                    continue
                out.append(f"  - {kk}: {vv}")
        else:
            out.append(f"- **{k}**: {v}")
    out.append("")
    return out


def _shot_description(shot: dict) -> str:
    """选出最适合导出的单条镜头描述。新版优先用 description，旧版则拼接 visual / line / editing。"""
    desc = (shot.get("description") or "").strip()
    if desc:
        return desc
    parts: list[str] = []
    visual = (shot.get("visual") or shot.get("scene") or "").strip()
    if visual:
        parts.append(f"画面:{visual}")
    line = (shot.get("line") or shot.get("voiceover") or shot.get("dialogue") or shot.get("narration") or "").strip()
    if line:
        parts.append(f"台词:\"{line}\"")
    editing = (shot.get("editing") or shot.get("camera") or shot.get("shot") or "").strip()
    if editing:
        parts.append(f"剪辑:{editing}")
    return ";".join(parts)


def _storyboard_section(shots: list[dict]) -> list[str]:
    if not shots:
        return []
    out = ["## 分镜脚本", ""]
    headers = ["#", "时长", "镜头描述"]
    out.append("| " + " | ".join(headers) + " |")
    out.append("|" + "|".join(["---", "---", "---"]) + "|")
    for i, s in enumerate(shots, 1):
        row = [
            str(i),
            _md_cell(_first_value(s, ("duration", "seconds"))),
            _md_cell(_shot_description(s)),
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
