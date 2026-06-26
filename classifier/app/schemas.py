"""Response schemas for the classifier API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Prediction(BaseModel):
    attribute: str = Field(..., examples=["age", "gender"])
    label: str = Field(..., examples=["20-29", "female"])
    score: float = Field(..., ge=0.0, le=1.0)


class Safety(BaseModel):
    nsfw_score: float = Field(..., ge=0.0, le=1.0)
    blocked: bool = False


class ClassificationResult(BaseModel):
    model: str
    device: str
    predictions: list[Prediction]
    safety: Safety


class Health(BaseModel):
    status: str
    device: str | None = None
    model_loaded: bool | None = None
