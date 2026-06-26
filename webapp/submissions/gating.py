"""Verification gate: only verified (or staff) users may access the platform."""

from functools import wraps

from django.shortcuts import redirect


def verified_required(view_func):
    """Redirect unverified users to the camera verification flow (or lock page)."""

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect("accounts:login")
        if user.is_staff or user.is_verified:
            return view_func(request, *args, **kwargs)
        if not user.has_profile:
            return redirect("accounts:profile")
        if user.is_verification_locked:
            return redirect("verify:locked")
        return redirect("verify:start")

    return wrapped
