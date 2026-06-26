"""HTMX user-facing routes mounted at /."""

from django.urls import path

from .views import (
    SubmissionCreateView,
    SubmissionDetailView,
    SubmissionListView,
    SubmissionResultPartial,
)

app_name = "submissions"

urlpatterns = [
    path("", SubmissionListView.as_view(), name="list"),
    path("submit/", SubmissionCreateView.as_view(), name="create"),
    path("s/<uuid:pk>/", SubmissionDetailView.as_view(), name="detail"),
    path("s/<uuid:pk>/result/", SubmissionResultPartial.as_view(), name="result-partial"),
]
