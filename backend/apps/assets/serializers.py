from rest_framework import serializers

from .models import (
    CharacterAsset,
    ColumnAsset,
    CustomAsset,
    CustomAssetKind,
    StyleAsset,
    WorldviewAsset,
)


def _factory(model_cls):
    class Meta:
        model = model_cls
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at", "updated_at")

    return type(f"{model_cls.__name__}Serializer", (serializers.ModelSerializer,), {"Meta": Meta})


CharacterAssetSerializer = _factory(CharacterAsset)
StyleAssetSerializer = _factory(StyleAsset)
WorldviewAssetSerializer = _factory(WorldviewAsset)
ColumnAssetSerializer = _factory(ColumnAsset)


class CustomAssetKindSerializer(serializers.ModelSerializer):
    asset_count = serializers.IntegerField(source="assets.count", read_only=True)

    class Meta:
        model = CustomAssetKind
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at", "updated_at", "asset_count")


class CustomAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomAsset
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Restrict the writable `kind` to the requesting user's kinds —
        # otherwise a user could parent their assets under another user's
        # custom kind by guessing the UUID.
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if "kind" in self.fields:
            if user and user.is_authenticated:
                self.fields["kind"].queryset = CustomAssetKind.objects.filter(user=user)
            else:
                self.fields["kind"].queryset = CustomAssetKind.objects.none()
