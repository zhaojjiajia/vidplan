"""Routes for user-defined asset categories (`CustomAssetKind`) and the
asset instances that belong to them (`CustomAsset`).

Mounted at /api/v1/asset-kinds/ and /api/v1/custom-assets/ respectively
(via the dual prefix in vidplan/urls.py).
"""
from rest_framework.routers import DefaultRouter

from .views import CustomAssetKindViewSet, CustomAssetViewSet

router = DefaultRouter()
router.register(r"", CustomAssetKindViewSet, basename="custom-asset-kind")

urlpatterns = router.urls
