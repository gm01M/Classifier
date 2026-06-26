"""HTMX admin panel: filter/search submissions and view full details.

Access is restricted to staff/admin users (RBAC, safety rule #5). The list view
returns either the full page or, for HTMX requests, just the results-table
partial so filtering feels live without a full reload.
"""

from __future__ import annotations

from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View

from common.storage import presigned_get_url

from .filters import SubmissionFilter
from .models import Consistency, Gender, Status, Submission

staff_required = user_passes_test(lambda u: u.is_authenticated and u.is_staff)


@method_decorator(staff_required, name="dispatch")
class AdminSubmissionListView(View):
    template_name = "admin_panel/list.html"
    partial_name = "partials/admin_table.html"

    def get(self, request):
        f = SubmissionFilter(
            request.GET,
            queryset=Submission.objects.all().select_related("owner"),
        )
        paginator = Paginator(f.qs, 20)
        page = paginator.get_page(request.GET.get("page"))

        context = {
            "page": page,
            "filter_data": request.GET,
            "genders": Gender.choices,
            "statuses": Status.choices,
            "consistencies": Consistency.choices,
        }
        # HTMX requests get just the table partial for live filtering.
        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


@method_decorator(staff_required, name="dispatch")
class AdminSubmissionDetailView(View):
    template_name = "admin_panel/detail.html"

    def get(self, request, pk):
        submission = get_object_or_404(Submission.objects.select_related("owner"), pk=pk)
        return render(
            request,
            self.template_name,
            {"submission": submission, "photo_url": presigned_get_url(submission.photo_key)},
        )
