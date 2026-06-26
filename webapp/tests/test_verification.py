"""Tests for the photo-vs-profile verification logic and the access gate."""

import sys

import pytest

from submissions.models import Consistency
from submissions.verification import evaluate, parse_age_bucket

# Django 5.1's test client copies template context after render; on Python 3.14
# that copy raises (Context.__copy__ / super() change). The app targets 3.12
# (Docker + CI), where this is fine. Skip the template-rendering assertion on 3.14.
_PY314_TEMPLATE_BUG = sys.version_info >= (3, 14)


def _result(age=None, gender=None):
    preds = []
    if age is not None:
        preds.append({"attribute": "age", "label": age, "score": 0.9})
    if gender is not None:
        preds.append({"attribute": "gender", "label": gender, "score": 0.9})
    return {"predictions": preds}


def test_parse_age_bucket():
    assert parse_age_bucket("20-29") == (20, 29)
    assert parse_age_bucket("0-2") == (0, 2)
    assert parse_age_bucket("more than 70") == (70, 120)
    assert parse_age_bucket("60+") == (60, 120)
    assert parse_age_bucket("") is None


def test_consistent_when_age_and_gender_match():
    status, details = evaluate(
        claimed_age=29, claimed_gender="female", result=_result("20-29", "female")
    )
    assert status == Consistency.CONSISTENT
    assert details["age_match"] is True
    assert details["gender_match"] is True


def test_inconsistent_on_age_mismatch():
    # Claimed 19 vs photo 30-39 (tolerance 8 -> [22,47]) -> mismatch.
    status, details = evaluate(
        claimed_age=19, claimed_gender="male", result=_result("30-39", "male")
    )
    assert status == Consistency.INCONSISTENT
    assert details["age_match"] is False
    assert details["reasons"]


def test_inconsistent_on_gender_mismatch():
    status, _ = evaluate(claimed_age=25, claimed_gender="female", result=_result("20-29", "male"))
    assert status == Consistency.INCONSISTENT


def test_unverified_when_no_predictions():
    status, _ = evaluate(claimed_age=25, claimed_gender="female", result=_result())
    assert status == Consistency.UNVERIFIED


def test_age_tolerance_allows_near_miss():
    # Claimed 31 vs photo 20-29 -> within +8 tolerance -> consistent.
    status, _ = evaluate(claimed_age=31, claimed_gender="male", result=_result("20-29", "male"))
    assert status == Consistency.CONSISTENT


# ---- Access gate ---------------------------------------------------------
pytestmark_db = pytest.mark.django_db


@pytest.mark.django_db
def test_unverified_user_redirected_to_verify(client, user):
    client.force_login(user)
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/verify/" in resp["Location"]


@pytest.mark.django_db
@pytest.mark.skipif(_PY314_TEMPLATE_BUG, reason="Django5.1 test-client context copy bug on py3.14")
def test_verified_user_sees_platform(client, user):
    user.is_verified = True
    user.save()
    client.force_login(user)
    resp = client.get("/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_locked_user_redirected_to_locked(client, user, settings):
    user.verification_attempts = settings.MAX_VERIFICATION_ATTEMPTS
    user.save()
    client.force_login(user)
    resp = client.get("/verify/", follow=False)
    assert resp.status_code == 302
    assert resp["Location"].endswith("/verify/locked/")
