"""Classifier FastAPI service.

  POST /v1/classify   multipart image -> structured attribute predictions
  GET  /healthz       liveness
  GET  /readyz        readiness (model loaded)
  GET  /metrics       Prometheus metrics
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings
from .model import SafetyBlocked, classifier
from .schemas import ClassificationResult, Health

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("classifier")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load (and warm) the model at startup so readiness reflects real state.
    classifier.load()
    logger.info("Model ready on device=%s", classifier.device_label)
    yield


app = FastAPI(title="Photo Classifier", version="1.0.0", lifespan=lifespan)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/healthz", response_model=Health)
def healthz() -> Health:
    return Health(status="ok")


@app.get("/readyz", response_model=Health)
def readyz() -> Health:
    if not classifier.ready:
        raise HTTPException(status_code=503, detail="model not loaded")
    return Health(status="ready", device=classifier.device_label, model_loaded=True)


@app.post("/v1/classify", response_model=ClassificationResult)
async def classify(file: UploadFile = File(...)) -> ClassificationResult:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File too large.")
    try:
        result = classifier.predict(data)
    except SafetyBlocked as exc:
        # 422 is the agreed "content blocked" signal the webapp maps to REJECTED.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("classification failed")
        raise HTTPException(status_code=500, detail="Classification failed.") from exc
    return ClassificationResult(**result)
