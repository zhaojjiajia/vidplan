from rest_framework.routers import DefaultRouter

from .views import VideoPlanViewSet

router = DefaultRouter()
router.register(r"", VideoPlanViewSet, basename="videoplan")

urlpatterns = router.urls
