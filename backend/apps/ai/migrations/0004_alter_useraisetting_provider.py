from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0003_rename_ai_aitask_user_id_fcb44f_idx_ai_aitask_user_id_6959a8_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="useraisetting",
            name="provider",
            field=models.CharField(
                choices=[
                    ("openai", "ChatGPT"),
                    ("qwen", "通义千问 (Qwen)"),
                    ("anthropic", "Anthropic"),
                ],
                default="openai",
                max_length=32,
            ),
        ),
    ]
