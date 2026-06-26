"""Classifier configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(int(default))).lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # device: "auto" -> cuda when available else cpu; or force "cuda"/"cpu".
    device: str = os.environ.get("MODEL_DEVICE", "auto")
    # Force the deterministic stub (no model download / no GPU needed).
    stub: bool = _bool("CLASSIFIER_STUB", False)

    age_model_id: str = os.environ.get("AGE_MODEL_ID", "nateraw/vit-age-classifier")
    gender_model_id: str = os.environ.get("GENDER_MODEL_ID", "rizvandwiki/gender-classification")
    nsfw_model_id: str = os.environ.get("NSFW_MODEL_ID", "Falconsai/nsfw_image_detection")
    nsfw_threshold: float = float(os.environ.get("NSFW_THRESHOLD", "0.85"))

    max_upload_bytes: int = int(os.environ.get("MAX_UPLOAD_BYTES", str(8 * 1024 * 1024)))


settings = Settings()
