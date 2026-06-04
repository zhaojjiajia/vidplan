from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.ai.models import AITask
from apps.ai.services import AIPayloadError
from apps.assets.models import CharacterAsset, WorldviewAsset

from .ai_workflows import apply_ai_payload
from .models import SeriesPlan, VideoPlan


User = get_user_model()


class PlansAndAssetsAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="password123")
        self.other_user = User.objects.create_user(username="bob", password="password123")

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def create_series(self, *, user=None, direction="vlog", title="测试系列") -> SeriesPlan:
        return SeriesPlan.objects.create(
            user=user or self.user,
            title=title,
            direction=direction,
            summary="系列总案简介",
            target_platform="抖音",
            target_audience="内容创作者",
            update_frequency="周更",
            episode_duration_seconds=60,
            planned_episodes=10,
            positioning={"core_concept": "帮助新手做短视频"},
            episode_template={"sections": [{"name": "开场钩子", "duration": "0-3s"}]},
            visual_style={"tone": "明亮"},
            title_style={"pattern": "数字 + 痛点"},
            initial_topics=["第一集选题", "第二集选题"],
        )

    def create_plan(self, *, user=None, series=None) -> VideoPlan:
        return VideoPlan.objects.create(
            user=user or self.user,
            series=series,
            title="测试方案",
            direction="vlog",
            category=VideoPlan.Category.REAL,
            is_ai_generated_video=False,
            target_platform="抖音",
            duration_seconds=30,
            summary="用于导出的测试简介",
            content={"positioning": "面向新手", "highlights": ["清晰", "实用"]},
            storyboard=[
                {
                    "idx": 1,
                    "duration": 3,
                    "visual": "开场画面",
                    "line": "欢迎观看",
                    "editing": "快切",
                    "ai_prompt": "bright room",
                }
            ],
            editing_advice={"steps": ["加字幕"]},
            ai_prompts={"positive": "clean"},
        )

    def test_plan_crud_is_user_scoped(self):
        own_plan = self.create_plan()
        other_plan = self.create_plan(user=self.other_user)

        self.authenticate()
        list_resp = self.client.get("/api/v1/plans/")
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in list_resp.data["results"]}
        self.assertIn(str(own_plan.id), ids)
        self.assertNotIn(str(other_plan.id), ids)

        detail_resp = self.client.get(f"/api/v1/plans/{other_plan.id}/")
        self.assertEqual(detail_resp.status_code, status.HTTP_404_NOT_FOUND)

        create_resp = self.client.post(
            "/api/v1/plans/",
            {
                "title": "手动草稿",
                "direction": "vlog",
                "category": VideoPlan.Category.REAL,
                "is_ai_generated_video": False,
                "duration_seconds": 45,
            },
            format="json",
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        created = VideoPlan.objects.get(pk=create_resp.data["id"])
        self.assertEqual(created.user, self.user)

        patch_resp = self.client.patch(
            f"/api/v1/plans/{created.id}/",
            {"title": "已修改标题"},
            format="json",
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        created.refresh_from_db()
        self.assertEqual(created.title, "已修改标题")

        delete_resp = self.client.delete(f"/api/v1/plans/{created.id}/")
        self.assertEqual(delete_resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(VideoPlan.objects.filter(pk=created.id).exists())

    @patch("apps.plans.ai_workflows.generate_single_plan")
    def test_generate_plan_creates_owned_plan(self, mock_generate_single_plan):
        mock_generate_single_plan.return_value = {
            "title": "AI 生成初稿",
            "summary": "生成简介",
            "content": {"positioning": "清晰定位"},
            "storyboard": [{"idx": 1, "duration": 3, "visual": "开场"}],
            "editing_advice": {"steps": ["加字幕"]},
            "ai_prompts": {"positive": "clean"},
        }

        self.authenticate()
        resp = self.client.post(
            "/api/v1/plans/generate/",
            {
                "direction": "vlog",
                "category": VideoPlan.Category.REAL,
                "is_ai_generated_video": False,
                "idea": "做一条咖啡店探访",
                "target_platform": "抖音",
                "target_audience": "城市白领",
                "duration_seconds": 30,
                "style": "轻松",
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        plan = VideoPlan.objects.get(pk=resp.data["id"])
        self.assertEqual(plan.user, self.user)
        self.assertEqual(plan.title, "AI 生成初稿")
        self.assertEqual(plan.content["positioning"], "清晰定位")
        self.assertIn("task_id", resp.data)
        task = AITask.objects.get(pk=resp.data["task_id"])
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.task_type, AITask.TaskType.GENERATE_PLAN)
        self.assertEqual(task.status, AITask.Status.SUCCEEDED)
        self.assertEqual(task.result_payload["plan_id"], str(plan.id))
        self.assertEqual(task.input_payload["idea"], "做一条咖啡店探访")
        self.assertEqual(plan.storyboard, [])
        self.assertEqual(plan.content["sections"][0]["storyboard"], [])
        mock_generate_single_plan.assert_called_once()

    def test_apply_ai_payload_keeps_section_storyboard_authoritative(self):
        plan = self.create_plan()
        plan.content = {
            "sections": [
                {"title": "章节 1", "summary": "铺垫", "storyboard": []},
                {"title": "章节 2", "summary": "推进", "storyboard": []},
            ]
        }
        plan.storyboard = []

        apply_ai_payload(plan, {
            "content": {
                "sections": [
                    {"title": "章节 1", "summary": "铺垫", "storyboard": []},
                    {
                        "title": "章节 2",
                        "summary": "推进",
                        "storyboard": [{"idx": 9, "duration": 30, "description": "第二章分镜"}],
                    },
                ]
            },
            "storyboard": [{"idx": 9, "duration": 30, "description": "第二章分镜"}],
        })

        self.assertEqual(plan.content["sections"][0]["storyboard"], [])
        self.assertEqual(plan.content["sections"][1]["storyboard"][0]["idx"], 1)
        self.assertEqual(plan.storyboard, [{"idx": 1, "duration": 30, "description": "第二章分镜"}])

    def test_apply_ai_payload_merges_single_section_storyboard_without_dropping_others(self):
        plan = self.create_plan()
        plan.content = {
            "sections": [
                {"title": "章节 1", "summary": "铺垫", "storyboard": [{"idx": 1, "duration": 3, "description": "第一章旧分镜"}]},
                {"title": "章节 2", "summary": "推进", "storyboard": [{"idx": 2, "duration": 3, "description": "第二章旧分镜"}]},
                {"title": "章节 3", "summary": "收束", "storyboard": [{"idx": 3, "duration": 3, "description": "第三章旧分镜"}]},
            ]
        }
        plan.storyboard = [
            {"idx": 1, "duration": 3, "description": "第一章旧分镜"},
            {"idx": 2, "duration": 3, "description": "第二章旧分镜"},
            {"idx": 3, "duration": 3, "description": "第三章旧分镜"},
        ]

        apply_ai_payload(
            plan,
            {
                "content": {
                    "sections": [
                        {"storyboard": [{"idx": 99, "duration": 8, "description": "第二章新分镜"}]},
                    ]
                },
                "storyboard": [{"idx": 99, "duration": 8, "description": "第二章新分镜"}],
            },
            scope="storyboard",
            hint="只为 content.sections[1] 生成分镜脚本。",
        )

        self.assertEqual(len(plan.content["sections"]), 3)
        self.assertEqual(plan.content["sections"][0]["storyboard"][0]["description"], "第一章旧分镜")
        self.assertEqual(plan.content["sections"][1]["storyboard"][0]["description"], "第二章新分镜")
        self.assertEqual(plan.content["sections"][2]["storyboard"][0]["description"], "第三章旧分镜")
        self.assertEqual([shot["idx"] for shot in plan.storyboard], [1, 2, 3])

    def test_apply_ai_payload_merges_top_level_section_storyboard_without_splitting_all_sections(self):
        plan = self.create_plan()
        plan.content = {
            "sections": [
                {"title": "章节 1", "summary": "铺垫", "storyboard": [{"idx": 1, "duration": 3, "description": "第一章旧分镜"}]},
                {"title": "章节 2", "summary": "推进", "storyboard": [{"idx": 2, "duration": 3, "description": "第二章旧分镜"}]},
            ]
        }

        apply_ai_payload(
            plan,
            {"storyboard": [{"idx": 9, "duration": 6, "description": "第二章新分镜"}]},
            scope="storyboard",
            hint="只为 content.sections[1] 生成分镜脚本。",
        )

        self.assertEqual(len(plan.content["sections"]), 2)
        self.assertEqual(plan.content["sections"][0]["storyboard"][0]["description"], "第一章旧分镜")
        self.assertEqual(plan.content["sections"][1]["storyboard"][0]["description"], "第二章新分镜")
        self.assertEqual(plan.storyboard[0]["description"], "第一章旧分镜")
        self.assertEqual(plan.storyboard[1]["description"], "第二章新分镜")

    @patch("apps.plans.views.build_creation_outline")
    def test_outline_returns_simple_payload_without_creating_plan(self, mock_build_creation_outline):
        mock_build_creation_outline.return_value = {
            "title": "咖啡探店大纲",
            "summary": "围绕一家咖啡店做探访视频",
            "plan_type": "single",
            "direction": "store_visit",
            "direction_label": "咖啡探店",
            "audience": "城市白领",
            "platform": "抖音",
            "style": "轻松",
            "duration_hint": "30 秒",
            "outline": [{"title": "开场", "note": "交代店铺反差"}],
            "key_points": ["店铺特色", "结尾反转"],
        }

        self.authenticate()
        resp = self.client.post(
            "/api/v1/plans/outline/",
            {
                "plan_type": "single",
                "idea": "做一条咖啡店探访",
                "target_platform": "抖音",
                "target_audience": "城市白领",
                "duration_seconds": 30,
                "style": "轻松",
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["title"], "咖啡探店大纲")
        self.assertEqual(VideoPlan.objects.count(), 0)
        mock_build_creation_outline.assert_called_once()

    @patch("apps.plans.ai_workflows.generate_single_plan")
    def test_generate_plan_no_inline_critique(self, mock_generate_single_plan):
        """V2 review flow: critique is no longer attached during generation —
        it only runs via the explicit POST /plans/{id}/review/ endpoint. This
        test guards the contract that even if services accidentally returns
        an `_ai_critique` field again, ai_workflows would not persist it
        because the helper now extracts only `content`."""
        mock_generate_single_plan.return_value = {
            "title": "无审稿方案",
            "summary": "",
            "content": {"positioning": "通用"},
            "storyboard": [{"idx": 1, "duration": 3, "description": "完整描述"}],
            "editing_advice": {},
            "ai_prompts": {},
        }

        self.authenticate()
        resp = self.client.post(
            "/api/v1/plans/generate/",
            {
                "direction": "ai_short_drama",
                "category": VideoPlan.Category.AI_GENERATED,
                "is_ai_generated_video": True,
                "idea": "校园悬疑",
                "duration_seconds": 45,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        plan = VideoPlan.objects.get(pk=resp.data["id"])
        self.assertEqual(plan.content["positioning"], "通用")
        self.assertNotIn("_ai_critique", plan.content)
        # 初始创建只保留章节规划,即使模型误返分镜也不直接入库。
        self.assertEqual(plan.storyboard, [])
        self.assertEqual(plan.content["sections"][0]["storyboard"], [])

    @patch("apps.plans.ai_workflows.generate_single_plan")
    def test_generate_plan_without_critique_stores_clean_content(self, mock_generate_single_plan):
        """When critique is disabled or missing, content must NOT contain a
        stale _ai_critique key — otherwise the editor would render a phantom
        panel from a previous generation."""
        mock_generate_single_plan.return_value = {
            "title": "无审稿方案",
            "summary": "",
            "content": {"positioning": "通用"},
            "storyboard": [],
            "editing_advice": {},
            "ai_prompts": {},
        }

        self.authenticate()
        resp = self.client.post(
            "/api/v1/plans/generate/",
            {
                "direction": "vlog",
                "category": VideoPlan.Category.REAL,
                "is_ai_generated_video": False,
                "idea": "城市漫步",
                "duration_seconds": 30,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        plan = VideoPlan.objects.get(pk=resp.data["id"])
        self.assertNotIn("_ai_critique", plan.content)

    @patch("apps.plans.ai_workflows.generate_single_plan")
    def test_generate_plan_records_failed_task_on_ai_payload_error(self, mock_generate_single_plan):
        mock_generate_single_plan.side_effect = AIPayloadError("模型返回格式错误")

        self.authenticate()
        resp = self.client.post(
            "/api/v1/plans/generate/",
            {
                "direction": "vlog",
                "category": VideoPlan.Category.REAL,
                "is_ai_generated_video": False,
                "idea": "做一条咖啡店探访",
                "target_platform": "抖音",
                "target_audience": "城市白领",
                "duration_seconds": 30,
                "style": "轻松",
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("task_id", resp.data)
        task = AITask.objects.get(pk=resp.data["task_id"])
        self.assertEqual(task.status, AITask.Status.FAILED)
        self.assertEqual(task.error, "模型返回格式错误")
        self.assertEqual(VideoPlan.objects.count(), 0)

    @patch("apps.plans.ai_workflows.generate_single_plan")
    def test_generate_plan_records_failed_task_on_ai_runtime_error(self, mock_generate_single_plan):
        mock_generate_single_plan.side_effect = RuntimeError("AI provider api_key is required")

        self.authenticate()
        resp = self.client.post(
            "/api/v1/plans/generate/",
            {
                "direction": "vlog",
                "category": VideoPlan.Category.REAL,
                "is_ai_generated_video": False,
                "idea": "做一条咖啡店探访",
                "target_platform": "抖音",
                "target_audience": "城市白领",
                "duration_seconds": 30,
                "style": "轻松",
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("task_id", resp.data)
        task = AITask.objects.get(pk=resp.data["task_id"])
        self.assertEqual(task.status, AITask.Status.FAILED)
        self.assertEqual(task.error, "AI provider api_key is required")
        self.assertEqual(resp.data["detail"], "AI provider api_key is required")
        self.assertEqual(VideoPlan.objects.count(), 0)

    @patch("apps.plans.views.enqueue_ai_task")
    def test_generate_plan_async_returns_queued_task(self, mock_enqueue_ai_task):
        self.authenticate()
        resp = self.client.post(
            "/api/v1/plans/generate/?async=1",
            {
                "direction": "vlog",
                "category": VideoPlan.Category.REAL,
                "is_ai_generated_video": False,
                "idea": "做一条咖啡店探访",
                "target_platform": "抖音",
                "target_audience": "城市白领",
                "duration_seconds": 30,
                "style": "轻松",
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(VideoPlan.objects.count(), 0)
        task = AITask.objects.get(pk=resp.data["id"])
        self.assertEqual(task.status, AITask.Status.QUEUED)
        self.assertEqual(task.task_type, AITask.TaskType.GENERATE_PLAN)
        self.assertEqual(task.input_payload["idea"], "做一条咖啡店探访")
        mock_enqueue_ai_task.assert_called_once_with(task)

    @patch("apps.plans.ai_workflows.optimize_plan")
    def test_optimize_plan_merges_payload_and_resets_optimizing_status(self, mock_optimize_plan):
        plan = self.create_plan()
        plan.status = VideoPlan.Status.OPTIMIZING
        plan.save()
        mock_optimize_plan.return_value = {
            "title": "优化后标题",
            "summary": "优化后简介",
            "content": {"new_field": "新增内容"},
        }

        self.authenticate()
        resp = self.client.post(
            f"/api/v1/plans/{plan.id}/optimize/",
            {"scope": "full"},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        plan.refresh_from_db()
        self.assertEqual(plan.title, "优化后标题")
        self.assertEqual(plan.summary, "优化后简介")
        self.assertEqual(plan.content["new_field"], "新增内容")
        self.assertEqual(plan.status, VideoPlan.Status.DRAFT)
        self.assertIn("task_id", resp.data)
        task = AITask.objects.get(pk=resp.data["task_id"])
        self.assertEqual(task.task_type, AITask.TaskType.OPTIMIZE_PLAN)
        self.assertEqual(task.status, AITask.Status.SUCCEEDED)
        self.assertEqual(task.result_payload["scope"], "full")
        self.assertEqual(task.result_payload["plan_id"], str(plan.id))
        mock_optimize_plan.assert_called_once()

    def test_duplicate_plan_creates_draft_copy(self):
        plan = self.create_plan()
        plan.status = VideoPlan.Status.CONFIRMED
        plan.save()

        self.authenticate()
        resp = self.client.post(f"/api/v1/plans/{plan.id}/duplicate/", {}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        copy = VideoPlan.objects.get(pk=resp.data["id"])
        self.assertNotEqual(copy.id, plan.id)
        self.assertEqual(copy.user, self.user)
        self.assertEqual(copy.status, VideoPlan.Status.DRAFT)
        self.assertTrue(copy.title.endswith("副本"))

    def test_asset_crud_is_user_scoped(self):
        self.authenticate()
        resp = self.client.post(
            "/api/v1/assets/characters/",
            {
                "name": "主角A",
                "payload": {"role": "博主"},
                "fixed_traits": ["发色"],
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        asset = CharacterAsset.objects.get(pk=resp.data["id"])
        self.assertEqual(asset.user, self.user)

        self.authenticate(self.other_user)
        resp = self.client.get("/api/v1/assets/characters/")
        self.assertEqual(
            resp.status_code,
            status.HTTP_200_OK,
            getattr(resp, "data", resp.content[:200]),
        )
        self.assertEqual(resp.data["results"], [])

        resp = self.client.get(f"/api/v1/assets/characters/{asset.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_series_rejects_other_users_assets(self):
        own_asset = CharacterAsset.objects.create(user=self.user, name="自己的角色")
        other_asset = CharacterAsset.objects.create(user=self.other_user, name="别人的角色")

        self.authenticate()
        resp = self.client.post(
            "/api/v1/series/",
            {
                "title": "不能绑定别人的资产",
                "direction": "vlog",
                "characters": [str(other_asset.id)],
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("characters", resp.data)

        resp = self.client.post(
            "/api/v1/series/",
            {
                "title": "可绑定自己的资产",
                "direction": "vlog",
                "characters": [str(own_asset.id)],
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        series = SeriesPlan.objects.get(pk=resp.data["id"])
        self.assertEqual(list(series.characters.values_list("id", flat=True)), [own_asset.id])

    def test_video_plan_rejects_other_users_series(self):
        plan = self.create_plan()
        own_series = self.create_series(title="自己的系列")
        other_series = self.create_series(user=self.other_user, title="别人的系列")

        self.authenticate()
        resp = self.client.patch(
            f"/api/v1/plans/{plan.id}/",
            {"series": str(other_series.id)},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("series", resp.data)
        plan.refresh_from_db()
        self.assertIsNone(plan.series)

        resp = self.client.patch(
            f"/api/v1/plans/{plan.id}/",
            {"series": str(own_series.id)},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        plan.refresh_from_db()
        self.assertEqual(plan.series, own_series)

    @patch("apps.plans.ai_workflows.generate_series_plan")
    def test_generate_series_records_task_and_creates_assets(self, mock_generate_series):
        mock_generate_series.return_value = {
            "title": "AI 生成系列",
            "summary": "系列简介",
            "positioning": {"core_concept": "连续选题"},
            "episode_template": {"sections": [{"name": "开场"}]},
            "visual_style": {"tone": "明亮"},
            "title_style": {"pattern": "数字 + 结果"},
            "initial_topics": ["第一集", "第二集"],
            "assets": {
                "characters": [
                    {
                        "name": "固定主角",
                        "payload": {"role": "博主"},
                        "fixed_traits": ["黑发"],
                    }
                ]
            },
        }

        self.authenticate()
        resp = self.client.post(
            "/api/v1/series/generate/",
            {
                "direction": "vlog",
                "idea": "做一个咖啡探店系列",
                "target_platform": "抖音",
                "target_audience": "城市白领",
                "update_frequency": "周更",
                "episode_duration_seconds": 60,
                "planned_episodes": 12,
                "style": "轻松",
                "auto_create_assets": True,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        series = SeriesPlan.objects.get(pk=resp.data["id"])
        self.assertEqual(series.title, "AI 生成系列")
        self.assertEqual(series.characters.count(), 1)
        self.assertIn("task_id", resp.data)
        task = AITask.objects.get(pk=resp.data["task_id"])
        self.assertEqual(task.task_type, AITask.TaskType.GENERATE_SERIES)
        self.assertEqual(task.status, AITask.Status.SUCCEEDED)
        self.assertEqual(task.result_payload["series_id"], str(series.id))
        self.assertTrue(task.input_payload["auto_create_assets"])

    @patch("apps.plans.ai_workflows.generate_series_plan")
    def test_generate_series_repairs_missing_characters_and_big_environment_asset(self, mock_generate_series):
        mock_generate_series.return_value = {
            "title": "熊出没之暗网风云",
            "summary": "光头强误入暗网后引发的连载短剧",
            "direction": "ai_short_drama",
            "positioning": {"core_concept": "森林反转短剧"},
            "assets": {
                "characters": [],
                "worldviews": [
                    {
                        "name": "森林日常",
                        "payload": {
                            "purpose": "所有角色共同所处的森林背景",
                            "tone_color": "浅绿色、荒诞、紧张",
                            "fixed_details": ["森林秩序会被超能力打破"],
                        },
                        "fixed_traits": [],
                    }
                ],
            },
        }

        idea = """
熊出没之暗网风云：五号化合物
光头强又被李老板扣光了工资。
熊大（外号“屠夫”）：研究如何对抗光头强。
吉吉国王（外号“法兰奇”）：研制毒气。
毛毛（外号“喜美子”）：拥有自愈能力。
蹦蹦：负责情报收集。
熊二（外号“休伊”）：被迫拿起武器。
"""
        self.authenticate()
        resp = self.client.post(
            "/api/v1/series/generate/",
            {
                "direction": "ai_short_drama",
                "idea": idea,
                "target_platform": "抖音",
                "auto_create_assets": True,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        series = SeriesPlan.objects.get(pk=resp.data["id"])
        character_names = set(series.characters.values_list("name", flat=True))
        self.assertIn("光头强", character_names)
        self.assertIn("熊大", character_names)
        self.assertIn("熊二", character_names)
        self.assertNotIn("熊出没之暗网风云", character_names)
        self.assertEqual(series.worldviews.count(), 0)
        self.assertEqual(series.positioning["big_environment"]["name"], "森林日常")
        self.assertFalse(WorldviewAsset.objects.filter(user=self.user, name="森林日常").exists())

    @patch("apps.plans.ai_workflows.generate_series_plan")
    def test_generate_series_maps_asset_relationships_to_canvas_assets(self, mock_generate_series):
        mock_generate_series.return_value = {
            "title": "独居女孩日常",
            "summary": "女孩和城市角落的温暖故事",
            "direction": "ai_short_drama",
            "positioning": {
                "core_concept": "城市治愈日常",
                "big_environment": {
                    "name": "老城区",
                    "description": "所有角色共同生活的城市街区",
                },
            },
            "assets": {
                "characters": [
                    {"name": "林小满", "payload": {"role": "主角"}, "fixed_traits": ["独居女孩"]}
                ],
                "worldviews": [
                    {"name": "林小满的出租屋", "payload": {"purpose": "居住环境"}, "fixed_traits": ["窗边有绿植"]}
                ],
            },
            "relationships": [
                {
                    "from": "林小满",
                    "from_type": "characters",
                    "to": "林小满的出租屋",
                    "to_type": "worldviews",
                    "label": "居住",
                }
            ],
        }

        self.authenticate()
        resp = self.client.post(
            "/api/v1/series/generate/",
            {
                "direction": "ai_short_drama",
                "idea": "林小满住在老城区出租屋,记录独居生活。",
                "auto_create_assets": True,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        series = SeriesPlan.objects.get(pk=resp.data["id"])
        character = series.characters.get(name="林小满")
        worldview = series.worldviews.get(name="林小满的出租屋")
        relationship = series.positioning["relationships"][0]
        self.assertEqual(relationship["from_asset_id"], str(character.id))
        self.assertEqual(relationship["from_asset_type"], "characters")
        self.assertEqual(relationship["to_asset_id"], str(worldview.id))
        self.assertEqual(relationship["to_asset_type"], "worldviews")
        self.assertEqual(relationship["label"], "居住")

    @patch("apps.plans.ai_workflows.generate_episode_plan")
    def test_generate_episode_sets_category_from_series_direction(self, mock_generate_episode):
        mock_generate_episode.return_value = {
            "title": "第 1 集",
            "summary": "测试单集",
            "content": {"positioning": "开场"},
            "storyboard": [{"idx": 1, "duration": 3, "visual": "画面", "line": "旁白"}],
            "editing_advice": {"steps": ["快切"]},
            "ai_prompts": {"positive": "cinematic"},
        }
        ai_series = self.create_series(direction="ai_short_drama", title="AI短剧")
        real_series = self.create_series(direction="vlog", title="真实拍摄")

        self.authenticate()
        resp = self.client.post(
            f"/api/v1/series/{ai_series.id}/episodes/",
            {"topic": "转校生收到匿名纸条"},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["category"], VideoPlan.Category.AI_GENERATED)
        self.assertTrue(resp.data["is_ai_generated_video"])
        self.assertIn("task_id", resp.data)

        resp = self.client.post(
            f"/api/v1/series/{real_series.id}/episodes/",
            {"topic": "城市咖啡店探访"},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["category"], VideoPlan.Category.REAL)
        self.assertFalse(resp.data["is_ai_generated_video"])
        self.assertIn("task_id", resp.data)
        tasks = AITask.objects.filter(task_type=AITask.TaskType.GENERATE_EPISODE).order_by("created_at")
        self.assertEqual(tasks.count(), 2)
        self.assertEqual(tasks[0].status, AITask.Status.SUCCEEDED)
        self.assertEqual(tasks[0].result_payload["series_id"], str(ai_series.id))

    @patch("apps.plans.ai_workflows.generate_episode_plan")
    def test_generate_episode_returns_asset_suggestions_without_creating_assets(self, mock_generate_episode):
        mock_generate_episode.return_value = {
            "title": "暗网风云第一集",
            "summary": "新角色登场",
            "content": {"sections": [{"title": "开头", "summary": "发现新线索", "storyboard": []}]},
            "storyboard": [],
            "asset_suggestions": {
                "characters": [
                    {"name": "光头强", "payload": {"role": "已有角色"}, "fixed_traits": []},
                    {"name": "熊大", "payload": {"role": "新增核心角色"}, "fixed_traits": ["冷静"]},
                ],
                "worldviews": [
                    {"name": "狗熊岭", "payload": {"purpose": "所有角色共同所处的大环境"}, "fixed_traits": []},
                    {"name": "树屋基地", "payload": {"tone_color": "昏暗绿光", "purpose": "临时据点"}, "fixed_traits": ["藏在森林深处"]},
                ],
                "relationships": [
                    {
                        "from": "熊大",
                        "from_type": "characters",
                        "to": "树屋基地",
                        "to_type": "worldviews",
                        "label": "据点",
                    }
                ],
            },
        }
        series = self.create_series(
            direction="ai_short_drama",
            title="熊出没之暗网风云",
        )
        series.positioning = {
            "big_environment": {
                "name": "狗熊岭",
                "description": "所有角色共同所处的森林大环境",
            }
        }
        series.save()
        character = CharacterAsset.objects.create(user=self.user, name="光头强")
        series.characters.add(character)

        self.authenticate()
        resp = self.client.post(
            f"/api/v1/series/{series.id}/episodes/",
            {"topic": "熊大加入对抗光头强"},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        suggestions = resp.data["asset_suggestions"]
        self.assertEqual([item["name"] for item in suggestions["characters"]], ["熊大"])
        self.assertEqual([item["name"] for item in suggestions["worldviews"]], ["树屋基地"])
        self.assertEqual(suggestions["relationships"][0]["label"], "据点")
        self.assertEqual(suggestions["relationships"][0]["from_asset_type"], "characters")
        self.assertEqual(suggestions["relationships"][0]["to_asset_type"], "worldviews")
        self.assertEqual(series.characters.count(), 1)
        self.assertFalse(CharacterAsset.objects.filter(user=self.user, name="熊大").exists())
        self.assertFalse(WorldviewAsset.objects.filter(user=self.user, name="树屋基地").exists())
        task = AITask.objects.get(pk=resp.data["task_id"])
        self.assertEqual(task.result_payload["asset_suggestions"], suggestions)

    @patch("apps.plans.ai_workflows.check_series_consistency")
    def test_check_consistency_returns_ai_report(self, mock_check_consistency):
        mock_check_consistency.return_value = {
            "score": 82,
            "issues": [
                {
                    "level": "warning",
                    "asset_type": "characters",
                    "asset_id": None,
                    "field": "appearance",
                    "plan_id": None,
                    "message": "角色外观有轻微漂移",
                    "suggestion": "保持固定发色",
                }
            ],
        }
        series = self.create_series(direction="ai_short_drama")
        self.create_plan(series=series)

        self.authenticate()
        resp = self.client.post(
            f"/api/v1/series/{series.id}/check-consistency/",
            {},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["score"], 82)
        self.assertEqual(resp.data["issues"][0]["message"], "角色外观有轻微漂移")
        self.assertIn("task_id", resp.data)
        task = AITask.objects.get(pk=resp.data["task_id"])
        self.assertEqual(task.task_type, AITask.TaskType.CHECK_CONSISTENCY)
        self.assertEqual(task.status, AITask.Status.SUCCEEDED)
        self.assertEqual(task.result_payload["score"], 82)
        mock_check_consistency.assert_called_once()

    def test_check_consistency_without_episodes_records_task(self):
        series = self.create_series(direction="vlog")

        self.authenticate()
        resp = self.client.post(
            f"/api/v1/series/{series.id}/check-consistency/",
            {},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["score"], 100)
        self.assertEqual(resp.data["issues"], [])
        task = AITask.objects.get(pk=resp.data["task_id"])
        self.assertEqual(task.status, AITask.Status.SUCCEEDED)
        self.assertEqual(task.result_payload["score"], 100)

    def test_export_markdown_and_docx(self):
        plan = self.create_plan()
        self.authenticate()

        resp = self.client.get(f"/api/v1/plans/{plan.id}/export/?format=md")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp["Content-Type"].startswith("text/markdown"))
        self.assertIn("filename*=UTF-8''", resp["Content-Disposition"])
        self.assertIn("测试方案", resp.content.decode("utf-8"))
        self.assertIn("欢迎观看", resp.content.decode("utf-8"))

        resp = self.client.get(f"/api/v1/plans/{plan.id}/export/?format=docx")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            resp["Content-Type"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertTrue(resp.content.startswith(b"PK"))

    @patch("apps.exports.services._render_pdf_with_weasyprint")
    def test_export_pdf(self, mock_render_pdf):
        mock_render_pdf.return_value = b"%PDF-1.7\n..."
        plan = self.create_plan()
        self.authenticate()

        resp = self.client.get(f"/api/v1/plans/{plan.id}/export/?format=pdf")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertTrue(resp.content.startswith(b"%PDF"))
        mock_render_pdf.assert_called_once()

    def test_export_rejects_unknown_format(self):
        plan = self.create_plan()
        self.authenticate()

        resp = self.client.get(f"/api/v1/plans/{plan.id}/export/?format=xlsx")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("暂不支持", resp.data["detail"])

    def test_export_series_markdown_and_docx(self):
        series = self.create_series()
        character = CharacterAsset.objects.create(
            user=self.user,
            name="主角A",
            payload={"role": "博主"},
            fixed_traits=["发色"],
        )
        series.characters.add(character)
        self.create_plan(series=series)

        self.authenticate()
        resp = self.client.get(f"/api/v1/series/{series.id}/export/?format=md")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp["Content-Type"].startswith("text/markdown"))
        body = resp.content.decode("utf-8")
        self.assertIn("测试系列", body)
        self.assertIn("第一集选题", body)
        self.assertIn("主角A", body)
        self.assertIn("测试方案", body)

        resp = self.client.get(f"/api/v1/series/{series.id}/export/?format=docx")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            resp["Content-Type"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertTrue(resp.content.startswith(b"PK"))

    def test_export_series_rejects_unknown_format(self):
        series = self.create_series()
        self.authenticate()

        resp = self.client.get(f"/api/v1/series/{series.id}/export/?format=pdf")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.plans.views.review_plan")
    def test_review_endpoint_returns_critique(self, mock_review_plan):
        mock_review_plan.return_value = {
            "score": 82,
            "axes": [{"name": "钩子强度", "score": 85, "comment": "强反差,可保留"}],
            "issues": [{"severity": "minor", "field": "storyboard[0].description", "comment": "可再细化光线"}],
            "summary": "整体可用",
        }
        plan = self.create_plan()
        self.authenticate()

        resp = self.client.post(f"/api/v1/plans/{plan.id}/review/", {}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["score"], 82)
        self.assertEqual(resp.data["issues"][0]["severity"], "minor")
        kwargs = mock_review_plan.call_args.kwargs
        self.assertEqual(kwargs["plan_dict"]["direction"], "vlog")

    def test_review_endpoint_is_user_scoped(self):
        other_plan = self.create_plan(user=self.other_user)
        self.authenticate()

        resp = self.client.post(f"/api/v1/plans/{other_plan.id}/review/", {}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    @patch("apps.plans.views.review_plan")
    def test_review_endpoint_swallows_critic_errors(self, mock_review_plan):
        """If the upstream provider explodes, /review/ must still return 200
        with a 0-score sentinel so the editor's modal can show 'audit failed,
        confirm anyway?' instead of a stack trace."""
        mock_review_plan.side_effect = RuntimeError("provider blew up")
        plan = self.create_plan()
        self.authenticate()

        resp = self.client.post(f"/api/v1/plans/{plan.id}/review/", {}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["score"], 0)
        self.assertIn("审稿失败", resp.data["summary"])

    @patch("apps.plans.views.rewrite_field")
    def test_rewrite_returns_candidates_for_allowed_path(self, mock_rewrite_field):
        mock_rewrite_field.return_value = {
            "candidates": [
                {"value": "更猛的钩子 A", "reason": "强冲突"},
                {"value": "更猛的钩子 B", "reason": "悬念"},
            ],
        }
        plan = self.create_plan()
        self.authenticate()

        resp = self.client.post(
            f"/api/v1/plans/{plan.id}/rewrite/",
            {"path": "title", "hint": "更冲突", "count": 2},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["candidates"]), 2)
        self.assertEqual(resp.data["candidates"][0]["value"], "更猛的钩子 A")
        # Ensure direction context + current value get propagated to the service.
        kwargs = mock_rewrite_field.call_args.kwargs
        self.assertEqual(kwargs["path"], "title")
        self.assertEqual(kwargs["hint"], "更冲突")
        self.assertEqual(kwargs["current_value"], "测试方案")
        self.assertEqual(kwargs["plan_dict"]["direction"], "vlog")

    def test_rewrite_rejects_disallowed_path(self):
        """Path allowlist is enforced — clients can't probe arbitrary fields."""
        plan = self.create_plan()
        self.authenticate()

        resp = self.client.post(
            f"/api/v1/plans/{plan.id}/rewrite/",
            {"path": "user", "count": 3},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("不支持改写", resp.data["detail"])

    def test_rewrite_rejects_malformed_path(self):
        plan = self.create_plan()
        self.authenticate()

        resp = self.client.post(
            f"/api/v1/plans/{plan.id}/rewrite/",
            {"path": "../etc/passwd"},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rewrite_returns_400_when_target_is_missing(self):
        """Path resolves to an out-of-range storyboard index — should 400, not 500."""
        plan = self.create_plan()
        self.authenticate()

        resp = self.client.post(
            f"/api/v1/plans/{plan.id}/rewrite/",
            {"path": "storyboard[42].line"},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rewrite_is_user_scoped(self):
        """A user cannot rewrite someone else's plan even if they know the UUID."""
        other_plan = self.create_plan(user=self.other_user)
        self.authenticate()

        resp = self.client.post(
            f"/api/v1/plans/{other_plan.id}/rewrite/",
            {"path": "title"},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    @patch("apps.plans.views.rewrite_field")
    def test_rewrite_passes_storyboard_context(self, mock_rewrite_field):
        """Storyboard rewrites must hand the AI the current shot + neighbours."""
        mock_rewrite_field.return_value = {"candidates": [{"value": "新台词", "reason": ""}]}
        plan = self.create_plan()
        self.authenticate()

        resp = self.client.post(
            f"/api/v1/plans/{plan.id}/rewrite/",
            {"path": "storyboard[0].line"},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        kwargs = mock_rewrite_field.call_args.kwargs
        self.assertEqual(kwargs["current_value"], "欢迎观看")
        self.assertIn("this_shot", kwargs["context"])
        self.assertEqual(kwargs["context"]["this_shot"]["visual"], "开场画面")
