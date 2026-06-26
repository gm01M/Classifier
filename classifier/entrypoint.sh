#!/usr/bin/env bash
set -euo pipefail

# Single uvicorn worker: the model lives in process memory and we scale by
# replicas (pods), not threads, so GPU memory stays bounded per replica.
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers "${UVICORN_WORKERS:-1}" \
  --log-level "${UVICORN_LOG_LEVEL:-info}"
