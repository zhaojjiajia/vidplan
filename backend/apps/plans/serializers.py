from rest_framework import serializers

from apps.assets.models import CharacterAsset, ColumnAsset, StyleAsset, WorldviewAsset

from .models import SeriesPlan, VideoPlan


ASSET_FIELD_MODELS = {
    "characters": CharacterAsset,
    "styles": StyleAsset,
    "worldviews": WorldviewAsset,
    "columns": ColumnAsset,
}


class VideoPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoPlan
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if "series" in self.fields:
            if user and user.is_authenticated:
                self.fields["series"].queryset = SeriesPlan.objects.filter(user=user)
            else:
                self.fields["series"].queryset = SeriesPlan.objects.none()


class EpisodeSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoPlan
        fields = ("id", "title", "status", "duration_seconds", "updated_at")
        read_only_fields = fields


class SeriesPlanSerializer(serializers.ModelSerializer):
    episode_count = serializers.IntegerField(source="episodes.count", read_only=True)
    episodes = EpisodeSummarySerializer(many=True, read_only=True)

    class Meta:
        model = SeriesPlan
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at", "updated_at", "episodes", "episode_count")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        for field_name, model_cls in ASSET_FIELD_MODELS.items():
            if field_name not in self.fields:
                continue
            if user and user.is_authenticated:
                self.fields[field_name].child_relation.queryset = model_cls.objects.filter(user=user)
            else:
                self.fields[field_name].child_relation.queryset = model_cls.objects.none()


class GenerateInputSerializer(serializers.Serializer):
    direction = serializers.CharField(max_length=64)
    category = serializers.ChoiceField(choices=VideoPlan.Category.choices)
    is_ai_generated_video = serializers.BooleanField(default=False)
    idea = serializers.CharField()

    target_platform = serializers.CharField(max_length=32, required=False, allow_blank=True, default="抖音")
    target_audience = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    duration_seconds = serializers.IntegerField(required=False, default=30)
    style = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")


class OptimizeInputSerializer(serializers.Serializer):
    scope = serializers.ChoiceField(
        choices=["full", "title", "hook", "storyboard", "editing", "ai_prompt"],
        default="full",
    )


class SeriesGenerateInputSerializer(serializers.Serializer):
    direction = serializers.CharField(max_length=64)
    idea = serializers.CharField()

    target_platform = serializers.CharField(max_length=32, required=False, allow_blank=True, default="抖音")
    target_audience = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    update_frequency = serializers.CharField(max_length=64, required=False, allow_blank=True, default="周更")
    episode_duration_seconds = serializers.IntegerField(required=False, default=60)
    planned_episodes = serializers.IntegerField(required=False, default=10)
    style = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    auto_create_assets = serializers.BooleanField(required=False, default=True)


class EpisodeGenerateInputSerializer(serializers.Serializer):
    topic = serializers.CharField()
    episode_goal = serializers.CharField(required=False, allow_blank=True, default="")
    extra_requirements = serializers.CharField(required=False, allow_blank=True, default="")


class ConsistencyCheckInputSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField(required=False, allow_null=True)
    scope = serializers.ChoiceField(choices=["all", "single"], required=False, default="all")
