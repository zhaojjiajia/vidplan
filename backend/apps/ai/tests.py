from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import AITask, UserAISetting
from .providers.base import ChatResponse
from .schemas import SinglePlanPayload
from .services import AIPayloadError, _call_json


User = get_user_model()


class FakeProvider:
    name = "fake"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        return ChatResponse(content=self.responses.pop(0), model="fake-model")


class AISettingsAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="password123")
        self.client.force_authenticate(self.user)

    def test_get_and_update_ai_settings(self):
        resp = self.client.get("/api/v1/ai-settings/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["provider"], "openai")
        self.assertFalse(resp.data["has_api_key"])

        resp = self.client.put(
            "/api/v1/ai-settings/",
            {
                "provider": "qwen",
                "api_key": "dashscope-secret-1234",
                "model": "qwen-plus",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["has_api_key"])
        self.assertNotIn("api_key", resp.data)
        self.assertEqual(resp.data["api_key_masked"], "dash******1234")

        resp = self.client.put(
            "/api/v1/ai-settings/",
            {"model": "qwen-max", "api_key": ""},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        setting = UserAISetting.objects.get(user=self.user)
        self.assertEqual(setting.api_key, "dashscope-secret-1234")
        self.assertEqual(setting.model, "qwen-max")

    def test_test_endpoint_without_api_key_returns_clear_failure(self):
        resp = self.client.post("/api/v1/ai-settings/test/", {}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["ok"])
        self.assertEqual(resp.data["error"], "未提供 API Key")

    @patch("apps.ai.views.build_provider")
    def test_test_endpoint_uses_provider(self, mock_build_provider):
        provider = FakeProvider(["好"])
        mock_build_provider.return_value = provider

        resp = self.client.post(
            "/api/v1/ai-settings/test/",
            {"provider": "openai", "api_key": "sk-test", "model": "gpt-test"},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["ok"])
        self.assertEqual(resp.data["sample"], "好")
        mock_build_provider.assert_called_once()


class AIJsonParsingTests(APITestCase):
    def test_call_json_repairs_invalid_first_response(self):
        provider = FakeProvider(
            [
                "不是 JSON",
                '{"title":"修复后的标题","summary":"简介","content":{},"storyboard":[],"editing_advice":{},"ai_prompts":{}}',
            ]
        )

        payload = _call_json(provider, "system", "user", SinglePlanPayload)

        self.assertEqual(payload["title"], "修复后的标题")
        self.assertEqual(len(provider.calls), 2)
        repair_messages = provider.calls[1]["messages"]
        self.assertIn("不是 JSON", repair_messages[-1].content)

    def test_call_json_raises_after_failed_repair(self):
        provider = FakeProvider(["不是 JSON", "仍然不是 JSON"])

        with self.assertRaises(AIPayloadError):
            _call_json(provider, "system", "user", SinglePlanPayload)


class AITaskAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="password123")
        self.other_user = User.objects.create_user(username="bob", password="password123")
        self.client.force_authenticate(self.user)

    def test_task_list_detail_and_filters_are_user_scoped(self):
        own_task = AITask.objects.create(
            user=self.user,
            task_type=AITask.TaskType.GENERATE_PLAN,
            title="生成方案",
            input_payload={"idea": "测试"},
        )
        running_task = AITask.objects.create(
            user=self.user,
            task_type=AITask.TaskType.OPTIMIZE_PLAN,
            status=AITask.Status.RUNNING,
            title="优化方案",
        )
        other_task = AITask.objects.create(
            user=self.other_user,
            task_type=AITask.TaskType.GENERATE_PLAN,
            title="别人的任务",
        )

        resp = self.client.get("/api/v1/ai-tasks/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in resp.data["results"]}
        self.assertIn(str(own_task.id), ids)
        self.assertIn(str(running_task.id), ids)
        self.assertNotIn(str(other_task.id), ids)

        resp = self.client.get("/api/v1/ai-tasks/?status=running")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in resp.data["results"]], [str(running_task.id)])

        resp = self.client.get(f"/api/v1/ai-tasks/{own_task.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["title"], "生成方案")
        self.assertEqual(resp.data["status"], AITask.Status.QUEUED)
        self.assertEqual(resp.data["task_type_label"], "生成单条方案")

        resp = self.client.get(f"/api/v1/ai-tasks/{other_task.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_task_state_helpers(self):
        task = AITask.objects.create(
            user=self.user,
            task_type=AITask.TaskType.GENERATE_SERIES,
            title="生成系列",
        )

        task.mark_running(progress=30)
        task.refresh_from_db()
        self.assertEqual(task.status, AITask.Status.RUNNING)
        self.assertEqual(task.progress, 30)
        self.assertIsNotNone(task.started_at)

        task.mark_succeeded({"series_id": "abc"})
        task.refresh_from_db()
        self.assertEqual(task.status, AITask.Status.SUCCEEDED)
        self.assertEqual(task.progress, 100)
        self.assertEqual(task.result_payload["series_id"], "abc")
        self.assertEqual(task.error, "")
        self.assertIsNotNone(task.finished_at)

        failed = AITask.objects.create(user=self.user, task_type=AITask.TaskType.CHECK_CONSISTENCY)
        failed.mark_failed("模型返回异常")
        failed.refresh_from_db()
        self.assertEqual(failed.status, AITask.Status.FAILED)
        self.assertEqual(failed.error, "模型返回异常")
        self.assertIsNotNone(failed.finished_at)

    def test_task_events_stream_terminal_task(self):
        task = AITask.objects.create(
            user=self.user,
            task_type=AITask.TaskType.GENERATE_PLAN,
            title="生成方案",
        )
        task.mark_succeeded({"plan_id": "abc"})

        resp = self.client.get(f"/api/v1/ai-tasks/{task.id}/events/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "text/event-stream")
        body = b"".join(resp.streaming_content).decode("utf-8")
        self.assertIn("event: succeeded", body)
        self.assertIn('"plan_id": "abc"', body)
        self.assertIn(str(task.id), body)

    def test_task_events_stream_is_user_scoped(self):
        other_task = AITask.objects.create(
            user=self.other_user,
            task_type=AITask.TaskType.GENERATE_PLAN,
            title="别人的任务",
        )

        resp = self.client.get(f"/api/v1/ai-tasks/{other_task.id}/events/")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
