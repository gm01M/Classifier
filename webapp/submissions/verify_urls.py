"""Camera verification routes mounted at /verify/."""

from django.urls import path

from .verify_views import (
    VerifyCaptureView,
    VerifyLockedView,
    VerifyResultView,
    VerifyStartView,
    VerifyStatusPartial,
)

app_name = "verify"

urlpatterns = [
    path("", VerifyStartView.as_view(), name="start"),
    path("capture/", VerifyCaptureView.as_view(), name="capture"),
    path("locked/", VerifyLockedView.as_view(), name="locked"),
    path("<uuid:pk>/", VerifyResultView.as_view(), name="result"),
    path("<uuid:pk>/status/", VerifyStatusPartial.as_view(), name="status"),
]
