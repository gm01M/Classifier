"""HTMX admin panel routes mounted at /admin-panel/."""

from django.urls import path

from .admin_views import AdminSubmissionDetailView, AdminSubmissionListView

app_name = "admin_panel"

urlpatterns = [
    path("", AdminSubmissionListView.as_view(), name="list"),
    path("s/<uuid:pk>/", AdminSubmissionDetailView.as_view(), name="detail"),
]
