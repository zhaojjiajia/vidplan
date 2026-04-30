from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel, UUIDModel


class SeriesPlan(UUIDModel, TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        ONGOING = "ongoing", "连载中"
        PAUSED = "paused", "已暂停"
        COMPLETED = "completed", "已完成"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="series")
    title = models.CharField(max_length=200)
    direction = models.CharField(max_length=64)
    summary = models.TextField(blank=True)

    target_platform = models.CharField(max_length=32, blank=True)
    target_audience = models.CharField(max_length=200, blank=True)
    update_frequency = models.CharField(max_length=64, blank=True)
    episode_duration_seconds = models.IntegerField(default=60)
    planned_episodes = models.IntegerField(default=0)

    positioning = models.JSONField(default=dict, blank=True)
    episode_template = models.JSONField(default=dict, blank=True)
    visual_style = models.JSONField(default=dict, blank=True)
    title_style = models.JSONField(default=dict, blank=True)
    initial_topics = models.JSONField(default=list, blank=True)

    characters = models.ManyToManyField("assets.CharacterAsset", blank=True, related_name="series")
    styles = models.ManyToManyField("assets.StyleAsset", blank=True, related_name="series")
    worldviews = models.ManyToManyField("assets.WorldviewAsset", blank=True, related_name="series")
    columns = models.ManyToManyField("assets.ColumnAsset", blank=True, related_name="series")

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        ordering = ("-updated_at",)


class VideoPlan(UUIDModel, TimestampedModel):
    class Category(models.TextChoices):
        REAL = "real", "不需要AI生成视频"
        AI_GENERATED = "ai_generated", "需要AI生成视频"

    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        OPTIMIZING = "optimizing", "优化中"
        CONFIRMED = "confirmed", "已确认"
        COMPLETED = "completed", "已完成"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="plans")
    series = models.ForeignKey(
        SeriesPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name="episodes"
    )

    title = models.CharField(max_length=200)
    direction = models.CharField(max_length=64)
    category = models.CharField(max_length=16, choices=Category.choices)
    is_ai_generated_video = models.BooleanField(default=False)

    target_platform = models.CharField(max_length=32, blank=True)
    target_audience = models.CharField(max_length=200, blank=True)
    duration_seconds = models.IntegerField(default=30)
    style = models.CharField(max_length=64, blank=True)

    summary = models.TextField(blank=True)
    content = models.JSONField(default=dict, blank=True)
    storyboard = models.JSONField(default=list, blank=True)
    editing_advice = models.JSONField(default=dict, blank=True)
    ai_prompts = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        ordering = ("-updated_at",)
