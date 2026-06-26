"""Shared pytest fixtures."""

import io

import pytest
from django.contrib.auth import get_user_model
from PIL import Image
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api():
    return APIClient()


PROFILE = {
    "full_name": "Test User",
    "age": 29,
    "place_of_living": "Berlin",
    "gender": "female",
    "country_of_origin": "Germany",
}


@pytest.fixture
def user(db):
    return User.objects.create_user(email="user@example.com", password="testpass123", **PROFILE)


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(email="admin@example.com", password="testpass123")


@pytest.fixture
def png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (120, 180, 90)).save(buf, format="PNG")
    return buf.getvalue()
