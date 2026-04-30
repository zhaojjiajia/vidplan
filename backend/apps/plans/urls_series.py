from rest_framework.routers import DefaultRouter

from .views import SeriesPlanViewSet

router = DefaultRouter()
router.register(r"", SeriesPlanViewSet, basename="seriesplan")

urlpatterns = router.urls
