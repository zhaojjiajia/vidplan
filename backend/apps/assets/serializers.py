from rest_framework import serializers

from .models import CharacterAsset, ColumnAsset, StyleAsset, WorldviewAsset


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
