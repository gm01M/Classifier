"""API routes for submissions, mounted under /api/."""

from rest_framework.routers import DefaultRouter

from .api_views import AdminSubmissionViewSet, SubmissionViewSet

router = DefaultRouter(trailing_slash=False)
router.register("submissions", SubmissionViewSet, basename="submission")
router.register("admin/submissions", AdminSubmissionViewSet, basename="admin-submission")

urlpatterns = router.urls
