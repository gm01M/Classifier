"""End-to-end submission creation test with storage + classifier mocked.

Celery runs eagerly in test settings, so creating a submission also exercises the
classify task synchronously — we stub object storage and the classifier client.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from submissions.models import Status, Submission

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _stub_io(monkeypatch, png_bytes):
    # Storage: pretend uploads/downloads succeed.
    monkeypatch.setattr("submissions.services.put_object", lambda *a, **k: None)
    monkeypatch.setattr("submissions.tasks.get_object_bytes", lambda key: png_bytes)
    monkeypatch.setattr(
        "submissions.serializers.presigned_get_url", lambda key: "http://x/presigned", raising=False
    )
    # Classifier: deterministic result.
    monkeypatch.setattr(
        "submissions.tasks.classify_image",
        lambda b, ct="image/jpeg": {
            "model": "stub",
            "device": "cpu",
            "predictions": [{"attribute": "age", "label": "20-29", "score": 0.9}],
        },
    )


def test_create_submission_snapshots_profile_and_classifies(api, user, png_bytes):
    api.force_authenticate(user=user)
    photo = SimpleUploadedFile("p.png", png_bytes, content_type="image/png")
    # Photo-only submission: metadata comes from the user's onboarding profile.
    resp = api.post("/api/submissions", {"photo": photo}, format="multipart")
    assert resp.status_code == 201, resp.data
    sub = Submission.objects.get()
    # Snapshotted from the user fixture profile.
    assert sub.name == "Test User"
    assert sub.gender == "female"
    assert sub.country_of_origin == "Germany"
    assert sub.status == Status.DONE
    assert sub.classification_result["predictions"][0]["label"] == "20-29"


def test_submission_requires_completed_profile(api, admin, png_bytes):
    # The admin fixture has no onboarding profile -> submission is rejected.
    api.force_authenticate(user=admin)
    photo = SimpleUploadedFile("p.png", png_bytes, content_type="image/png")
    resp = api.post("/api/submissions", {"photo": photo}, format="multipart")
    assert resp.status_code == 400
    assert Submission.objects.count() == 0


def test_user_cannot_see_others_submission(api, user, admin, png_bytes):
    other = Submission.objects.create(
        owner=admin,
        name="Bob",
        age=40,
        place_of_living="Paris",
        gender="male",
        country_of_origin="France",
        photo_key="k",
    )
    api.force_authenticate(user=user)
    resp = api.get(f"/api/submissions/{other.id}")
    assert resp.status_code == 404


def test_admin_filter_by_gender(api, admin):
    Submission.objects.create(
        owner=admin,
        name="A",
        age=30,
        place_of_living="X",
        gender="female",
        country_of_origin="DE",
        photo_key="k1",
    )
    Submission.objects.create(
        owner=admin,
        name="B",
        age=31,
        place_of_living="Y",
        gender="male",
        country_of_origin="FR",
        photo_key="k2",
    )
    api.force_authenticate(user=admin)
    resp = api.get("/api/admin/submissions?gender=female")
    assert resp.status_code == 200
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["name"] == "A"
