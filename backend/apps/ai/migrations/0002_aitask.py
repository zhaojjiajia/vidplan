import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AITask",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "task_type",
                    models.CharField(
                        choices=[
                            ("generate_plan", "生成单条方案"),
                            ("optimize_plan", "优化方案"),
                            ("generate_series", "生成系列"),
                            ("generate_episode", "生成单集"),
                            ("check_consistency", "一致性检查"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "排队中"),
                            ("running", "执行中"),
                            ("succeeded", "已完成"),
                            ("failed", "失败"),
                            ("canceled", "已取消"),
                        ],
                        default="queued",
                        max_length=16,
                    ),
                ),
                ("title", models.CharField(blank=True, default="", max_length=200)),
                ("progress", models.PositiveSmallIntegerField(default=0)),
                ("input_payload", models.JSONField(blank=True, default=dict)),
                ("result_payload", models.JSONField(blank=True, default=dict)),
                ("error", models.TextField(blank=True, default="")),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-updated_at",),
                "indexes": [
                    models.Index(fields=["user", "status", "-updated_at"], name="ai_aitask_user_id_fcb44f_idx"),
                    models.Index(fields=["task_type", "-updated_at"], name="ai_aitask_task_ty_b1d13f_idx"),
                ],
            },
        ),
    ]
