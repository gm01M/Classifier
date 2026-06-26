"""REST API for submissions.

  POST /api/submissions            create (multipart photo + metadata)
  GET  /api/submissions            list own submissions
  GET  /api/submissions/{id}       retrieve (owner or admin)
  GET  /api/submissions/{id}/result classification result (polled by HTMX/API)
  GET  /api/admin/submissions      admin-only filter/search
  GET  /api/admin/submissions/{id} admin-only retrieve
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from common.permissions import IsAdminUserRole, IsOwnerOrAdmin, IsVerifiedUser

from .filters import SubmissionFilter
from .models import Submission
from .serializers import SubmissionCreateSerializer, SubmissionSerializer
from .services import ProfileIncomplete, create_submission


class SubmissionViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """User-facing submissions: create + read your own."""

    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_permissions(self):
        # Submitting requires identity verification (same gate as the web /submit/).
        if self.action == "create":
            return [IsAuthenticated(), IsVerifiedUser()]
        return super().get_permissions()

    def get_queryset(self):
        # Users see only their own; admins see all.
        qs = Submission.objects.all().select_related("owner")
        if self.request.user.is_staff:
            return qs
        return qs.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return SubmissionCreateSerializer
        return SubmissionSerializer

    def get_throttles(self):
        if self.action == "create":
            self.throttle_scope = "upload"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    @extend_schema(request=SubmissionCreateSerializer, responses=SubmissionSerializer)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            submission = create_submission(
                owner=request.user,
                raw_photo=serializer._raw_photo,
                declared_type=serializer._declared_type,
            )
        except ProfileIncomplete as exc:
            return Response({"detail": str(exc)}, status=400)
        out = SubmissionSerializer(submission, context=self.get_serializer_context())
        return Response(out.data, status=201)

    @extend_schema(responses=SubmissionSerializer)
    @action(detail=True, methods=["get"])
    def result(self, request, pk=None):
        """Return just the lifecycle status + classification result."""
        submission = self.get_object()
        return Response(
            {
                "id": str(submission.id),
                "status": submission.status,
                "classification_result": submission.classification_result,
                "consistency": submission.consistency,
                "verification": submission.verification,
                "error_detail": submission.error_detail,
            }
        )


class AdminSubmissionViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Admin-only: list/filter/search all submissions and retrieve details."""

    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated, IsAdminUserRole]
    filterset_class = SubmissionFilter
    queryset = Submission.objects.all().select_related("owner")
