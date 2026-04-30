from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, ValidationError

from .prompts import consistency, episode, markdown_import, optimize, series_plan, single_plan
from .providers.base import AIProvider, ChatMessage
from .registry import resolve_provider_for_user
from .schemas import (
    ConsistencyReport,
    MarkdownAssetImportPayload,
    MarkdownPlanImportPayload,
    OptimizePayload,
    SeriesPlanPayload,
    SinglePlanPayload,
)

logger = logging.getLogger(__name__)


class AIPayloadError(Exception):
    """Raised when the AI response cannot be coerced into the expected shape after one repair retry."""


REPAIR_INSTRUCTION = (
    "你上一次返回的内容不是合法 JSON 或字段不符合 schema。"
    "请只返回符合要求的 JSON,不要解释,不要 markdown,不要代码块。"
    "下面是上一次的返回:\n\n{previous}\n\n"
    "请基于原始任务重新输出严格的 JSON。"
)


def _try_parse_json(text: str) -> dict | None:
    if not text:
        return None
    text = text.strip()
    # Strip possible ```json fences.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _validate(schema: type[BaseModel], data: dict) -> dict | None:
    try:
        return schema.model_validate(data).model_dump(exclude_none=True)
    except ValidationError as exc:
        logger.warning("AI payload schema mismatch: %s", exc.errors()[:3])
        return None


def _call_json(
    provider: AIProvider,
    system: str,
    user: str,
    schema: type[BaseModel],
    *,
    temperature: float = 0.7,
    max_tokens: int | None = None,
) -> dict:
    """Call the provider, parse + validate the JSON response, retry once on failure."""
    messages = [ChatMessage("system", system), ChatMessage("user", user)]
    resp = provider.chat(
        messages=messages,
        response_format="json",
        temperature=temperature,
        max_tokens=max_tokens,
    )

    parsed = _try_parse_json(resp.content)
    validated = _validate(schema, parsed) if parsed is not None else None
    if validated is not None:
        return validated

    # One repair attempt: feed the model its broken output and ask for valid JSON.
    repair_messages = messages + [
        ChatMessage("assistant", resp.content),
        ChatMessage("user", REPAIR_INSTRUCTION.format(previous=resp.content[:4000])),
    ]
    resp2 = provider.chat(
        messages=repair_messages,
        response_format="json",
        temperature=temperature,
        max_tokens=max_tokens,
    )
    parsed2 = _try_parse_json(resp2.content)
    validated2 = _validate(schema, parsed2) if parsed2 is not None else None
    if validated2 is not None:
        return validated2

    raise AIPayloadError(
        "AI 输出无法解析为预期 JSON。原始返回片段:" + (resp2.content or resp.content or "")[:300]
    )


def generate_single_plan(*, user, direction: str, idea: str, **kwargs: Any) -> dict:
    provider = resolve_provider_for_user(user)
    user_prompt = single_plan.USER_TEMPLATE.format(
        direction=direction,
        is_ai=kwargs.get("is_ai_generated_video", False),
        platform=kwargs.get("target_platform", "抖音"),
        audience=kwargs.get("target_audience", "普通用户"),
        duration=kwargs.get("duration_seconds", 30),
        style=kwargs.get("style", "默认"),
        idea=idea,
    )
    return _call_json(provider, single_plan.SYSTEM, user_prompt, SinglePlanPayload)


def analyze_plan_markdown_import(*, user, markdown: str) -> dict:
    provider = resolve_provider_for_user(user)
    user_prompt = markdown_import.PLAN_USER_TEMPLATE.format(markdown=_clip_markdown(markdown))
    return _call_json(
        provider,
        markdown_import.PLAN_SYSTEM,
        user_prompt,
        MarkdownPlanImportPayload,
        temperature=0.1,
        max_tokens=1200,
    )


def analyze_asset_markdown_import(
    *,
    user,
    markdown: str,
    asset_title: str,
    fields: list[dict[str, str]],
) -> dict:
    provider = resolve_provider_for_user(user)
    field_lines = []
    for field in fields:
        key = str(field.get("key") or "").strip()
        label = str(field.get("label") or "").strip()
        kind = str(field.get("kind") or "").strip()
        if key:
            field_lines.append(f"- key: {key}; label: {label}; kind: {kind}")
    user_prompt = markdown_import.ASSET_USER_TEMPLATE.format(
        asset_title=asset_title,
        fields="\n".join(field_lines),
        markdown=_clip_markdown(markdown),
    )
    return _call_json(
        provider,
        markdown_import.ASSET_SYSTEM,
        user_prompt,
        MarkdownAssetImportPayload,
        temperature=0.1,
        max_tokens=1800,
    )


def _clip_markdown(markdown: str, limit: int = 30000) -> str:
    text = (markdown or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[内容过长,后续已截断]"


def optimize_plan(*, user, plan_dict: dict, scope: str = "full") -> dict:
    provider = resolve_provider_for_user(user)
    scope_desc = optimize.SCOPE_INSTRUCTIONS.get(scope, optimize.SCOPE_INSTRUCTIONS["full"])
    user_prompt = optimize.USER_TEMPLATE.format(
        scope=scope,
        scope_desc=scope_desc,
        plan_json=json.dumps(plan_dict, ensure_ascii=False, indent=2, default=str),
    )
    return _call_json(provider, optimize.SYSTEM, user_prompt, OptimizePayload)


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def generate_series_plan(*, user, direction: str, idea: str, **kwargs: Any) -> dict:
    provider = resolve_provider_for_user(user)
    user_prompt = series_plan.USER_TEMPLATE.format(
        direction=direction,
        platform=kwargs.get("target_platform", "抖音"),
        audience=kwargs.get("target_audience", "普通用户"),
        frequency=kwargs.get("update_frequency", "周更"),
        episode_duration=kwargs.get("episode_duration_seconds", 60),
        planned_episodes=kwargs.get("planned_episodes", 10),
        style=kwargs.get("style", "默认"),
        idea=idea,
    )
    return _call_json(provider, series_plan.SYSTEM, user_prompt, SeriesPlanPayload)


def generate_episode_plan(
    *,
    user,
    series_dict: dict,
    assets_dict: dict,
    topic: str,
    episode_goal: str = "",
    extra: str = "",
) -> dict:
    provider = resolve_provider_for_user(user)
    user_prompt = episode.USER_TEMPLATE.format(
        series_title=series_dict.get("title", ""),
        direction=series_dict.get("direction", ""),
        platform=series_dict.get("target_platform", ""),
        duration=series_dict.get("episode_duration_seconds", 60),
        summary=series_dict.get("summary", ""),
        positioning=_dump(series_dict.get("positioning", {})),
        episode_template=_dump(series_dict.get("episode_template", {})),
        visual_style=_dump(series_dict.get("visual_style", {})),
        assets=_dump(assets_dict),
        topic=topic,
        episode_goal=episode_goal or "",
        extra=extra or "",
    )
    return _call_json(provider, episode.SYSTEM, user_prompt, SinglePlanPayload)


def check_series_consistency(
    *,
    user,
    series_dict: dict,
    assets_dict: dict,
    episodes_list: list[dict],
) -> dict:
    provider = resolve_provider_for_user(user)
    user_prompt = consistency.USER_TEMPLATE.format(
        series_title=series_dict.get("title", ""),
        summary=series_dict.get("summary", ""),
        positioning=_dump(series_dict.get("positioning", {})),
        assets=_dump(assets_dict),
        episodes=_dump(episodes_list),
    )
    return _call_json(provider, consistency.SYSTEM, user_prompt, ConsistencyReport)
