"""DirectionSpec dataclass + registry resolver.

The registry lives in this module instead of __init__.py to make import order
explicit: each direction module imports DirectionSpec from here and registers
itself by being imported below.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CritiqueAxis:
    """One scoring axis used by the self-critique step.

    `name` is shown to the model, `description` is the rubric, `weight` lets
    different directions emphasise different things (e.g. AI 短剧 weights 钩子
    强度 higher than 知识分享 does)."""

    name: str
    description: str
    weight: int = 10


@dataclass(frozen=True)
class DirectionSpec:
    """Per-direction prompt + critique configuration.

    `generate_system` fully replaces the generic system prompt. `generate_user_appendix`
    is injected into the user prompt before the JSON schema block (see
    single_plan.USER_TEMPLATE). The critique fields drive the optional self-review pass.
    """

    key: str
    label: str

    generate_system: str
    generate_user_appendix: str = ""

    critique_focus: str = ""
    critique_axes: list[CritiqueAxis] = field(default_factory=list)
    revision_threshold: int = 75

    optimize_appendix: str = ""
    episode_appendix: str = ""


# Default fallback spec — uses the original generic system prompt, no critique focus,
# and a balanced rubric. Imported lazily to avoid circular imports with the prompt
# modules that reference DirectionSpec.
DEFAULT_SPEC: DirectionSpec = DirectionSpec(
    key="_default",
    label="通用",
    generate_system=(
        "你是 VidPlan AI 的短视频方案规划助手。\n"
        "任务: 根据用户输入的方向与想法,生成一份完整、可执行的单条短视频方案。\n"
        "输出严格遵循 JSON Schema,字段缺失时给出合理默认值。"
    ),
    critique_focus=(
        "你是一名资深短视频内容审稿人,你的工作是给方案打分并指出最关键的问题。"
        "你的评分必须严格、可执行,只针对方案本身,不要表扬。"
    ),
    critique_axes=[
        CritiqueAxis("钩子强度", "前 3 秒能否在不依赖标题的情况下抓住观众。", weight=20),
        CritiqueAxis("结构清晰", "开头/主体/结尾是否分工明确,信息量分布是否合理。", weight=15),
        CritiqueAxis("画面可执行", "分镜的画面描述是否具体、可拍摄/可生成,而非空话。", weight=15),
        CritiqueAxis("台词节奏", "台词字数与时长是否匹配(中文每秒 4-5 字),是否有冗余。", weight=10),
        CritiqueAxis("观众契合", "内容是否真的服务目标观众的兴趣点和痛点。", weight=15),
        CritiqueAxis("传播潜力", "标题、封面、发布文案是否具备让人想点开/转发的特质。", weight=15),
        CritiqueAxis("执行细节", "剪辑、字幕、音乐、AI 提示词等执行字段是否填到位。", weight=10),
    ],
    revision_threshold=75,
)


_REGISTRY: dict[str, DirectionSpec] = {}


def _register(spec: DirectionSpec) -> None:
    _REGISTRY[spec.key] = spec


def resolve_spec(direction: str) -> DirectionSpec:
    """Return the DirectionSpec for `direction`, falling back to DEFAULT_SPEC.

    Direction keys come from frontend/src/data/directions.ts. The frontend uses
    the `key` (e.g. "ai_short_drama") as both display id and serialised value,
    so we look up the same string here.
    """
    _ensure_loaded()
    return _REGISTRY.get(direction or "", DEFAULT_SPEC)


_loaded = False


def _ensure_loaded() -> None:
    """Load every direction module on first lookup.

    Done lazily so importing the registry doesn't transitively import every
    prompt module at Django startup; also keeps the test suite snappier when
    only one direction is exercised.
    """
    global _loaded
    if _loaded:
        return
    # Modules register themselves on import via _register(SPEC).
    for module_name in ("ai_short_drama", "spoken", "knowledge"):
        module = importlib.import_module(f"{__package__}.{module_name}")
        spec = getattr(module, "SPEC", None)
        if isinstance(spec, DirectionSpec):
            _register(spec)
    _loaded = True


def all_specs() -> dict[str, DirectionSpec]:
    """Return a copy of the registry — convenient for tests / admin pages."""
    _ensure_loaded()
    return dict(_REGISTRY)
