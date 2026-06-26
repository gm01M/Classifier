"""HTMX user views: list own submissions, create, detail, and poll for result."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from common.storage import presigned_get_url

from .forms import SubmissionForm
from .models import Status, Submission
from .services import ProfileIncomplete, create_submission


@method_decorator(login_required, name="dispatch")
class SubmissionListView(View):
    template_name = "submissions/list.html"

    def get(self, request):
        submissions = Submission.objects.filter(owner=request.user)
        return render(request, self.template_name, {"submissions": submissions})


@method_decorator(login_required, name="dispatch")
class SubmissionCreateView(View):
    template_name = "submissions/create.html"

    def get(self, request):
        if not request.user.has_profile:
            messages.info(request, "Complete your profile before submitting a photo.")
            return redirect("accounts:profile")
        ctx = {"form": SubmissionForm(), "profile": request.user}
        return render(request, self.template_name, ctx)

    def post(self, request):
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                submission = create_submission(
                    owner=request.user,
                    raw_photo=form._raw_photo,
                    declared_type=form._declared_type,
                )
            except ProfileIncomplete:
                messages.info(request, "Complete your profile before submitting a photo.")
                return redirect("accounts:profile")
            return redirect("submissions:detail", pk=submission.pk)
        ctx = {"form": form, "profile": request.user}
        return render(request, self.template_name, ctx)


@method_decorator(login_required, name="dispatch")
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


@method_decorator(login_required, name="dispatch")
class SubmissionResultPartial(View):
    """HTMX polling endpoint — returns just the result card partial.

    The detail page polls this every couple of seconds until status leaves
    PENDING, at which point the partial omits the hx-trigger and polling stops.
    """

    template_name = "partials/result_card.html"

    def get(self, request, pk):
        submission = SubmissionDetailView._get(request, pk)
        return render(
            request,
            self.template_name,
            {"submission": submission, "still_pending": submission.status == Status.PENDING},
        )
