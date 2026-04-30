from __future__ import annotations

from urllib.parse import quote

from django.conf import settings
from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from apps.ai.models import AITask
from apps.ai.serializers import AITaskSerializer
from apps.ai.task_runtime import (
    TrackedAITaskError,
    create_ai_task,
    enqueue_ai_task,
    run_existing_ai_task,
)
from apps.core.permissions import IsOwner
from apps.exports.renderers import MarkdownRenderer
from apps.exports.services import ExportRenderError, render_plan, render_series

from .ai_workflows import (
    execute_check_consistency_task,
    execute_generate_episode_task,
    execute_generate_plan_task,
    execute_generate_series_task,
    execute_optimize_plan_task,
)
from .models import SeriesPlan, VideoPlan
from .serializers import (
    ConsistencyCheckInputSerializer,
    EpisodeGenerateInputSerializer,
    GenerateInputSerializer,
    OptimizeInputSerializer,
    SeriesGenerateInputSerializer,
    SeriesPlanSerializer,
    VideoPlanSerializer,
)


ASYNC_TRUE_VALUES = {"1", "true", "yes", "on"}


def _with_task_id(payload, task: AITask) -> dict:
    data = dict(payload)
    data["task_id"] = str(task.id)
    return data


def _request_wants_async(request) -> bool:
    requested = request.query_params.get("async")
    if requested is not None:
        return str(requested).strip().lower() in ASYNC_TRUE_VALUES
    return getattr(settings, "AI_TASK_EXECUTION", "sync").strip().lower() == "celery"


def _enqueue_if_requested(request, task: AITask) -> Response | None:
    if not _request_wants_async(request):
        return None

    try:
        enqueue_ai_task(task)
    except Exception as exc:
        message = f"任务入队失败: {exc}"
        task.mark_failed(message)
        return Response(
            {"detail": message, "task_id": str(task.id)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response(AITaskSerializer(task).data, status=status.HTTP_202_ACCEPTED)


def _ai_task_error_response(exc: TrackedAITaskError) -> Response:
    return Response(
        {"detail": str(exc), "task_id": str(exc.task.id)},
        status=status.HTTP_502_BAD_GATEWAY,
    )


class VideoPlanViewSet(viewsets.ModelViewSet):
    serializer_class = VideoPlanSerializer
    permission_classes = (IsOwner,)

    def get_queryset(self):
        return VideoPlan.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        input_ser = GenerateInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        data = dict(input_ser.validated_data)
        task = create_ai_task(
            user=request.user,
            task_type=AITask.TaskType.GENERATE_PLAN,
            title="生成单条方案",
            input_payload=data,
        )

        async_response = _enqueue_if_requested(request, task)
        if async_response is not None:
            return async_response

        try:
            task, result = run_existing_ai_task(task, execute_generate_plan_task)
        except TrackedAITaskError as exc:
            return _ai_task_error_response(exc)

        plan = self.get_queryset().get(pk=result["plan_id"])
        return Response(_with_task_id(VideoPlanSerializer(plan).data, task), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="optimize")
    def optimize(self, request, pk=None):
        plan = self.get_object()
        input_ser = OptimizeInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        scope = input_ser.validated_data["scope"]
        task = create_ai_task(
            user=request.user,
            task_type=AITask.TaskType.OPTIMIZE_PLAN,
            title=f"优化方案: {plan.title}",
            input_payload={"plan_id": str(plan.id), "scope": scope},
        )

        async_response = _enqueue_if_requested(request, task)
        if async_response is not None:
            return async_response

        try:
            task, _result = run_existing_ai_task(task, execute_optimize_plan_task)
        except TrackedAITaskError as exc:
            return _ai_task_error_response(exc)

        plan.refresh_from_db()
        return Response(_with_task_id(VideoPlanSerializer(plan).data, task))

    @action(
        detail=True,
        methods=["get"],
        url_path="export",
        renderer_classes=[MarkdownRenderer, JSONRenderer],
    )
    def export(self, request, pk=None):
        plan = self.get_object()
        fmt = (request.query_params.get("format") or request.query_params.get("type") or "md").lower()
        try:
            exported = render_plan(plan, fmt)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ExportRenderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        resp = HttpResponse(exported.body, content_type=exported.content_type)
        extension = exported.filename.rsplit(".", 1)[-1]
        resp["Content-Disposition"] = f"attachment; filename=plan.{extension}; filename*=UTF-8''{quote(exported.filename)}"
        return resp

    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request, pk=None):
        plan = self.get_object()
        plan.pk = None
        plan.title = f"{plan.title} - 副本"[:200]
        plan.status = VideoPlan.Status.DRAFT
        plan.save()
        return Response(VideoPlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class SeriesPlanViewSet(viewsets.ModelViewSet):
    serializer_class = SeriesPlanSerializer
    permission_classes = (IsOwner,)

    def get_queryset(self):
        return (
            SeriesPlan.objects.filter(user=self.request.user)
            .prefetch_related("episodes", "characters", "styles", "worldviews", "columns")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(
        detail=True,
        methods=["get"],
        url_path="export",
        renderer_classes=[MarkdownRenderer, JSONRenderer],
    )
    def export(self, request, pk=None):
        series = self.get_object()
        fmt = (request.query_params.get("format") or request.query_params.get("type") or "md").lower()
        try:
            exported = render_series(series, fmt)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ExportRenderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        resp = HttpResponse(exported.body, content_type=exported.content_type)
        extension = exported.filename.rsplit(".", 1)[-1]
        resp["Content-Disposition"] = f"attachment; filename=series.{extension}; filename*=UTF-8''{quote(exported.filename)}"
        return resp

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        input_ser = SeriesGenerateInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        data = dict(input_ser.validated_data)
        task = create_ai_task(
            user=request.user,
            task_type=AITask.TaskType.GENERATE_SERIES,
            title="生成系列方案",
            input_payload=data,
        )

        async_response = _enqueue_if_requested(request, task)
        if async_response is not None:
            return async_response

        try:
            task, result = run_existing_ai_task(task, execute_generate_series_task)
        except TrackedAITaskError as exc:
            return _ai_task_error_response(exc)

        series = self.get_queryset().get(pk=result["series_id"])
        return Response(_with_task_id(SeriesPlanSerializer(series).data, task), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="episodes")
    def episodes(self, request, pk=None):
        series = self.get_object()
        input_ser = EpisodeGenerateInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        data = dict(input_ser.validated_data)
        task = create_ai_task(
            user=request.user,
            task_type=AITask.TaskType.GENERATE_EPISODE,
            title=f"生成单集: {series.title}",
            input_payload={
                "series_id": str(series.id),
                "topic": data["topic"],
                "episode_goal": data["episode_goal"],
                "extra_requirements": data["extra_requirements"],
            },
        )

        async_response = _enqueue_if_requested(request, task)
        if async_response is not None:
            return async_response

        try:
            task, result = run_existing_ai_task(task, execute_generate_episode_task)
        except TrackedAITaskError as exc:
            return _ai_task_error_response(exc)

        plan = VideoPlan.objects.get(pk=result["plan_id"], user=request.user)
        return Response(_with_task_id(VideoPlanSerializer(plan).data, task), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="check-consistency")
    def check_consistency(self, request, pk=None):
        series = self.get_object()
        input_ser = ConsistencyCheckInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        data = input_ser.validated_data
        task = create_ai_task(
            user=request.user,
            task_type=AITask.TaskType.CHECK_CONSISTENCY,
            title=f"一致性检查: {series.title}",
            input_payload={
                "series_id": str(series.id),
                "plan_id": str(data["plan_id"]) if data.get("plan_id") else "",
                "scope": data.get("scope", "all"),
            },
        )

        async_response = _enqueue_if_requested(request, task)
        if async_response is not None:
            return async_response

        try:
            task, report = run_existing_ai_task(task, execute_check_consistency_task)
        except TrackedAITaskError as exc:
            return _ai_task_error_response(exc)

        return Response(_with_task_id(report, task))
