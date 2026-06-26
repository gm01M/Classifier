"""Tests for registration + JWT auth + RBAC on admin endpoints."""

import pytest

pytestmark = pytest.mark.django_db


PROFILE = {
    "full_name": "New",
    "age": 31,
    "place_of_living": "Oslo",
    "gender": "male",
    "country_of_origin": "Norway",
}


def test_register_creates_user_with_profile(api):
    resp = api.post(
        "/api/auth/register",
        {"email": "new@example.com", "password": "s3curepass!", **PROFILE},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["email"] == "new@example.com"
    assert resp.data["age"] == 31
    assert resp.data["country_of_origin"] == "Norway"
    assert "password" not in resp.data


def test_register_requires_profile_fields(api):
    # Missing age/gender/etc. should fail — onboarding collects the full profile.
    resp = api.post(
        "/api/auth/register",
        {"email": "partial@example.com", "password": "s3curepass!", "full_name": "P"},
        format="json",
    )
    assert resp.status_code == 400
    assert "age" in resp.data


def test_register_rejects_weak_password(api):
    resp = api.post(
        "/api/auth/register",
        {"email": "weak@example.com", "password": "123", **PROFILE},
        format="json",
    )
    assert resp.status_code == 400


def test_update_profile(api, user):
    api.force_authenticate(user=user)
    resp = api.patch("/api/auth/me", {"country_of_origin": "France"}, format="json")
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.country_of_origin == "France"


def test_jwt_login_and_me(api, user):
    resp = api.post(
        "/api/auth/login",
        {"email": "user@example.com", "password": "testpass123"},
        format="json",
    )
    assert resp.status_code == 200
    token = resp.data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    me = api.get("/api/auth/me")
    assert me.status_code == 200
    assert me.data["email"] == "user@example.com"
    assert me.data["is_admin"] is False


def test_admin_endpoint_forbidden_for_regular_user(api, user):
    api.force_authenticate(user=user)
    resp = api.get("/api/admin/submissions")
    assert resp.status_code == 403


def test_admin_endpoint_allowed_for_admin(api, admin):
    api.force_authenticate(user=admin)
    resp = api.get("/api/admin/submissions")
    assert resp.status_code == 200
