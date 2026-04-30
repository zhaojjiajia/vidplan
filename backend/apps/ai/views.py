from __future__ import annotations

import json
import time

from django.core.serializers.json import DjangoJSONEncoder
from django.http import StreamingHttpResponse
from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AITask, UserAISetting
from .providers.base import ChatMessage
from .registry import build_provider
from .serializers import (
    AISettingTestSerializer,
    AITaskSerializer,
    MarkdownImportAnalyzeSerializer,
    UserAISettingSerializer,
)
from .services import analyze_asset_markdown_import, analyze_plan_markdown_import


class UserAISettingView(APIView):
    permission_classes = (IsAuthenticated,)

    def _get_or_create(self, user) -> UserAISetting:
        obj, _ = UserAISetting.objects.get_or_create(user=user)
        return obj

    def get(self, request):
        obj = self._get_or_create(request.user)
        return Response(UserAISettingSerializer(obj).data)

    def put(self, request):
        obj = self._get_or_create(request.user)
        ser = UserAISettingSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(UserAISettingSerializer(obj).data)


class AISettingTestView(APIView):
    """Quick smoke-test that the provided (or saved) credentials answer a trivial prompt."""

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        ser = AISettingTestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        override = ser.validated_data

        saved = UserAISetting.objects.filter(user=request.user).first()
        provider_name = override.get("provider") or (saved.provider if saved else "openai")
        api_key = override.get("api_key") or (saved.api_key if saved else "")
        model = override.get("model") or (saved.resolved_model() if saved else UserAISetting.PROVIDER_DEFAULTS[provider_name]["model"])
        base_url = override.get("base_url") or (
            saved.resolved_base_url() if saved else UserAISetting.PROVIDER_DEFAULTS[provider_name]["base_url"]
        )

        if not api_key:
            return Response({"ok": False, "error": "未提供 API Key"})

        try:
            provider = build_provider(name=provider_name, api_key=api_key, model=model, base_url=base_url)
            resp = provider.chat(
                messages=[ChatMessage("user", "回复一个字:好")],
                max_tokens=10,
                temperature=0,
                timeout=20.0,
            )
            return Response({"ok": True, "model": resp.model, "sample": resp.content[:120]})
        except Exception as exc:  # noqa: BLE001
            err = type(exc).__name__
            msg = str(exc) or err
            hint = ""
            low = msg.lower()
            if "timeout" in low or "timed out" in low:
                hint = " (无法连通,可能是网络/代理问题或 Base URL 不可达)"
            elif "401" in msg or "unauthorized" in low or "invalid_api_key" in low:
                hint = " (API Key 无效或权限不足)"
            elif "404" in msg or "model" in low and "not" in low:
                hint = " (模型名不存在或当前账号无权使用)"
            return Response({"ok": False, "error": f"{err}: {msg[:400]}{hint}"})


class MarkdownImportAnalyzeView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        ser = MarkdownImportAnalyzeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            if data["mode"] == "plan":
                payload = analyze_plan_markdown_import(
                    user=request.user,
                    markdown=data["markdown"],
                )
            else:
                payload = analyze_asset_markdown_import(
                    user=request.user,
                    markdown=data["markdown"],
                    asset_title=data.get("asset_title") or data["asset_type"],
                    fields=data["fields"],
                )
        except Exception as exc:  # noqa: BLE001
            return Response({
                "ok": False,
                "detail": f"{type(exc).__name__}: {str(exc)[:400]}",
            })

        return Response({"ok": True, "data": payload})


class AITaskViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AITaskSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = AITask.objects.filter(user=self.request.user)
        status_param = self.request.query_params.get("status")
        task_type = self.request.query_params.get("task_type")
        if status_param:
            queryset = queryset.filter(status=status_param)
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        return queryset


class AITaskEventsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk):
        task = AITask.objects.filter(pk=pk, user=request.user).first()
        if task is None:
            raise NotFound("任务不存在")

        response = StreamingHttpResponse(
            self._event_stream(task.id, request.user.id),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    def _event_stream(self, task_id, user_id):
        last_payload = ""
        while True:
            task = AITask.objects.filter(pk=task_id, user_id=user_id).first()
            if task is None:
                yield self._format_event("failed", {"detail": "任务不存在"})
                return

            payload = json.dumps(AITaskSerializer(task).data, ensure_ascii=False, cls=DjangoJSONEncoder)
            if payload != last_payload:
                yield self._format_event(task.status, payload)
                last_payload = payload

            if task.status in {AITask.Status.SUCCEEDED, AITask.Status.FAILED, AITask.Status.CANCELED}:
                return

            yield ": keep-alive\n\n"
            time.sleep(2)

    def _format_event(self, event: str, payload) -> str:
        data = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, cls=DjangoJSONEncoder)
        return f"event: {event}\ndata: {data}\n\n"
