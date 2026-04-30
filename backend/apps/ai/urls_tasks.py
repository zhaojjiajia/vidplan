from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AITaskEventsView, AITaskViewSet

router = DefaultRouter()
router.register(r"", AITaskViewSet, basename="ai-task")

urlpatterns = [
    path("<uuid:pk>/events/", AITaskEventsView.as_view(), name="ai-task-events"),
    *router.urls,
]
