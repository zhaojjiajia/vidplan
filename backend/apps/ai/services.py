from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings
from pydantic import BaseModel, ValidationError

from .prompts import consistency, critique, episode, markdown_import, optimize, outline, rewrite, series_plan, single_plan
from .prompts.directions import DEFAULT_SPEC, DirectionSpec, resolve_spec
from .providers.base import AIProvider, ChatMessage
from .registry import resolve_provider_for_user
from .schemas import (
    ConsistencyReport,
    CreationOutlinePayload,
    CritiquePayload,
    MarkdownAssetImportPayload,
    MarkdownPlanImportPayload,
    OptimizePayload,
    RewriteCandidatesPayload,
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
    try:
        resp = provider.chat(
            messages=messages,
            response_format="json",
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:  # noqa: BLE001
        raise AIPayloadError(f"AI 服务连接失败或调用异常: {exc}") from exc

    parsed = _try_parse_json(resp.content)
    validated = _validate(schema, parsed) if parsed is not None else None
    if validated is not None:
        return validated

    # One repair attempt: feed the model its broken output and ask for valid JSON.
    repair_messages = messages + [
        ChatMessage("assistant", resp.content),
        ChatMessage("user", REPAIR_INSTRUCTION.format(previous=resp.content[:4000])),
    ]
    try:
        resp2 = provider.chat(
            messages=repair_messages,
            response_format="json",
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:  # noqa: BLE001
        raise AIPayloadError(f"AI 服务连接失败或调用异常: {exc}") from exc
    parsed2 = _try_parse_json(resp2.content)
    validated2 = _validate(schema, parsed2) if parsed2 is not None else None
    if validated2 is not None:
        return validated2

    raise AIPayloadError(
        "AI 输出无法解析为预期 JSON。原始返回片段:" + (resp2.content or resp.content or "")[:300]
    )


def _critique_enabled() -> bool:
    return bool(getattr(settings, "AI_CRITIQUE_ENABLED", True))


def _format_appendix(text: str) -> str:
    """Normalise an appendix string so it slots cleanly into a USER_TEMPLATE.

    Templates have the form `... {extra_guidance}\n请输出 JSON ...`. An empty
    appendix should produce a blank line; a non-empty one is wrapped with
    leading/trailing newlines so it visually separates from neighbouring blocks.
    """
    text = (text or "").strip()
    if not text:
        return ""
    return "\n" + text + "\n"


def _run_critique(
    provider: AIProvider,
    spec: DirectionSpec,
    *,
    direction_label: str,
    plan: dict,
    platform: str,
    audience: str,
    duration: int | str,
    idea: str,
) -> dict:
    """Score a generated plan against the direction-specific rubric.

    Returns a dict matching CritiquePayload (score / axes / issues / summary).
    Failures are swallowed and reported as a 0 score so callers can decide
    whether to skip revision; we never let a critique error fail the whole
    generation flow.
    """
    rubric = critique.render_rubric(spec.critique_axes)
    focus = spec.critique_focus or DEFAULT_SPEC.critique_focus
    system = critique.SYSTEM_TEMPLATE.format(focus=focus, rubric=rubric)
    user = critique.USER_TEMPLATE.format(
        direction_label=direction_label,
        platform=platform or "未指定",
        audience=audience or "未指定",
        duration=duration,
        idea=idea or "(未提供)",
        plan_json=json.dumps(plan, ensure_ascii=False, indent=2, default=str),
    )
    try:
        return _call_json(
            provider,
            system,
            user,
            CritiquePayload,
            temperature=0.2,
        )
    except AIPayloadError as exc:
        logger.warning("Critique failed for direction=%s: %s", spec.key, exc)
        return {"score": 0, "axes": [], "issues": [], "summary": "审稿失败,跳过修订"}


def _has_critical_issue(critique_result: dict) -> bool:
    for issue in critique_result.get("issues") or []:
        severity = (issue.get("severity") or "").lower()
        if severity in {"critical", "major"}:
            return True
    return False


def _run_revision(
    provider: AIProvider,
    spec: DirectionSpec,
    schema: type[BaseModel],
    *,
    original_user_prompt: str,
    plan: dict,
    critique_result: dict,
) -> dict:
    """One revision pass: feed the model its plan + critique, ask for a fixed plan."""
    system = critique.REVISION_SYSTEM_TEMPLATE.format(generate_system=spec.generate_system)
    user = critique.REVISION_USER_TEMPLATE.format(
        original_user_prompt=original_user_prompt,
        plan_json=json.dumps(plan, ensure_ascii=False, indent=2, default=str),
        critique_json=json.dumps(critique_result, ensure_ascii=False, indent=2, default=str),
    )
    try:
        return _call_json(provider, system, user, schema, temperature=0.6)
    except AIPayloadError as exc:
        logger.warning("Revision failed for direction=%s, keeping original: %s", spec.key, exc)
        return plan


def _critique_and_maybe_revise(
    provider: AIProvider,
    spec: DirectionSpec,
    schema: type[BaseModel],
    *,
    plan: dict,
    original_user_prompt: str,
    direction_label: str,
    platform: str,
    audience: str,
    duration: int | str,
    idea: str,
) -> dict:
    """Run critique; if score is below threshold OR there are critical/major issues, revise once.

    Returns the (possibly revised) plan. Critique notes are attached under the
    `_ai_critique` key for observability — callers can choose to drop or persist
    this field. (Currently downstream apply_ai_payload only consumes known keys
    so this is harmless.)
    """
    if not _critique_enabled():
        return plan

    critique_result = _run_critique(
        provider,
        spec,
        direction_label=direction_label,
        plan=plan,
        platform=platform,
        audience=audience,
        duration=duration,
        idea=idea,
    )

    score = int(critique_result.get("score") or 0)
    needs_revision = score and (score < spec.revision_threshold or _has_critical_issue(critique_result))

    if needs_revision:
        revised = _run_revision(
            provider,
            spec,
            schema,
            original_user_prompt=original_user_prompt,
            plan=plan,
            critique_result=critique_result,
        )
        revised["_ai_critique"] = critique_result
        return revised

    plan["_ai_critique"] = critique_result
    return plan


def generate_single_plan(*, user, direction: str, idea: str, **kwargs: Any) -> dict:
    """Generate a fresh single plan.

    Note: critique was previously inlined here, but as of the V2 review flow
    it's only triggered explicitly via review_plan() — typically when the
    user clicks "确认方案" in the editor. Skipping critique here makes the
    primary "生成方案" path 1 model call instead of 2-3, much faster, and
    leaves the user free to iterate before paying the audit cost.
    """
    provider = resolve_provider_for_user(user)
    spec = resolve_spec(direction)
    direction_label = spec.label if spec is not DEFAULT_SPEC else direction

    user_prompt = single_plan.USER_TEMPLATE.format(
        direction=direction_label,
        is_ai=kwargs.get("is_ai_generated_video", False),
        platform=kwargs.get("target_platform", "抖音"),
        audience=kwargs.get("target_audience", "普通用户"),
        duration=kwargs.get("duration_seconds", 30),
        style=kwargs.get("style", "默认"),
        idea=idea,
        extra_guidance=_format_appendix(spec.generate_user_appendix),
    )
    return _call_json(provider, spec.generate_system, user_prompt, SinglePlanPayload)


def build_creation_outline(
    *,
    user,
    plan_type: str,
    direction: str,
    idea: str,
    previous_outline: str = "",
    feedback: str = "",
    **kwargs: Any,
) -> dict:
    provider = resolve_provider_for_user(user)
    plan_type = "series" if plan_type == "series" else "single"
    plan_type_label = "系列视频" if plan_type == "series" else "单条视频"
    user_prompt = outline.USER_TEMPLATE.format(
        plan_type=plan_type,
        plan_type_label=plan_type_label,
        direction=direction or "未指定",
        audience=kwargs.get("target_audience", "") or "未指定",
        style=kwargs.get("style", "") or "未指定",
        idea=idea,
        previous_outline=previous_outline or "(无)",
        feedback=feedback or "(无)",
    )
    return _call_json(
        provider,
        outline.SYSTEM,
        user_prompt,
        CreationOutlinePayload,
        temperature=0.2,
        max_tokens=1400,
    )


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


def optimize_plan(*, user, plan_dict: dict, scope: str = "full", hint: str = "") -> dict:
    provider = resolve_provider_for_user(user)
    spec = resolve_spec(plan_dict.get("direction", "") or "")
    scope_desc = optimize.SCOPE_INSTRUCTIONS.get(scope, optimize.SCOPE_INSTRUCTIONS["full"])
    user_prompt = optimize.USER_TEMPLATE.format(
        scope=scope,
        scope_desc=scope_desc,
        extra_guidance=_format_appendix(spec.optimize_appendix),
        hint=(hint or "").strip() or "(无,沿用 scope 默认目标)",
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
    previous_episodes: list[dict] | None = None,
) -> dict:
    provider = resolve_provider_for_user(user)
    spec = resolve_spec(series_dict.get("direction", "") or "")
    direction_label = spec.label if spec is not DEFAULT_SPEC else series_dict.get("direction", "")

    user_prompt = episode.USER_TEMPLATE.format(
        series_title=series_dict.get("title", ""),
        direction=direction_label,
        platform=series_dict.get("target_platform", ""),
        duration=series_dict.get("episode_duration_seconds", 60),
        summary=series_dict.get("summary", ""),
        positioning=_dump(series_dict.get("positioning", {})),
        episode_template=_dump(series_dict.get("episode_template", {})),
        visual_style=_dump(series_dict.get("visual_style", {})),
        assets=_dump(assets_dict),
        previous_episodes=_dump(previous_episodes or []),
        topic=topic,
        episode_goal=episode_goal or "",
        extra=extra or "",
        extra_guidance=_format_appendix(spec.episode_appendix),
    )
    episode_system = f"{episode.SYSTEM}\n\n【方向补充】\n{spec.generate_system}"
    # See generate_single_plan: critique only runs via the explicit review flow.
    return _call_json(provider, episode_system, user_prompt, SinglePlanPayload)


def review_plan(*, user, plan_dict: dict) -> dict:
    """Run the direction-aware critique against an existing plan.

    Used by the editor's "确认方案" flow: the user has finished iterating, we
    audit the plan once and surface the score + issues in a modal so they can
    decide whether to proceed or go back and fix things. Returns a dict
    matching CritiquePayload (score / axes / issues / summary). Failures
    return a 0-score sentinel rather than raising — UI can then show a
    "审稿失败,可手动确认" fallback.
    """
    provider = resolve_provider_for_user(user)
    spec = resolve_spec(plan_dict.get("direction", "") or "")
    direction_label = spec.label if spec is not DEFAULT_SPEC else plan_dict.get("direction", "")
    return _run_critique(
        provider,
        spec,
        direction_label=direction_label or "未指定",
        plan=plan_dict,
        platform=plan_dict.get("target_platform", "") or "未指定",
        audience=plan_dict.get("target_audience", "") or "未指定",
        duration=plan_dict.get("duration_seconds", "") or "未指定",
        idea=plan_dict.get("summary", "") or "(无)",
    )


def rewrite_field(
    *,
    user,
    plan_dict: dict,
    path: str,
    current_value: str,
    field_kind: str,
    context: dict,
    hint: str = "",
    count: int = 3,
) -> dict:
    """Generate `count` rewrite candidates for a single leaf string field.

    The direction-specific spec is reused as the persona so candidates stay
    on-brand with how the plan was originally generated. Returns a dict with
    a `candidates` list (validated against RewriteCandidatesPayload).
    """
    provider = resolve_provider_for_user(user)
    spec = resolve_spec(plan_dict.get("direction", "") or "")
    direction_label = spec.label if spec is not DEFAULT_SPEC else plan_dict.get("direction", "")

    system = rewrite.SYSTEM_TEMPLATE.format(generate_system=spec.generate_system)
    user_prompt = rewrite.USER_TEMPLATE.format(
        path=path,
        count=max(1, min(int(count or 3), 5)),
        direction_label=direction_label or "未指定",
        platform=plan_dict.get("target_platform", "") or "未指定",
        duration=plan_dict.get("duration_seconds", "") or "未指定",
        field_kind=field_kind,
        current_value=current_value or "(空)",
        context=_dump(context),
        hint=hint.strip() or "(无,请改进原版的最弱点)",
    )
    return _call_json(
        provider,
        system,
        user_prompt,
        RewriteCandidatesPayload,
        temperature=0.85,
    )


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
