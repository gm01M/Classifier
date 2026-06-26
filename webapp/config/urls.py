"""Root URL configuration.

Layout:
  /                      -> HTMX UI (submissions home)
  /accounts/...          -> HTMX auth pages (register/login/logout)
  /admin-panel/...       -> HTMX admin panel (staff only)
  /api/...               -> REST API (DRF) + JWT
  /api/docs/             -> Swagger UI (drf-spectacular)
  /api/schema/           -> raw OpenAPI schema
  /healthz, /readyz      -> liveness/readiness probes
  /metrics               -> Prometheus metrics (django-prometheus)
  /django-admin/         -> Django's built-in admin
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from common.views import healthz, readyz

urlpatterns = [
    # Health / observability
    path("healthz", healthz, name="healthz"),
    path("readyz", readyz, name="readyz"),
    path("", include("django_prometheus.urls")),  # /metrics
    # API
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/auth/", include("accounts.api_urls")),
    path("api/", include("submissions.api_urls")),
    # HTMX UI
    path("accounts/", include("accounts.urls")),
    path("admin-panel/", include("submissions.admin_urls")),
    path("", include("submissions.urls")),
    # Django admin
    path("django-admin/", admin.site.urls),
]
