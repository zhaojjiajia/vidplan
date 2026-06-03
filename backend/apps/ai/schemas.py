"""Pydantic schemas for validating AI JSON output.

Field-level optional / default to keep validation tolerant — we want to catch
truly malformed payloads (string instead of dict, list instead of object) while
still letting the editor render a partially-filled plan.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Whitelist of routing-eligible direction keys. Mirrors frontend
# `directions.ts`. AI is asked to pick the closest one (or "" if none fits)
# in the `direction` field; anything outside this set is normalised to "" by
# the validator below so it falls through to DEFAULT_SPEC at routing time.
VALID_DIRECTION_KEYS: frozenset[str] = frozenset({
    "",
    # Real-shoot / spoken-word category
    "vlog", "tutorial", "spoken", "knowledge",
    "store_visit", "review", "sales", "daily",
    # AI-generated category
    "ai_beauty", "ai_drama", "ai_animation", "ai_short_drama",
    "ai_kichiku", "text_to_video", "image_to_video", "virtual_ip",
})


class StoryboardShot(BaseModel):
    model_config = ConfigDict(extra="allow")

    idx: int | None = None
    duration: float | int | str | None = None
    # `description` is the V2 single-field shot body — a self-contained
    # paragraph that fuses 画面 / 台词 / 剪辑提示 into one chunk. The legacy
    # split fields (visual/line/editing/ai_prompt) are still allowed for
    # backwards-compat with existing plans; new generations only populate
    # description.
    description: str | None = None
    visual: str | None = None
    line: str | None = None
    editing: str | None = None
    ai_prompt: str | None = None


class SinglePlanPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = ""
    summary: str = ""
    # `direction` carries the routing key (one of VALID_DIRECTION_KEYS).
    # `direction_label` is a free-form Chinese label the AI may pick to give
    # a richer name than the canonical category (e.g. "AI 校园悬疑短剧" while
    # routing-key stays `ai_short_drama`). Display layer prefers the label,
    # routing layer uses the key.
    direction: str = ""
    direction_label: str = ""
    content: dict[str, Any] = Field(default_factory=dict)
    storyboard: list[StoryboardShot] = Field(default_factory=list)
    editing_advice: dict[str, Any] = Field(default_factory=dict)
    ai_prompts: dict[str, Any] = Field(default_factory=dict)
    asset_suggestions: dict[str, Any] = Field(default_factory=dict)

    @field_validator("direction", mode="before")
    @classmethod
    def _coerce_direction(cls, value: Any) -> str:
        """Reject any direction key not in the canonical set.

        We can't trust the AI to always pick from the whitelist; quietly
        coerce off-list values (or non-strings) to "" so routing falls back
        to DEFAULT_SPEC instead of crashing the response. The free-form
        `direction_label` field is what carries any specialised naming.
        """
        if not isinstance(value, str):
            return ""
        return value if value in VALID_DIRECTION_KEYS else ""


class OutlineItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = ""
    note: str = ""


class CreationOutlinePayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = ""
    summary: str = ""
    plan_type: str = "single"
    direction: str = ""
    direction_label: str = ""
    audience: str = ""
    platform: str = ""
    style: str = ""
    duration_hint: str = ""
    outline: list[OutlineItem] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)

    @field_validator("plan_type", mode="before")
    @classmethod
    def _coerce_plan_type(cls, value: Any) -> str:
        return value if value in {"single", "series"} else "single"

    @field_validator("direction", mode="before")
    @classmethod
    def _coerce_direction(cls, value: Any) -> str:
        if not isinstance(value, str):
            return ""
        return value if value in VALID_DIRECTION_KEYS else ""


class OptimizePayload(BaseModel):
    """Optimize may return a subset of fields scoped to what was asked."""

    model_config = ConfigDict(extra="allow")

    title: str | None = None
    summary: str | None = None
    content: dict[str, Any] | None = None
    storyboard: list[StoryboardShot] | None = None
    editing_advice: dict[str, Any] | None = None
    ai_prompts: dict[str, Any] | None = None


class AssetSuggestion(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    fixed_traits: list[Any] = Field(default_factory=list)


class SeriesAssetBundle(BaseModel):
    model_config = ConfigDict(extra="allow")

    characters: list[AssetSuggestion] = Field(default_factory=list)
    styles: list[AssetSuggestion] = Field(default_factory=list)
    worldviews: list[AssetSuggestion] = Field(default_factory=list)
    columns: list[AssetSuggestion] = Field(default_factory=list)


class SeriesRelationshipSuggestion(BaseModel):
    model_config = ConfigDict(extra="allow")

    from_: str = Field(default="", alias="from")
    to: str = ""
    label: str = ""
    description: str = ""


class SeriesPlanPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = ""
    summary: str = ""
    direction: str = ""
    direction_label: str = ""
    positioning: dict[str, Any] = Field(default_factory=dict)
    episode_template: dict[str, Any] = Field(default_factory=dict)
    visual_style: dict[str, Any] = Field(default_factory=dict)
    title_style: dict[str, Any] = Field(default_factory=dict)
    initial_topics: list[Any] = Field(default_factory=list)
    relationships: list[SeriesRelationshipSuggestion] = Field(default_factory=list)
    assets: SeriesAssetBundle = Field(default_factory=SeriesAssetBundle)

    @field_validator("direction", mode="before")
    @classmethod
    def _coerce_direction(cls, value: Any) -> str:
        if not isinstance(value, str):
            return ""
        return value if value in VALID_DIRECTION_KEYS else ""


class ConsistencyIssue(BaseModel):
    model_config = ConfigDict(extra="allow")

    level: str = "warning"
    asset_type: str | None = None
    asset_id: str | None = None
    field: str | None = None
    plan_id: str | None = None
    message: str = ""
    suggestion: str = ""


class ConsistencyReport(BaseModel):
    model_config = ConfigDict(extra="allow")

    score: int = 100
    issues: list[ConsistencyIssue] = Field(default_factory=list)


class CritiqueAxisScore(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = ""
    score: int = 0
    comment: str = ""


class CritiqueIssue(BaseModel):
    model_config = ConfigDict(extra="allow")

    severity: str = "minor"
    field: str = ""
    comment: str = ""


class CritiquePayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    score: int = 0
    axes: list[CritiqueAxisScore] = Field(default_factory=list)
    issues: list[CritiqueIssue] = Field(default_factory=list)
    summary: str = ""


class RewriteCandidate(BaseModel):
    model_config = ConfigDict(extra="allow")

    value: str = ""
    reason: str = ""


class RewriteCandidatesPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    candidates: list[RewriteCandidate] = Field(default_factory=list)


class MarkdownPlanImportPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    idea: str = ""
    target_platform: str = ""
    target_audience: str = ""
    duration_seconds: int | None = None
    style: str = ""


class MarkdownAssetImportPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    fixed_traits: list[Any] = Field(default_factory=list)
