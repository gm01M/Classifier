"""Submission creation logic shared by the REST API and the HTMX views.

A submission is now photo-only: it snapshots the uploader's onboarding profile
(name, age, place, gender, country, description) onto the submission record, then
validates + sanitises the photo (safety rules #1/#2), stores it in object
storage, and enqueues async classification.
"""

from __future__ import annotations

import uuid

from common.image_safety import validate_and_sanitize
from common.storage import put_object

from .models import Submission
from .tasks import classify_submission


class ProfileIncomplete(Exception):
    """Raised when a user without a completed onboarding profile tries to submit."""


def _snapshot_profile(owner) -> dict:
    return {
        "name": owner.full_name,
        "age": owner.age,
        "place_of_living": owner.place_of_living,
        "gender": owner.gender,
        "country_of_origin": owner.country_of_origin,
        "description": owner.description,
    }


def create_submission(*, owner, raw_photo: bytes, declared_type: str) -> Submission:
    """Create a Submission for ``owner`` from a raw uploaded photo.

    Metadata is snapshotted from the owner's profile. Raises ``ProfileIncomplete``
    if the profile hasn't been filled in, or ``ImageValidationError`` if the photo
    fails a safety check.
    """
    if not owner.has_profile:
        raise ProfileIncomplete("Complete your profile before submitting a photo.")

    clean_bytes, content_type = validate_and_sanitize(raw_photo, declared_type)

    key = f"submissions/{owner.id}/{uuid.uuid4().hex}.jpg"
    put_object(key, clean_bytes, content_type)

    submission = Submission.objects.create(
        owner=owner,
        photo_key=key,
        photo_content_type=content_type,
        **_snapshot_profile(owner),
    )

    # Fire-and-forget: classification runs in the worker.
    classify_submission.delay(str(submission.id))
    return submission
