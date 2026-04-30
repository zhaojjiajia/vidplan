from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserAISetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "provider",
                    models.CharField(
                        choices=[("openai", "OpenAI"), ("qwen", "通义千问 (Qwen)")],
                        default="openai",
                        max_length=32,
                    ),
                ),
                ("api_key", models.CharField(blank=True, default="", max_length=512)),
                ("model", models.CharField(blank=True, default="", max_length=128)),
                ("base_url", models.URLField(blank=True, default="")),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        related_name="ai_setting",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "AI 设置",
                "verbose_name_plural": "AI 设置",
            },
        ),
    ]
