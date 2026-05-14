"""Field path resolver for inline rewrite.

Paths look like `title`, `content.structure.hook`, `storyboard[2].line`. We
parse them into a token sequence and walk a plan dict to read the leaf value
(plus a small surrounding context blob for the AI prompt). Only safe ops:
attribute lookup on dicts, integer index into lists. No `__class__` etc.
"""
from __future__ import annotations

import re
from typing import Any


_TOKEN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?$")


class PathError(ValueError):
    """Raised when a path is malformed or doesn't resolve to a leaf string."""


def parse_path(path: str) -> list[tuple[str, str | int]]:
    """Tokenize a path into a list of (kind, key) pairs.

    `kind` is "key" for dict access or "index" for list access. We require
    every token to match a strict regex so attempts like `__class__` or
    arbitrary attribute strings get rejected at parse time.
    """
    if not path or not isinstance(path, str):
        raise PathError("路径不能为空")
    raw_segments = path.split(".")
    tokens: list[tuple[str, str | int]] = []
    for seg in raw_segments:
        seg = seg.strip()
        if not seg or not _TOKEN_RE.match(seg):
            raise PathError(f"非法路径片段: {seg!r}")
        if "[" in seg:
            name, _, idx_part = seg.partition("[")
            idx = int(idx_part.rstrip("]"))
            tokens.append(("key", name))
            tokens.append(("index", idx))
        else:
            tokens.append(("key", seg))
    return tokens


def resolve(data: Any, path: str) -> Any:
    """Walk `data` following `path` and return the leaf value.

    Raises PathError on missing keys, out-of-range indices, or type mismatch."""
    tokens = parse_path(path)
    current = data
    for kind, key in tokens:
        if kind == "key":
            if not isinstance(current, dict):
                raise PathError(f"路径 {path!r} 指向非字典节点")
            if key not in current:
                raise PathError(f"路径 {path!r} 不存在 (字段 {key!r})")
            current = current[key]
        else:  # index
            if not isinstance(current, list):
                raise PathError(f"路径 {path!r} 指向非数组节点")
            try:
                current = current[key]
            except IndexError as exc:
                raise PathError(f"路径 {path!r} 越界 (index {key})") from exc
    return current


# Whitelisted leaf paths the rewrite endpoint will accept. Avoids letting
# users probe arbitrary plan internals or attempt to rewrite structural fields.
LEAF_PATH_PATTERNS = [
    re.compile(r"^title$"),
    re.compile(r"^summary$"),
    re.compile(r"^content\.positioning$"),
    re.compile(r"^content\.structure\.(hook|body|climax|ending)$"),
    re.compile(r"^content\.subtitles$"),
    re.compile(r"^content\.music$"),
    re.compile(r"^content\.publish_caption$"),
    re.compile(r"^content\.cover_caption$"),
    re.compile(r"^storyboard\[\d+\]\.(description|visual|line|editing|ai_prompt|camera)$"),
]


def is_rewritable(path: str) -> bool:
    """Return True iff `path` matches the allowlist of leaf string fields."""
    return any(p.match(path) for p in LEAF_PATH_PATTERNS)


def field_kind_label(path: str) -> str:
    """Human-readable hint about what kind of text this field carries.

    Fed into the rewrite prompt so the model knows whether it's writing a
    title (short, punchy) vs. a storyboard line (dialogue) vs. an editing
    note (terse). Matters more for short fields where length and tone vary
    sharply between field types.
    """
    if path == "title":
        return "视频标题,长度不超过 20 字,需具有点击吸引力"
    if path == "summary":
        return "一句话简介,1-2 句话,不超过 60 字"
    if path == "content.positioning":
        return "视频核心定位,1-2 句话,说明这条视频对观众的价值"
    if path.startswith("content.structure."):
        section = path.rsplit(".", 1)[-1]
        labels = {
            "hook": "0-3 秒钩子,必须具备冲突/反差/悬念/反常识至少一项",
            "body": "中段内容展开,信息密度要够",
            "climax": "高潮 / 反转 / 情绪爆点段",
            "ending": "结尾段,需有记忆点或行动指引",
        }
        return labels.get(section, "结构段落")
    if path == "content.subtitles":
        return "字幕样式建议(字号/颜色/重点词高亮等)"
    if path == "content.music":
        return "音乐建议(情绪曲线 / 风格 / 节奏)"
    if path == "content.publish_caption":
        return "发布平台的正文文案,带话题标签"
    if path == "content.cover_caption":
        return "封面字,要短、抓眼球、冲突感强"
    if "storyboard" in path:
        suffix = path.rsplit(".", 1)[-1]
        labels = {
            "description": (
                "分镜的完整描述,80-180 字一段,顺序: 画面(主体/动作/表情/构图/光线) "
                "→ 台词或旁白(用引号) → 剪辑/运镜/字幕提示。要写到拍/生成时可直接执行。"
            ),
            "visual": "分镜画面描述,需包含主体/动作/表情/构图",
            "line": "分镜对应的台词或旁白,口语化、有冲突",
            "editing": "分镜剪辑提示,简短可执行",
            "ai_prompt": "AI 文生/图生视频的英文提示词,30-60 词",
            "camera": "运镜方式,如 push-in/handheld/tracking 等",
        }
        return labels.get(suffix, "分镜字段")
    return "文本字段"


def build_context(plan_dict: dict, path: str) -> dict:
    """Collect a small bundle of nearby fields the model should respect.

    For storyboard[i].* we include the whole shot. For content.structure.* we
    include sibling structure sections. For top-level text we include the
    plan title + summary as orientation. This stays lean so the prompt token
    count doesn't balloon for every keystroke-triggered rewrite.
    """
    context: dict = {
        "title": plan_dict.get("title", ""),
        "summary": plan_dict.get("summary", ""),
    }
    if path.startswith("storyboard["):
        match = re.match(r"^storyboard\[(\d+)\]\.", path)
        if match:
            idx = int(match.group(1))
            shots = plan_dict.get("storyboard") or []
            if 0 <= idx < len(shots):
                context["this_shot"] = shots[idx]
            # Give immediate neighbours for continuity.
            if idx - 1 >= 0 and idx - 1 < len(shots):
                context["prev_shot"] = shots[idx - 1]
            if idx + 1 < len(shots):
                context["next_shot"] = shots[idx + 1]
    elif path.startswith("content.structure"):
        structure = (plan_dict.get("content") or {}).get("structure") or {}
        context["structure"] = structure
    elif path.startswith("content."):
        context["content"] = plan_dict.get("content") or {}
    return context
