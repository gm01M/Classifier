"""Classifier model wrapper.

Runs face/person attribute analysis (age + gender) plus an NSFW safety gate.
Uses Hugging Face ``transformers`` pipelines on GPU when available. If
``CLASSIFIER_STUB=1`` (or torch/transformers are unavailable) it falls back to a
deterministic stub so the whole platform still runs without a GPU or model
downloads — useful for CI and laptops. The HTTP contract is identical either way.
"""

from __future__ import annotations

import hashlib
import io
import logging

from PIL import Image

from .config import settings

logger = logging.getLogger("classifier.model")


class SafetyBlocked(Exception):
    """Raised when an image exceeds the NSFW threshold (mapped to HTTP 422)."""

    def __init__(self, score: float):
        self.score = score
        super().__init__(f"Image blocked by NSFW screening (score={score:.3f}).")


class Classifier:
    """Lazy-loading classifier. Construct once at startup and call ``predict``."""

    def __init__(self) -> None:
        self._loaded = False
        self.device_label = "stub"
        self.model_label = "stub-v1"
        self._age = self._gender = self._nsfw = None

    # -- lifecycle ------------------------------------------------------------
    def load(self) -> None:
        if self._loaded:
            return
        if settings.stub or settings.device == "stub":
            logger.info("Classifier running in STUB mode.")
            self._loaded = True
            return
        try:
            self._load_real()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load ML models; falling back to STUB mode.")
            self.device_label = "stub"
            self.model_label = "stub-v1"
        self._loaded = True

    def _load_real(self) -> None:
        import torch  # local import keeps stub mode dependency-free
        from transformers import pipeline

        use_cuda = (settings.device == "cuda") or (
            settings.device == "auto" and torch.cuda.is_available()
        )
        device = 0 if use_cuda else -1
        self.device_label = "cuda" if use_cuda else "cpu"
        logger.info("Loading models on %s", self.device_label)

        self._age = pipeline("image-classification", model=settings.age_model_id, device=device)
        self._gender = pipeline(
            "image-classification", model=settings.gender_model_id, device=device
        )
        self._nsfw = pipeline("image-classification", model=settings.nsfw_model_id, device=device)
        self.model_label = f"{settings.age_model_id}+{settings.gender_model_id}"

    @property
    def ready(self) -> bool:
        return self._loaded

    # -- inference ------------------------------------------------------------
    def predict(self, image_bytes: bytes) -> dict:
        if not self._loaded:
            self.load()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        if self.device_label == "stub":
            return self._predict_stub(image_bytes)
        return self._predict_real(image)

    def _predict_real(self, image: Image.Image) -> dict:
        nsfw_score = self._nsfw_score(image)
        if nsfw_score >= settings.nsfw_threshold:
            raise SafetyBlocked(nsfw_score)

        age = max(self._age(image), key=lambda r: r["score"])
        gender = max(self._gender(image), key=lambda r: r["score"])
        return {
            "model": self.model_label,
            "device": self.device_label,
            "predictions": [
                {"attribute": "age", "label": str(age["label"]), "score": float(age["score"])},
                {
                    "attribute": "gender",
                    "label": str(gender["label"]),
                    "score": float(gender["score"]),
                },
            ],
            "safety": {"nsfw_score": nsfw_score, "blocked": False},
        }

    def _nsfw_score(self, image: Image.Image) -> float:
        results = {r["label"].lower(): r["score"] for r in self._nsfw(image)}
        return float(results.get("nsfw", 0.0))

    def _predict_stub(self, image_bytes: bytes) -> dict:
        """Deterministic pseudo-prediction derived from the image hash."""
        h = hashlib.sha256(image_bytes).digest()
        age_buckets = ["0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60+"]
        genders = ["male", "female"]
        age = age_buckets[h[0] % len(age_buckets)]
        gender = genders[h[1] % len(genders)]
        return {
            "model": self.model_label,
            "device": "stub",
            "predictions": [
                {"attribute": "age", "label": age, "score": 0.5 + (h[2] % 50) / 100.0},
                {"attribute": "gender", "label": gender, "score": 0.5 + (h[3] % 50) / 100.0},
            ],
            "safety": {"nsfw_score": (h[4] % 10) / 100.0, "blocked": False},
        }


classifier = Classifier()
