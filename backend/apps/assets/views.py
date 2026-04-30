from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.core.permissions import IsOwner

from .models import CharacterAsset, ColumnAsset, StyleAsset, WorldviewAsset
from .serializers import (
    CharacterAssetSerializer,
    ColumnAssetSerializer,
    StyleAssetSerializer,
    WorldviewAssetSerializer,
)


class _OwnedViewSet(viewsets.ModelViewSet):
    permission_classes = (IsOwner,)
    queryset = None
    serializer_class = None
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("name",)
    ordering_fields = ("name", "updated_at", "created_at")
    ordering = ("-updated_at",)

    def get_queryset(self):
        return self.queryset.model.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CharacterAssetViewSet(_OwnedViewSet):
    queryset = CharacterAsset.objects.all()
    serializer_class = CharacterAssetSerializer


class StyleAssetViewSet(_OwnedViewSet):
    queryset = StyleAsset.objects.all()
    serializer_class = StyleAssetSerializer


class WorldviewAssetViewSet(_OwnedViewSet):
    queryset = WorldviewAsset.objects.all()
    serializer_class = WorldviewAssetSerializer


class ColumnAssetViewSet(_OwnedViewSet):
    queryset = ColumnAsset.objects.all()
    serializer_class = ColumnAssetSerializer
