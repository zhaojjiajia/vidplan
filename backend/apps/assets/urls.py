from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AssetAIImageGenerateView,
    AssetImageUploadView,
    CharacterAssetViewSet,
    ColumnAssetViewSet,
    StyleAssetViewSet,
    WorldviewAssetViewSet,
)

router = DefaultRouter()
router.register(r"characters", CharacterAssetViewSet, basename="character-asset")
router.register(r"styles", StyleAssetViewSet, basename="style-asset")
router.register(r"worldviews", WorldviewAssetViewSet, basename="worldview-asset")
router.register(r"columns", ColumnAssetViewSet, basename="column-asset")

urlpatterns = [
    path("upload-image/", AssetImageUploadView.as_view(), name="asset-image-upload"),
    path("generate-image/", AssetAIImageGenerateView.as_view(), name="asset-image-generate"),
    *router.urls,
]
