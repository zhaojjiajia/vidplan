"""CRUD routes for user-created asset instances (CustomAsset).

Mounted at /api/v1/custom-assets/. Use ?kind=<uuid> to scope listing to a
specific custom kind.
"""
from rest_framework.routers import DefaultRouter

from .views import CustomAssetViewSet

router = DefaultRouter()
router.register(r"", CustomAssetViewSet, basename="custom-asset")

urlpatterns = router.urls
