"""Classifier API tests — run against the deterministic stub (no GPU/model)."""

import io
import os

os.environ.setdefault("CLASSIFIER_STUB", "1")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # triggers lifespan -> model load
        yield c


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (24, 24), (40, 90, 160)).save(buf, format="PNG")
    return buf.getvalue()


def test_healthz(client):
    assert client.get("/healthz").json()["status"] == "ok"


def test_readyz(client):
    body = client.get("/readyz").json()
    assert body["status"] == "ready"
    assert body["model_loaded"] is True


def test_classify_returns_predictions(client):
    resp = client.post("/v1/classify", files={"file": ("p.png", _png(), "image/png")})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["device"] == "stub"
    attrs = {p["attribute"] for p in body["predictions"]}
    assert attrs == {"age", "gender"}
    assert body["safety"]["blocked"] is False


def test_classify_is_deterministic(client):
    img = _png()
    a = client.post("/v1/classify", files={"file": ("p.png", img, "image/png")}).json()
    b = client.post("/v1/classify", files={"file": ("p.png", img, "image/png")}).json()
    assert a["predictions"] == b["predictions"]


def test_empty_file_rejected(client):
    resp = client.post("/v1/classify", files={"file": ("p.png", b"", "image/png")})
    assert resp.status_code == 400
