"""Platform routes mounted at /."""

from django.urls import path

from .views import (
    PlatformHomeView,
    SubmissionDetailView,
    SubmissionListView,
    SubmissionResultPartial,
    SubmitCaptureView,
    SubmitView,
)

app_name = "submissions"

urlpatterns = [
    path("", PlatformHomeView.as_view(), name="home"),
    path("submit/", SubmitView.as_view(), name="submit"),
    path("submit/capture/", SubmitCaptureView.as_view(), name="submit-capture"),
    path("history/", SubmissionListView.as_view(), name="list"),
    path("s/<uuid:pk>/", SubmissionDetailView.as_view(), name="detail"),
    path("s/<uuid:pk>/result/", SubmissionResultPartial.as_view(), name="result-partial"),
]
