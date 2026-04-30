from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimestampedModel


class UserAISetting(TimestampedModel):
    """Per-user AI provider configuration. Falls back to env defaults when blank."""

    class Provider(models.TextChoices):
        OPENAI = "openai", "OpenAI"
        QWEN = "qwen", "通义千问 (Qwen)"

    PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
        "openai": {"base_url": "", "model": "gpt-4o"},
        "qwen": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-plus",
        },
    }

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_setting",
    )
    provider = models.CharField(max_length=32, choices=Provider.choices, default=Provider.OPENAI)
    api_key = models.CharField(max_length=512, blank=True, default="")
    model = models.CharField(max_length=128, blank=True, default="")
    base_url = models.URLField(blank=True, default="")

    class Meta:
        verbose_name = "AI 设置"
        verbose_name_plural = "AI 设置"

    def resolved_model(self) -> str:
        if self.model:
            return self.model
        return self.PROVIDER_DEFAULTS.get(self.provider, {}).get("model", "")

    def resolved_base_url(self) -> str:
        if self.base_url:
            return self.base_url
        return self.PROVIDER_DEFAULTS.get(self.provider, {}).get("base_url", "")


class AITask(TimestampedModel):
    class TaskType(models.TextChoices):
        GENERATE_PLAN = "generate_plan", "生成单条方案"
        OPTIMIZE_PLAN = "optimize_plan", "优化方案"
        GENERATE_SERIES = "generate_series", "生成系列"
        GENERATE_EPISODE = "generate_episode", "生成单集"
        CHECK_CONSISTENCY = "check_consistency", "一致性检查"

    class Status(models.TextChoices):
        QUEUED = "queued", "排队中"
        RUNNING = "running", "执行中"
        SUCCEEDED = "succeeded", "已完成"
        FAILED = "failed", "失败"
        CANCELED = "canceled", "已取消"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_tasks")
    task_type = models.CharField(max_length=32, choices=TaskType.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    title = models.CharField(max_length=200, blank=True, default="")
    progress = models.PositiveSmallIntegerField(default=0)
    input_payload = models.JSONField(default=dict, blank=True)
    result_payload = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [
            models.Index(fields=("user", "status", "-updated_at")),
            models.Index(fields=("task_type", "-updated_at")),
        ]

    def mark_running(self, *, progress: int = 1) -> None:
        self.status = self.Status.RUNNING
        self.progress = min(max(progress, 0), 100)
        self.started_at = self.started_at or timezone.now()
        self.save(update_fields=("status", "progress", "started_at", "updated_at"))

    def mark_succeeded(self, result: dict | None = None) -> None:
        self.status = self.Status.SUCCEEDED
        self.progress = 100
        self.result_payload = result or {}
        self.error = ""
        self.finished_at = timezone.now()
        self.save(update_fields=("status", "progress", "result_payload", "error", "finished_at", "updated_at"))

    def mark_failed(self, error: str, result: dict | None = None) -> None:
        self.status = self.Status.FAILED
        self.error = error[:4000]
        self.result_payload = result or {}
        self.finished_at = timezone.now()
        self.save(update_fields=("status", "error", "result_payload", "finished_at", "updated_at"))
