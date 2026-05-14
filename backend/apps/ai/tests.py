import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase

from .models import AITask, UserAISetting
from .prompts.directions import DEFAULT_SPEC, resolve_spec
from .providers.base import ChatResponse
from .schemas import SinglePlanPayload
from .services import AIPayloadError, _call_json, build_creation_outline, generate_single_plan, optimize_plan


User = get_user_model()


class FakeProvider:
    name = "fake"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        return ChatResponse(content=self.responses.pop(0), model="fake-model")


class FailingProvider:
    name = "failing"

    def chat(self, messages, **kwargs):
        raise RuntimeError("connection refused")


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

    def test_call_json_wraps_provider_connection_error(self):
        with self.assertRaises(AIPayloadError) as ctx:
            _call_json(FailingProvider(), "system", "user", SinglePlanPayload)

        self.assertIn("AI 服务连接失败或调用异常", str(ctx.exception))


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


class DirectionRegistryTests(APITestCase):
    def test_unknown_direction_falls_back_to_default(self):
        spec = resolve_spec("not_a_direction")
        self.assertIs(spec, DEFAULT_SPEC)

    def test_flagship_directions_are_registered(self):
        for key in ("ai_short_drama", "spoken", "knowledge"):
            spec = resolve_spec(key)
            self.assertEqual(spec.key, key, f"{key} should resolve to its own spec")
            self.assertNotEqual(spec.label, DEFAULT_SPEC.label)
            self.assertTrue(spec.generate_user_appendix.strip(), f"{key} should ship an appendix")
            self.assertTrue(spec.critique_axes, f"{key} should ship a rubric")

    def test_empty_direction_falls_back_to_default(self):
        spec = resolve_spec("")
        self.assertIs(spec, DEFAULT_SPEC)


def _valid_plan_payload(title: str = "测试方案") -> str:
    """Return a JSON string that satisfies SinglePlanPayload validation."""
    return json.dumps({
        "title": title,
        "summary": "一句话简介",
        "content": {"positioning": "测试定位"},
        "storyboard": [{"idx": 1, "duration": 3, "visual": "镜头", "line": "台词"}],
        "editing_advice": {},
        "ai_prompts": {},
    }, ensure_ascii=False)


class GenerateSinglePlanTests(APITransactionTestCase):
    """`generate_single_plan` no longer runs critique inline (that was moved to
    the explicit /review/ endpoint). These tests pin down that contract: a
    single generation = a single model call, with the direction-specific
    system prompt applied."""

    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="password123")

    def test_generate_runs_single_call_with_direction_system(self):
        provider = FakeProvider([_valid_plan_payload("生成版")])

        with patch("apps.ai.services.resolve_provider_for_user", return_value=provider):
            result = generate_single_plan(
                user=self.user,
                direction="ai_short_drama",
                idea="校园悬疑",
                target_platform="抖音",
                duration_seconds=45,
            )

        self.assertEqual(result["title"], "生成版")
        self.assertEqual(len(provider.calls), 1, "no inline critique/revision expected")
        first_system = provider.calls[0]["messages"][0].content
        self.assertIn("AI 短剧编剧总监", first_system)
        self.assertNotIn("_ai_critique", result)


class CreationOutlineServiceTests(APITransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="password123")

    def test_outline_uses_lightweight_prompt(self):
        provider = FakeProvider([
            json.dumps({
                "title": "校园悬疑大纲",
                "summary": "一个校园未来短信系列",
                "plan_type": "series",
                "direction": "ai_short_drama",
                "direction_label": "校园悬疑短剧",
                "audience": "短剧观众",
                "platform": "抖音",
                "style": "悬疑",
                "duration_hint": "每集 60 秒",
                "outline": [
                    {"title": "核心设定", "note": "未来短信引发冲突"},
                    {"title": "主线推进", "note": "每集解开一个疑点"},
                ],
                "key_points": ["主角身份", "反转强度"],
            }, ensure_ascii=False),
        ])

        with patch("apps.ai.services.resolve_provider_for_user", return_value=provider):
            result = build_creation_outline(
                user=self.user,
                plan_type="series",
                direction="",
                idea="校园里每个人都收到未来短信",
                target_platform="抖音",
                duration_seconds=60,
                style="悬疑",
            )

        self.assertEqual(result["plan_type"], "series")
        self.assertEqual(result["direction"], "ai_short_drama")
        self.assertEqual(len(provider.calls), 1)
        system_prompt = provider.calls[0]["messages"][0].content
        user_prompt = provider.calls[0]["messages"][1].content
        self.assertIn("创建接待 agent", system_prompt)
        self.assertIn("不要直接生成完整视频方案", system_prompt)
        self.assertIn("校园里每个人都收到未来短信", user_prompt)


class ReviewPlanServiceTests(APITransactionTestCase):
    """`review_plan` is the new entry point invoked from the editor's confirm
    flow. It runs one critique call against the supplied plan dict and returns
    a CritiquePayload-shaped dict."""

    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="password123")

    def test_review_returns_critique_payload(self):
        from apps.ai.services import review_plan as review_service

        critique_json = json.dumps({
            "score": 78,
            "axes": [{"name": "钩子强度", "score": 70, "comment": "可加冲突"}],
            "issues": [{"severity": "major", "field": "content.structure.hook", "comment": "钩子偏平"}],
            "summary": "整体可用,需打磨钩子",
        }, ensure_ascii=False)
        provider = FakeProvider([critique_json])

        plan_dict = {
            "direction": "ai_short_drama",
            "title": "测试方案",
            "summary": "校园悬疑短剧",
            "target_platform": "抖音",
            "duration_seconds": 45,
        }
        with patch("apps.ai.services.resolve_provider_for_user", return_value=provider):
            result = review_service(user=self.user, plan_dict=plan_dict)

        self.assertEqual(result["score"], 78)
        self.assertEqual(len(result["issues"]), 1)
        self.assertEqual(result["issues"][0]["severity"], "major")
        # The critic system prompt should reference the direction-specific focus.
        first_system = provider.calls[0]["messages"][0].content
        self.assertIn("短剧", first_system)

    def test_review_swallows_garbage_and_returns_zero_score(self):
        from apps.ai.services import review_plan as review_service

        provider = FakeProvider(["完全不是 JSON", "依然不是 JSON"])
        plan_dict = {"direction": "spoken", "title": "X"}
        with patch("apps.ai.services.resolve_provider_for_user", return_value=provider):
            result = review_service(user=self.user, plan_dict=plan_dict)

        self.assertEqual(result["score"], 0)
        self.assertEqual(result["issues"], [])


class OptimizePlanDirectionTests(APITransactionTestCase):
    """Optimize prompt should pick up direction-specific guidance from the spec."""

    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="password123")

    def test_direction_appendix_is_injected_into_optimize_prompt(self):
        provider = FakeProvider([
            json.dumps({"title": "更好的标题"}, ensure_ascii=False),
        ])

        with patch("apps.ai.services.resolve_provider_for_user", return_value=provider):
            result = optimize_plan(
                user=self.user,
                plan_dict={"direction": "spoken", "title": "原标题"},
                scope="title",
            )

        self.assertEqual(result["title"], "更好的标题")
        self.assertEqual(len(provider.calls), 1)
        user_prompt = provider.calls[0]["messages"][1].content
        # spec.optimize_appendix from spoken.py mentions "口语化" / "口播优化重点".
        self.assertIn("口播优化重点", user_prompt)

    def test_unknown_direction_uses_no_appendix(self):
        provider = FakeProvider([
            json.dumps({"title": "通用优化"}, ensure_ascii=False),
        ])

        with patch("apps.ai.services.resolve_provider_for_user", return_value=provider):
            optimize_plan(
                user=self.user,
                plan_dict={"direction": "rare_unknown", "title": "X"},
                scope="title",
            )

        user_prompt = provider.calls[0]["messages"][1].content
        # No direction-specific appendix should leak in.
        self.assertNotIn("口播优化重点", user_prompt)
        self.assertNotIn("短剧优化重点", user_prompt)
        self.assertNotIn("知识类优化重点", user_prompt)
