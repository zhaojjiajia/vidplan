from django.contrib import admin
from django.urls import include, path

api_v1 = [
    path("auth/", include("apps.accounts.urls")),
    path("plans/", include("apps.plans.urls")),
    path("series/", include("apps.plans.urls_series")),
    path("assets/", include("apps.assets.urls")),
    path("ai-settings/", include("apps.ai.urls")),
    path("ai-tasks/", include("apps.ai.urls_tasks")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
]
