# syntax=docker/dockerfile:1
# Webapp image — runs as either the web (gunicorn) or worker (celery) role.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

# Only runtime libs are needed: psycopg[binary] + Pillow ship their own.
# curl is handy for debugging; bash for the entrypoint.
RUN apt-get update && apt-get install -y --no-install-recommends \
        bash curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Bake static assets into the image so K8s pods can run gunicorn directly
# (no runtime collectstatic needed). Uses a throwaway settings/secret; no DB.
RUN DJANGO_SETTINGS_MODULE=config.settings.dev DJANGO_SECRET_KEY=build-only \
    python manage.py collectstatic --noinput

# Drop privileges (security: never run app code as root).
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/staticfiles \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

ENTRYPOINT ["bash", "entrypoint.sh"]
CMD ["web"]
