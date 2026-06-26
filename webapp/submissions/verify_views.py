"""Live camera identity-verification flow.

  GET  /verify/                 camera page (capture a face)
  POST /verify/capture/         accept a captured frame -> create + classify
  GET  /verify/<id>/            result page (polls status)
  GET  /verify/<id>/status/     HTMX status partial (verifying -> success/failed/locked)
  GET  /verify/locked/          locked-out page (retry limit exhausted)

The capture is classified and cross-checked against the user's claimed profile
(see verification.py). A consistent result marks the user verified; an
inconsistent one burns a retry; after MAX_VERIFICATION_ATTEMPTS the user is
locked pending admin review.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from common.image_safety import ImageValidationError

from .models import Consistency, Status, Submission
from .services import ProfileIncomplete, create_submission


@method_decorator(login_required, name="dispatch")
class VerifyStartView(View):
    """Camera page. Bounces verified users to the platform, locked users to lock."""

    template_name = "verify/start.html"

    def get(self, request):
        user = request.user
        if user.is_verified:
            return redirect("submissions:home")
        if not user.has_profile:
            return redirect("accounts:profile")
        if user.is_verification_locked:
            return redirect("verify:locked")
        return render(request, self.template_name, {"attempts_remaining": user.attempts_remaining})


@method_decorator(login_required, name="dispatch")
class VerifyCaptureView(View):
    """Receive a captured camera frame (multipart 'photo') and start verification."""

    def post(self, request):
        user = request.user
        if user.is_verified:
            return JsonResponse({"redirect": reverse("submissions:home")})
        if user.is_verification_locked:
            return JsonResponse({"redirect": reverse("verify:locked")})

        photo = request.FILES.get("photo")
        if not photo:
            return JsonResponse({"error": "No image captured."}, status=400)

        raw = photo.read()
        try:
            submission = create_submission(
                owner=user,
                raw_photo=raw,
                declared_type=getattr(photo, "content_type", "image/jpeg"),
            )
        except ProfileIncomplete:
            return JsonResponse({"redirect": reverse("accounts:profile")}, status=400)
        except ImageValidationError as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        return JsonResponse(
            {"id": str(submission.id), "redirect": reverse("verify:result", args=[submission.id])}
        )


@method_decorator(login_required, name="dispatch")
class VerifyResultView(View):
    """Page that polls the verification status partial until it resolves."""

    template_name = "verify/result.html"

    def get(self, request, pk):
        submission = get_object_or_404(Submission, pk=pk, owner=request.user)
        return render(request, self.template_name, {"submission": submission})


@method_decorator(login_required, name="dispatch")
class VerifyStatusPartial(View):
    """HTMX partial: verifying -> success / failed / locked."""

    template_name = "partials/verify_status.html"

    def get(self, request, pk):
        submission = get_object_or_404(Submission, pk=pk, owner=request.user)
        user = request.user
        ctx = {
            "submission": submission,
            "pending": submission.status == Status.PENDING,
            "verified": submission.consistency == Consistency.CONSISTENT,
            "rejected": submission.status == Status.REJECTED,
            "failed_tech": submission.status == Status.FAILED,
            "inconsistent": submission.consistency == Consistency.INCONSISTENT,
            "locked": user.is_verification_locked,
            "attempts_remaining": user.attempts_remaining,
        }
        return render(request, self.template_name, ctx)


@method_decorator(login_required, name="dispatch")
class VerifyLockedView(View):
    template_name = "verify/locked.html"

    def get(self, request):
        if request.user.is_verified:
            return redirect("submissions:home")
        return render(request, self.template_name)
