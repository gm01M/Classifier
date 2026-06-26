"""HTMX platform views: gated home/dashboard, verification history, detail."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from common.image_safety import ImageValidationError
from common.storage import presigned_get_url

from .gating import verified_required
from .models import Status, Submission
from .services import ProfileIncomplete, create_submission


@method_decorator(login_required, name="dispatch")
class PlatformHomeView(View):
    """Landing page. Verified users see the platform; everyone else is routed
    into the verification flow (or the lock page)."""

    template_name = "submissions/home.html"

    def get(self, request):
        user = request.user
        if not user.is_staff and not user.is_verified:
            if not user.has_profile:
                return redirect("accounts:profile")
            if user.is_verification_locked:
                return redirect("verify:locked")
            return redirect("verify:start")
        latest = Submission.objects.filter(owner=user).first()
        return render(request, self.template_name, {"latest": latest})


@method_decorator(verified_required, name="dispatch")
class SubmitView(View):
    """New submission (resubmit) for a verified user — camera or upload."""

    template_name = "submissions/submit.html"

    def get(self, request):
        return render(request, self.template_name)


@method_decorator(verified_required, name="dispatch")
class SubmitCaptureView(View):
    """Accept a captured/uploaded photo and create a classified submission."""

    def post(self, request):
        photo = request.FILES.get("photo")
        if not photo:
            return JsonResponse({"error": "No image provided."}, status=400)
        try:
            submission = create_submission(
                owner=request.user,
                raw_photo=photo.read(),
                declared_type=getattr(photo, "content_type", "image/jpeg"),
            )
        except ProfileIncomplete:
            return JsonResponse({"redirect": reverse("accounts:profile")}, status=400)
        except ImageValidationError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse(
            {
                "id": str(submission.id),
                "redirect": reverse("submissions:detail", args=[submission.id]),
            }
        )


@method_decorator(verified_required, name="dispatch")
class SubmissionListView(View):
    """Verification + submission history for the current user."""

    template_name = "submissions/list.html"

    def get(self, request):
        submissions = Submission.objects.filter(owner=request.user)
        return render(request, self.template_name, {"submissions": submissions})


@method_decorator(verified_required, name="dispatch")
class SubmissionDetailView(View):
    template_name = "submissions/detail.html"

    def get(self, request, pk):
        submission = self._get(request, pk)
        return render(
            request,
            self.template_name,
            {"submission": submission, "photo_url": presigned_get_url(submission.photo_key)},
        )

    @staticmethod
    def _get(request, pk) -> Submission:
        qs = (
            Submission.objects.all()
            if request.user.is_staff
            else Submission.objects.filter(owner=request.user)
        )
        return get_object_or_404(qs, pk=pk)


@method_decorator(verified_required, name="dispatch")
class SubmissionResultPartial(View):
    """HTMX polling endpoint for a submission's classification result."""

    template_name = "partials/result_card.html"

    def get(self, request, pk):
        submission = SubmissionDetailView._get(request, pk)
        return render(
            request,
            self.template_name,
            {"submission": submission, "still_pending": submission.status == Status.PENDING},
        )
