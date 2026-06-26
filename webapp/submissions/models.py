"""Submission model — metadata in Postgres, photo bytes in object storage.

Indexing is tuned for the admin filters (age range, gender, location, country);
see docs/database.md.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from common.choices import AGE_VALIDATORS, Gender

__all__ = ["Consistency", "Gender", "Status", "Submission"]


class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    DONE = "done", "Done"
    FAILED = "failed", "Failed"
    REJECTED = "rejected", "Rejected (safety)"


class Consistency(models.TextChoices):
    """Result of cross-checking the photo prediction against the claimed profile."""

    PENDING = "pending", "Pending"
    CONSISTENT = "consistent", "Consistent"
    INCONSISTENT = "inconsistent", "Inconsistent"
    UNVERIFIED = "unverified", "Unverified"


class Submission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    # User-provided metadata
    name = models.CharField(max_length=150)
    age = models.PositiveSmallIntegerField(validators=AGE_VALIDATORS)
    place_of_living = models.CharField(max_length=120)
    gender = models.CharField(max_length=12, choices=Gender.choices)
    country_of_origin = models.CharField(max_length=80)
    description = models.TextField(blank=True, max_length=2000)

    # Storage reference (object key in the S3/MinIO bucket — never the bytes).
    photo_key = models.CharField(max_length=255)
    photo_content_type = models.CharField(max_length=40, default="image/jpeg")

    # Classification lifecycle
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    classification_result = models.JSONField(null=True, blank=True)
    error_detail = models.CharField(max_length=255, blank=True)

    # Verification: does the photo prediction match the self-reported profile?
    consistency = models.CharField(
        max_length=12, choices=Consistency.choices, default=Consistency.PENDING
    )
    verification = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["age"], name="sub_age_idx"),
            models.Index(fields=["gender"], name="sub_gender_idx"),
            models.Index(fields=["country_of_origin"], name="sub_country_idx"),
            models.Index(fields=["place_of_living"], name="sub_place_idx"),
            models.Index(fields=["created_at"], name="sub_created_idx"),
            models.Index(fields=["status"], name="sub_status_idx"),
            models.Index(fields=["consistency"], name="sub_consistency_idx"),
            # Composite index for the common admin filter combination.
            models.Index(
                fields=["gender", "country_of_origin", "age"],
                name="sub_gender_country_age_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"
