from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

api_v1 = [
    path("auth/", include("apps.accounts.urls")),
    path("plans/", include("apps.plans.urls")),
    path("series/", include("apps.plans.urls_series")),
    path("assets/", include("apps.assets.urls")),
    path("asset-kinds/", include("apps.assets.urls_kinds")),
    path("custom-assets/", include("apps.assets.urls_custom_assets")),
    path("ai-settings/", include("apps.ai.urls")),
    path("ai-tasks/", include("apps.ai.urls_tasks")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
]

# Serve uploaded asset images via Django's static helper in development.
# In production (gunicorn + nginx) media should be served by a reverse proxy
# pointed at MEDIA_ROOT — Django itself shouldn't be in the file path.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
