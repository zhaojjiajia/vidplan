from django.urls import path

from .views import AISettingTestView, MarkdownImportAnalyzeView, UserAISettingView

urlpatterns = [
    path("", UserAISettingView.as_view(), name="ai-setting"),
    path("test/", AISettingTestView.as_view(), name="ai-setting-test"),
    path("markdown-import/analyze/", MarkdownImportAnalyzeView.as_view(), name="markdown-import-analyze"),
]
