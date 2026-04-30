from __future__ import annotations

from apps.ai.models import AITask
from apps.ai.services import (
    check_series_consistency,
    generate_episode_plan,
    generate_series_plan,
    generate_single_plan,
    optimize_plan,
)
from apps.assets.models import CharacterAsset, ColumnAsset, StyleAsset, WorldviewAsset
from apps.assets.serializers import (
    CharacterAssetSerializer,
    ColumnAssetSerializer,
    StyleAssetSerializer,
    WorldviewAssetSerializer,
)

from .models import SeriesPlan, VideoPlan
from .serializers import SeriesPlanSerializer, VideoPlanSerializer


ASSET_MODEL_BY_TYPE = {
    "characters": (CharacterAsset, CharacterAssetSerializer, "characters"),
    "styles": (StyleAsset, StyleAssetSerializer, "styles"),
    "worldviews": (WorldviewAsset, WorldviewAssetSerializer, "worldviews"),
    "columns": (ColumnAsset, ColumnAssetSerializer, "columns"),
}

AI_GENERATED_DIRECTIONS = {
    "ai_beauty",
    "ai_drama",
    "ai_animation",
    "ai_short_drama",
    "ai_kichiku",
    "text_to_video",
    "image_to_video",
    "virtual_ip",
}


def execute_ai_task(task: AITask) -> dict:
    handlers = {
        AITask.TaskType.GENERATE_PLAN: execute_generate_plan_task,
        AITask.TaskType.OPTIMIZE_PLAN: execute_optimize_plan_task,
        AITask.TaskType.GENERATE_SERIES: execute_generate_series_task,
        AITask.TaskType.GENERATE_EPISODE: execute_generate_episode_task,
        AITask.TaskType.CHECK_CONSISTENCY: execute_check_consistency_task,
    }
    handler = handlers.get(task.task_type)
    if handler is None:
        raise ValueError(f"Unsupported AI task type: {task.task_type}")
    return handler(task)


def execute_generate_plan_task(task: AITask) -> dict:
    data = task.input_payload
    ai_payload = generate_single_plan(
        user=task.user,
        direction=data["direction"],
        idea=data["idea"],
        is_ai_generated_video=data["is_ai_generated_video"],
        target_platform=data.get("target_platform", "抖音"),
        target_audience=data.get("target_audience", ""),
        duration_seconds=data.get("duration_seconds", 30),
        style=data.get("style", ""),
    )
    plan = VideoPlan.objects.create(
        user=task.user,
        title=ai_payload.get("title", "未命名方案")[:200],
        direction=data["direction"],
        category=data["category"],
        is_ai_generated_video=data["is_ai_generated_video"],
        target_platform=data.get("target_platform", "抖音"),
        target_audience=data.get("target_audience", ""),
        duration_seconds=data.get("duration_seconds", 30),
        style=data.get("style", ""),
        summary=ai_payload.get("summary", ""),
        content=ai_payload.get("content", {}),
        storyboard=ai_payload.get("storyboard", []),
        editing_advice=ai_payload.get("editing_advice", {}),
        ai_prompts=ai_payload.get("ai_prompts", {}),
    )
    return {"plan_id": str(plan.id), "title": plan.title}


def execute_optimize_plan_task(task: AITask) -> dict:
    data = task.input_payload
    plan = VideoPlan.objects.get(pk=data["plan_id"], user=task.user)
    scope = data.get("scope", "full")
    current = VideoPlanSerializer(plan).data
    ai_payload = optimize_plan(user=task.user, plan_dict=current, scope=scope)
    apply_ai_payload(plan, ai_payload)
    if plan.status == VideoPlan.Status.OPTIMIZING:
        plan.status = VideoPlan.Status.DRAFT
    plan.save()
    return {"plan_id": str(plan.id), "title": plan.title, "scope": scope}


def execute_generate_series_task(task: AITask) -> dict:
    data = task.input_payload
    auto_create = data.get("auto_create_assets", True)
    ai_payload = generate_series_plan(
        user=task.user,
        direction=data["direction"],
        idea=data["idea"],
        target_platform=data.get("target_platform", "抖音"),
        target_audience=data.get("target_audience", ""),
        update_frequency=data.get("update_frequency", "周更"),
        episode_duration_seconds=data.get("episode_duration_seconds", 60),
        planned_episodes=data.get("planned_episodes", 10),
        style=data.get("style", ""),
    )
    series = SeriesPlan.objects.create(
        user=task.user,
        title=ai_payload.get("title", "未命名系列")[:200],
        direction=data["direction"],
        summary=ai_payload.get("summary", ""),
        target_platform=data.get("target_platform", "抖音"),
        target_audience=data.get("target_audience", ""),
        update_frequency=data.get("update_frequency", "周更"),
        episode_duration_seconds=data.get("episode_duration_seconds", 60),
        planned_episodes=data.get("planned_episodes", 10),
        positioning=ai_payload.get("positioning", {}),
        episode_template=ai_payload.get("episode_template", {}),
        visual_style=ai_payload.get("visual_style", {}),
        title_style=ai_payload.get("title_style", {}),
        initial_topics=ai_payload.get("initial_topics", []),
    )

    created_asset_count = 0
    if auto_create:
        asset_bundle = ai_payload.get("assets", {}) or {}
        for atype, (model_cls, _ser, m2m_name) in ASSET_MODEL_BY_TYPE.items():
            created_asset_ids = []
            for spec in asset_bundle.get(atype, []) or []:
                if not isinstance(spec, dict):
                    continue
                name = (spec.get("name") or "").strip()[:120] or "未命名"
                payload = spec.get("payload") or {}
                fixed_traits = spec.get("fixed_traits") or []
                asset = model_cls.objects.create(
                    user=task.user,
                    name=name,
                    payload=payload if isinstance(payload, dict) else {},
                    fixed_traits=fixed_traits if isinstance(fixed_traits, list) else [],
                )
                created_asset_ids.append(asset.pk)
            if created_asset_ids:
                getattr(series, m2m_name).set(created_asset_ids)
                created_asset_count += len(created_asset_ids)

    return {"series_id": str(series.id), "title": series.title, "created_asset_count": created_asset_count}


def execute_generate_episode_task(task: AITask) -> dict:
    data = task.input_payload
    series = SeriesPlan.objects.get(pk=data["series_id"], user=task.user)
    series_dict = SeriesPlanSerializer(series).data
    assets_dict = collect_assets(series)
    ai_payload = generate_episode_plan(
        user=task.user,
        series_dict=series_dict,
        assets_dict=assets_dict,
        topic=data["topic"],
        episode_goal=data.get("episode_goal", ""),
        extra=data.get("extra_requirements", ""),
    )

    is_ai_direction = series.direction in AI_GENERATED_DIRECTIONS
    plan = VideoPlan.objects.create(
        user=task.user,
        series=series,
        title=ai_payload.get("title", data["topic"])[:200],
        direction=series.direction,
        category=VideoPlan.Category.AI_GENERATED if is_ai_direction else VideoPlan.Category.REAL,
        is_ai_generated_video=is_ai_direction,
        target_platform=series.target_platform,
        target_audience=series.target_audience,
        duration_seconds=series.episode_duration_seconds,
        style="",
        summary=ai_payload.get("summary", ""),
        content=ai_payload.get("content", {}),
        storyboard=ai_payload.get("storyboard", []),
        editing_advice=ai_payload.get("editing_advice", {}),
        ai_prompts=ai_payload.get("ai_prompts", {}),
    )
    return {"plan_id": str(plan.id), "series_id": str(series.id), "title": plan.title}


def execute_check_consistency_task(task: AITask) -> dict:
    data = task.input_payload
    series = SeriesPlan.objects.get(pk=data["series_id"], user=task.user)
    series_dict = SeriesPlanSerializer(series).data
    assets_dict = collect_assets(series)

    episode_qs = series.episodes.all()
    if data.get("plan_id"):
        episode_qs = episode_qs.filter(pk=data["plan_id"])
    episodes_list = [VideoPlanSerializer(e).data for e in episode_qs]

    if not episodes_list:
        return {"score": 100, "issues": []}

    return check_series_consistency(
        user=task.user,
        series_dict=series_dict,
        assets_dict=assets_dict,
        episodes_list=episodes_list,
    )


def apply_ai_payload(plan: VideoPlan, payload: dict) -> None:
    if "title" in payload:
        plan.title = payload["title"][:200] or plan.title
    if "summary" in payload:
        plan.summary = payload["summary"]
    if "content" in payload:
        plan.content = {**plan.content, **payload["content"]} if isinstance(plan.content, dict) else payload["content"]
    if "storyboard" in payload:
        plan.storyboard = payload["storyboard"]
    if "editing_advice" in payload:
        plan.editing_advice = payload["editing_advice"]
    if "ai_prompts" in payload:
        plan.ai_prompts = payload["ai_prompts"]


def collect_assets(series: SeriesPlan) -> dict:
    out: dict[str, list[dict]] = {}
    for atype, (_model, ser_cls, m2m_name) in ASSET_MODEL_BY_TYPE.items():
        out[atype] = [ser_cls(a).data for a in getattr(series, m2m_name).all()]
    return out
