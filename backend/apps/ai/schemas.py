"""Pydantic schemas for validating AI JSON output.

Field-level optional / default to keep validation tolerant — we want to catch
truly malformed payloads (string instead of dict, list instead of object) while
still letting the editor render a partially-filled plan.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StoryboardShot(BaseModel):
    model_config = ConfigDict(extra="allow")

    idx: int | None = None
    duration: float | int | str | None = None
    visual: str | None = None
    line: str | None = None
    editing: str | None = None
    ai_prompt: str | None = None


class SinglePlanPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = ""
    summary: str = ""
    content: dict[str, Any] = Field(default_factory=dict)
    storyboard: list[StoryboardShot] = Field(default_factory=list)
    editing_advice: dict[str, Any] = Field(default_factory=dict)
    ai_prompts: dict[str, Any] = Field(default_factory=dict)


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


class SeriesPlanPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = ""
    summary: str = ""
    positioning: dict[str, Any] = Field(default_factory=dict)
    episode_template: dict[str, Any] = Field(default_factory=dict)
    visual_style: dict[str, Any] = Field(default_factory=dict)
    title_style: dict[str, Any] = Field(default_factory=dict)
    initial_topics: list[Any] = Field(default_factory=list)
    assets: SeriesAssetBundle = Field(default_factory=SeriesAssetBundle)


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
