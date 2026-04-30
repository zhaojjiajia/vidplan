from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .models import AITask
from .services import AIPayloadError


class TrackedAITaskError(Exception):
    def __init__(self, message: str, task: AITask):
        super().__init__(message)
        self.task = task


def run_tracked_ai_task(
    *,
    user,
    task_type: str,
    title: str,
    input_payload: dict[str, Any] | None,
    work: Callable[[AITask], dict[str, Any] | None],
) -> tuple[AITask, dict[str, Any]]:
    task = create_ai_task(
        user=user,
        task_type=task_type,
        title=title,
        input_payload=input_payload or {},
    )
    return run_existing_ai_task(task, work)


def create_ai_task(
    *,
    user,
    task_type: str,
    title: str,
    input_payload: dict[str, Any] | None = None,
) -> AITask:
    return AITask.objects.create(
        user=user,
        task_type=task_type,
        title=title,
        input_payload=input_payload or {},
    )


def run_existing_ai_task(
    task: AITask,
    work: Callable[[AITask], dict[str, Any] | None],
) -> tuple[AITask, dict[str, Any]]:
    try:
        task.mark_running(progress=10)
        result = work(task) or {}
    except AIPayloadError as exc:
        task.mark_failed(str(exc))
        raise TrackedAITaskError(str(exc), task) from exc
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        task.mark_failed(message)
        raise TrackedAITaskError(message, task) from exc

    task.mark_succeeded(result)
    return task, result


def enqueue_ai_task(task: AITask) -> None:
    from .celery_tasks import run_ai_task

    run_ai_task.delay(str(task.id))
