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
from apps.ai.services import AIPayloadError, build_creation_outline, review_plan, rewrite_field
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
from .path_resolver import (
    PathError,
    build_context,
    field_kind_label,
    is_rewritable,
    resolve as resolve_path,
)
from .serializers import (
    ConsistencyCheckInputSerializer,
    CreationOutlineInputSerializer,
    EpisodeGenerateInputSerializer,
    GenerateInputSerializer,
    OptimizeInputSerializer,
    RewriteInputSerializer,
    SeriesGenerateInputSerializer,
    SeriesPlanSerializer,
    VideoPlanSerializer,
)


ASYNC_TRUE_VALUES = {"1", "true", "yes", "on"}


def _next_episode_order(series: SeriesPlan, *, exclude_pk=None) -> int:
    qs = series.episodes.all()
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    current = qs.order_by("-episode_order", "-created_at").values_list("episode_order", flat=True).first()
    return int(current or 0) + 1


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
        plan = serializer.save(user=self.request.user)
        if plan.series_id and not plan.episode_order:
            plan.episode_order = _next_episode_order(plan.series, exclude_pk=plan.pk)
            plan.save(update_fields=["episode_order", "updated_at"])

    def perform_update(self, serializer):
        previous_series_id = serializer.instance.series_id
        had_explicit_order = "episode_order" in serializer.validated_data
        plan = serializer.save()
        if plan.series_id and previous_series_id != plan.series_id and not had_explicit_order:
            plan.episode_order = _next_episode_order(plan.series, exclude_pk=plan.pk)
            plan.save(update_fields=["episode_order", "updated_at"])
        elif not plan.series_id and previous_series_id and not had_explicit_order and plan.episode_order:
            plan.episode_order = 0
            plan.save(update_fields=["episode_order", "updated_at"])

    @action(detail=False, methods=["post"], url_path="outline")
    def outline(self, request):
        input_ser = CreationOutlineInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        data = dict(input_ser.validated_data)
        try:
            payload = build_creation_outline(user=request.user, **data)
        except AIPayloadError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(payload)

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
        hint = input_ser.validated_data.get("hint", "")
        task = create_ai_task(
            user=request.user,
            task_type=AITask.TaskType.OPTIMIZE_PLAN,
            title=f"优化方案: {plan.title}",
            input_payload={"plan_id": str(plan.id), "scope": scope, "hint": hint},
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
        source_series = plan.series
        plan.pk = None
        plan.title = f"{plan.title} - 副本"[:200]
        plan.status = VideoPlan.Status.DRAFT
        if source_series:
            plan.episode_order = _next_episode_order(source_series)
        else:
            plan.episode_order = 0
        plan.save()
        return Response(VideoPlanSerializer(plan).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, pk=None):
        """Run an on-demand AI critique against this plan.

        Triggered by the editor when the user is about to confirm a plan;
        results are shown in a modal so they can decide whether to proceed.
        Always returns 200 with a CritiquePayload-shaped body — even if the
        critic call itself failed (in which case score=0 + summary explains).
        """
        plan = self.get_object()
        plan_dict = VideoPlanSerializer(plan).data
        try:
            payload = review_plan(user=request.user, plan_dict=plan_dict)
        except Exception as exc:  # noqa: BLE001 — surface but don't raise
            payload = {
                "score": 0,
                "axes": [],
                "issues": [],
                "summary": f"审稿失败: {type(exc).__name__}: {str(exc)[:200]}",
            }
        return Response(payload)

    @action(detail=True, methods=["post"], url_path="rewrite")
    def rewrite(self, request, pk=None):
        """Inline AI rewrite for a single leaf field of the plan.

        Path is validated against an allowlist (see path_resolver.LEAF_PATH_PATTERNS)
        so callers can't probe arbitrary plan internals or rewrite structural
        sections that would corrupt the editor's data shape.
        """
        plan = self.get_object()
        input_ser = RewriteInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        path = input_ser.validated_data["path"]
        hint = input_ser.validated_data.get("hint", "")
        count = input_ser.validated_data.get("count", 3)

        if not is_rewritable(path):
            return Response(
                {"detail": f"该字段不支持改写: {path}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan_dict = VideoPlanSerializer(plan).data
        try:
            current_value = resolve_path(plan_dict, path)
        except PathError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(current_value, str):
            return Response(
                {"detail": "该字段当前不是文本,无法改写"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = rewrite_field(
                user=request.user,
                plan_dict=plan_dict,
                path=path,
                current_value=current_value,
                field_kind=field_kind_label(path),
                context=build_context(plan_dict, path),
                hint=hint,
                count=count,
            )
        except AIPayloadError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(payload)


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
        payload = _with_task_id(VideoPlanSerializer(plan).data, task)
        payload["asset_suggestions"] = result.get("asset_suggestions", {})
        return Response(payload, status=status.HTTP_201_CREATED)

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
