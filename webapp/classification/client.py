"""HTTP client for the classifier microservice.

The webapp/worker never imports ML libraries — it just calls the classifier's
stable ``POST /v1/classify`` contract. This keeps the web image small and lets
the GPU service scale independently.
"""

from __future__ import annotations

import requests
from django.conf import settings


class ClassifierError(Exception):
    """Raised when the classifier service errors or is unreachable."""


class SafetyRejection(Exception):
    """Raised when the classifier rejects an image on safety grounds (NSFW)."""


def classify_image(image_bytes: bytes, content_type: str = "image/jpeg") -> dict:
    """Send an image to the classifier and return its structured result.

    Raises:
        SafetyRejection: classifier returned 422 (content blocked).
        ClassifierError: any other failure (network, 5xx, timeout).
    """
    url = f"{settings.CLASSIFIER_URL.rstrip('/')}/v1/classify"
    try:
        resp = requests.post(
            url,
            files={"file": ("upload.jpg", image_bytes, content_type)},
            timeout=settings.CLASSIFIER_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ClassifierError(f"Classifier unreachable: {exc}") from exc

    if resp.status_code == 422:
        detail = _safe_detail(resp)
        raise SafetyRejection(detail)
    if resp.status_code >= 400:
        raise ClassifierError(f"Classifier returned {resp.status_code}: {_safe_detail(resp)}")
    return resp.json()


def _safe_detail(resp: requests.Response) -> str:
    try:
        return str(resp.json().get("detail", resp.text))[:200]
    except ValueError:
        return resp.text[:200]
