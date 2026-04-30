from rest_framework.routers import DefaultRouter

from .views import (
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

urlpatterns = router.urls
