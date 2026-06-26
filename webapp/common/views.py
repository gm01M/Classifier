"""Liveness/readiness probes used by docker-compose healthchecks and K8s."""

from django.db import connection
from django.http import JsonResponse


def healthz(request):
    """Liveness — process is up. Cheap, no dependencies."""
    return JsonResponse({"status": "ok"})


def readyz(request):
    """Readiness — can we serve traffic? Checks the database connection."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"status": "unready", "error": str(exc)}, status=503)
    return JsonResponse({"status": "ready"})
