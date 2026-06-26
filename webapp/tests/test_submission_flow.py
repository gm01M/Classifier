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


def test_first_verification_via_capture_marks_user_verified(client, user, png_bytes):
    # The onboarding camera/upload capture is NOT gated on is_verified (it's how
    # you become verified). It snapshots the profile, classifies, and verifies.
    assert user.is_verified is False
    client.force_login(user)
    photo = SimpleUploadedFile("capture.jpg", png_bytes, content_type="image/jpeg")
    resp = client.post("/verify/capture/", {"photo": photo})
    assert resp.status_code == 200
    sub = Submission.objects.get(owner=user)
    # Snapshotted from the user fixture profile.
    assert sub.name == "Test User"
    assert sub.gender == "female"
    assert sub.country_of_origin == "Germany"
    assert sub.status == Status.DONE
    assert sub.classification_result["predictions"][0]["label"] == "20-29"
    # Predicted 20-29 vs claimed age 29 -> consistent -> user becomes verified.
    assert sub.consistency == "consistent"
    user.refresh_from_db()
    assert user.is_verified is True


def test_unverified_user_cannot_submit_via_api(api, user, png_bytes):
    # The API enforces the same verification gate as the web platform.
    api.force_authenticate(user=user)  # user fixture is unverified
    photo = SimpleUploadedFile("p.jpg", png_bytes, content_type="image/jpeg")
    resp = api.post("/api/submissions", {"photo": photo}, format="multipart")
    assert resp.status_code == 403
    assert Submission.objects.count() == 0


def test_verified_user_can_submit_via_api(api, user, png_bytes):
    user.is_verified = True
    user.save()
    api.force_authenticate(user=user)
    photo = SimpleUploadedFile("p.jpg", png_bytes, content_type="image/jpeg")
    resp = api.post("/api/submissions", {"photo": photo}, format="multipart")
    assert resp.status_code == 201, resp.data


def test_submission_requires_completed_profile(api, admin, png_bytes):
    # The admin fixture has no onboarding profile -> submission is rejected.
    api.force_authenticate(user=admin)
    photo = SimpleUploadedFile("p.png", png_bytes, content_type="image/png")
    resp = api.post("/api/submissions", {"photo": photo}, format="multipart")
    assert resp.status_code == 400
    assert Submission.objects.count() == 0


def test_verified_user_can_resubmit_via_capture(client, user, png_bytes):
    # A verified user can submit again (camera/upload) and gets a classified result.
    user.is_verified = True
    user.save()
    client.force_login(user)
    photo = SimpleUploadedFile("capture.jpg", png_bytes, content_type="image/jpeg")
    resp = client.post("/submit/capture/", {"photo": photo})
    assert resp.status_code == 200
    data = resp.json()
    assert "redirect" in data and "/s/" in data["redirect"]
    sub = Submission.objects.get(owner=user)
    assert sub.status == Status.DONE
    assert sub.classification_result is not None


def test_inconsistent_resubmission_revokes_verification(client, user, png_bytes, monkeypatch):
    # "Count the last one": a verified user whose latest capture is inconsistent
    # loses verification and is sent back through the gate.
    monkeypatch.setattr(
        "submissions.tasks.classify_image",
        lambda b, ct="image/jpeg": {
            "model": "stub",
            "device": "cpu",
            # user fixture is female/29 -> these mismatch -> inconsistent.
            "predictions": [
                {"attribute": "age", "label": "0-9", "score": 0.9},
                {"attribute": "gender", "label": "male", "score": 0.9},
            ],
        },
    )
    user.is_verified = True
    user.save()
    client.force_login(user)
    photo = SimpleUploadedFile("c.jpg", png_bytes, content_type="image/jpeg")
    resp = client.post("/submit/capture/", {"photo": photo})
    assert resp.status_code == 200
    sub = Submission.objects.get(owner=user)
    assert sub.consistency == "inconsistent"
    user.refresh_from_db()
    assert user.is_verified is False
    assert user.verification_attempts == 1


def test_unverified_user_blocked_from_submit_page(client, user):
    # Unverified users are gated out of the resubmit page into verification.
    client.force_login(user)
    resp = client.get("/submit/")
    assert resp.status_code == 302
    assert "/verify/" in resp["Location"]


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
