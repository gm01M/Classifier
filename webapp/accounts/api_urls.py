"""Auth API routes mounted under /api/auth/ and /api/users/."""

from django.urls import path

from .api_views import (
    MeView,
    RegisterView,
    ThrottledTokenObtainPairView,
    ThrottledTokenRefreshView,
)

urlpatterns = [
    path("register", RegisterView.as_view(), name="api-register"),
    path("login", ThrottledTokenObtainPairView.as_view(), name="api-login"),
    path("refresh", ThrottledTokenRefreshView.as_view(), name="api-refresh"),
    # Mounted at /api/auth/me for grouping; documented alias of /api/users/me.
    path("me", MeView.as_view(), name="api-me"),
]
