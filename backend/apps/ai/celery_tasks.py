from __future__ import annotations

try:
    from celery import shared_task
except ModuleNotFoundError:
    shared_task = None

from .models import AITask
from .task_runtime import run_existing_ai_task
from apps.plans.ai_workflows import execute_ai_task


if shared_task is not None:

    @shared_task(name="apps.ai.run_ai_task")
    def run_ai_task(task_id: str) -> dict:
        task = AITask.objects.select_related("user").get(pk=task_id)
        if task.status == AITask.Status.CANCELED:
            return {"task_id": str(task.id), "status": task.status}
        _task, result = run_existing_ai_task(task, execute_ai_task)
        return result

else:

    class MissingCeleryTask:
        def delay(self, *_args, **_kwargs):
            raise RuntimeError("Celery 未安装,无法异步执行 AI 任务")

    run_ai_task = MissingCeleryTask()
