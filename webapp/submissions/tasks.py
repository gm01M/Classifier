"""Celery task that runs classification asynchronously.

Flow: webapp stores the submission as PENDING and enqueues ``classify_submission``.
The worker downloads the photo from object storage, calls the classifier service,
and writes the result (or a failure/rejection status) back to Postgres. The HTMX
UI polls the submission's result endpoint until status leaves PENDING.
"""

from __future__ import annotations

import logging

from celery import shared_task

from classification.client import ClassifierError, SafetyRejection, classify_image
from common.storage import get_object_bytes

from .models import Consistency, Status, Submission
from .verification import evaluate

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(ClassifierError,),
    retry_backoff=True,
)
def classify_submission(self, submission_id: str) -> str:
    submission = Submission.objects.filter(pk=submission_id).first()
    if submission is None:
        logger.warning("classify_submission: submission %s vanished", submission_id)
        return "missing"

    try:
        image_bytes = get_object_bytes(submission.photo_key)
        result = classify_image(image_bytes, submission.photo_content_type)
    except SafetyRejection as exc:
        submission.status = Status.REJECTED
        submission.error_detail = str(exc)[:255]
        submission.classification_result = None
        submission.save(update_fields=["status", "error_detail", "classification_result"])
        logger.info("submission %s rejected on safety grounds", submission_id)
        return "rejected"
    except ClassifierError:
        # autoretry_for will re-raise; on final failure mark FAILED.
        if self.request.retries >= self.max_retries:
            submission.status = Status.FAILED
            submission.error_detail = "Classifier unavailable after retries."
            submission.save(update_fields=["status", "error_detail"])
            return "failed"
        raise

    # Verify the prediction against the self-reported profile snapshot.
    consistency, details = evaluate(
        claimed_age=submission.age,
        claimed_gender=submission.gender,
        result=result,
    )

    submission.status = Status.DONE
    submission.classification_result = result
    submission.consistency = consistency
    submission.verification = details
    submission.error_detail = ""
    submission.save(
        update_fields=[
            "status",
            "classification_result",
            "consistency",
            "verification",
            "error_detail",
        ]
    )

    _update_user_verification(submission.owner, consistency)
    return "done"


def _update_user_verification(user, consistency: str) -> None:
    """Update the verification gate from the latest finished submission.

    The most recent result governs ("count the last one"):
      * CONSISTENT   -> verified, and the consecutive-failure counter resets.
      * INCONSISTENT -> verification revoked, and a strike is recorded; after
                        MAX_VERIFICATION_ATTEMPTS consecutive strikes the user is
                        locked (see User.is_verification_locked).
      * UNVERIFIED/REJECTED/FAILED -> no change (couldn't determine a match).
    """
    fields: list[str] = []
    if consistency == Consistency.CONSISTENT:
        if not user.is_verified:
            user.is_verified = True
            fields.append("is_verified")
        if user.verification_attempts:
            user.verification_attempts = 0
            fields.append("verification_attempts")
    elif consistency == Consistency.INCONSISTENT:
        if user.is_verified:
            user.is_verified = False
            fields.append("is_verified")
        user.verification_attempts = (user.verification_attempts or 0) + 1
        fields.append("verification_attempts")
    if fields:
        user.save(update_fields=fields)
