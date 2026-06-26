# syntax=docker/dockerfile:1
# Classifier image — GPU-capable model server.
#
# Built on python:3.12-slim with a CUDA-enabled torch wheel (cu121). The same
# image runs on GPU (when the NVIDIA runtime + a GPU are available, selected via
# docker-compose.gpu.yml or a K8s GPU node) and transparently falls back to CPU
# otherwise (MODEL_DEVICE=auto). Set CLASSIFIER_STUB=1 to skip model downloads.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models/.hf_cache \
    MODEL_DEVICE=auto

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash curl \
    && rm -rf /var/lib/apt/lists/*

# Base API deps (always). Then optionally the heavy ML stack.
#   INSTALL_TORCH=false              -> lightweight stub-only image (no torch).
#   TORCH_INDEX_URL=.../whl/cu121    -> GPU build (default; standard NVIDIA GPUs).
#   TORCH_INDEX_URL=.../whl/cpu      -> CPU build (smaller; also use for GPUs
#                                       too new for the cu121 kernels, e.g. Blackwell).
ARG INSTALL_TORCH=true
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121
COPY requirements.txt requirements-ml.txt ./
RUN pip install -r requirements.txt \
    && if [ "$INSTALL_TORCH" = "true" ]; then \
         pip install --extra-index-url "$TORCH_INDEX_URL" -r requirements-ml.txt; \
       fi

COPY . .

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /models/.hf_cache \
    && chown -R appuser:appuser /app /models
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=5 \
    CMD curl -fsS http://localhost:8000/readyz || exit 1

ENTRYPOINT ["bash", "entrypoint.sh"]
