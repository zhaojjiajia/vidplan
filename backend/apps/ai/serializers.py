from __future__ import annotations

from rest_framework import serializers

from .models import AITask, UserAISetting


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}{'*' * 6}{key[-4:]}"


class UserAISettingSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=512)
    api_key_masked = serializers.SerializerMethodField()
    has_api_key = serializers.SerializerMethodField()
    resolved_model = serializers.SerializerMethodField()
    resolved_base_url = serializers.SerializerMethodField()

    class Meta:
        model = UserAISetting
        fields = (
            "provider",
            "model",
            "base_url",
            "api_key",
            "api_key_masked",
            "has_api_key",
            "resolved_model",
            "resolved_base_url",
        )

    def get_api_key_masked(self, obj: UserAISetting) -> str:
        return _mask_key(obj.api_key)

    def get_has_api_key(self, obj: UserAISetting) -> bool:
        return bool(obj.api_key)

    def get_resolved_model(self, obj: UserAISetting) -> str:
        return obj.resolved_model()

    def get_resolved_base_url(self, obj: UserAISetting) -> str:
        return obj.resolved_base_url()

    def update(self, instance: UserAISetting, validated_data: dict) -> UserAISetting:
        # Empty string for api_key in PUT means "leave unchanged".
        new_key = validated_data.pop("api_key", None)
        if new_key:
            instance.api_key = new_key
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance


class AISettingTestSerializer(serializers.Serializer):
    """Optional override fields — if omitted the saved setting is used."""

    provider = serializers.ChoiceField(choices=UserAISetting.Provider.choices, required=False)
    api_key = serializers.CharField(required=False, allow_blank=True, max_length=512)
    model = serializers.CharField(required=False, allow_blank=True, max_length=128)
    base_url = serializers.URLField(required=False, allow_blank=True)


class MarkdownImportFieldSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=64)
    label = serializers.CharField(max_length=120, required=False, allow_blank=True)
    kind = serializers.ChoiceField(choices=["text", "textarea", "lines"], required=False)


class MarkdownImportAnalyzeSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=["plan", "asset"])
    markdown = serializers.CharField(trim_whitespace=False, max_length=100000)
    asset_type = serializers.ChoiceField(
        choices=["characters", "styles", "worldviews", "columns"],
        required=False,
    )
    asset_title = serializers.CharField(max_length=120, required=False, allow_blank=True)
    fields = MarkdownImportFieldSerializer(many=True, required=False)

    def validate(self, attrs):
        if attrs["mode"] == "asset":
            if not attrs.get("asset_type"):
                raise serializers.ValidationError({"asset_type": "资产导入必须提供资产类型"})
            if not attrs.get("fields"):
                raise serializers.ValidationError({"fields": "资产导入必须提供字段列表"})
        return attrs


class AITaskSerializer(serializers.ModelSerializer):
    task_type_label = serializers.CharField(source="get_task_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = AITask
        fields = (
            "id",
            "task_type",
            "task_type_label",
            "status",
            "status_label",
            "title",
            "progress",
            "input_payload",
            "result_payload",
            "error",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
