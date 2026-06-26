#!/usr/bin/env bash
# Container entrypoint. First arg selects the role: "web" (default) or "worker".
set -euo pipefail

ROLE="${1:-web}"

wait_for() {
  local host="$1" port="$2" name="$3" tries=60
  echo "Waiting for ${name} (${host}:${port})..."
  until python -c "import socket,sys; s=socket.socket(); s.settimeout(2); \
    sys.exit(0) if s.connect_ex(('${host}', ${port}))==0 else sys.exit(1)" 2>/dev/null; do
    tries=$((tries - 1))
    if [ "$tries" -le 0 ]; then echo "Timed out waiting for ${name}"; exit 1; fi
    sleep 1
  done
  echo "${name} is up."
}

wait_for "${POSTGRES_HOST:-postgres}" "${POSTGRES_PORT:-5432}" "PostgreSQL"

if [ "$ROLE" = "web" ]; then
  echo "Applying migrations..."
  python manage.py migrate --noinput

  # Storage + admin bootstrap (best-effort; MinIO may still be warming up).
  wait_for "$(python -c "from urllib.parse import urlparse;import os;print(urlparse(os.environ['S3_ENDPOINT_URL']).hostname)")" \
           "$(python -c "from urllib.parse import urlparse;import os;print(urlparse(os.environ['S3_ENDPOINT_URL']).port or 9000)")" \
           "MinIO" || true
  python manage.py init_storage || echo "init_storage failed (will retry on next boot)"
  python manage.py ensure_admin || true
  python manage.py collectstatic --noinput

  echo "Starting gunicorn..."
  exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 120 \
    --access-logfile - --error-logfile -
elif [ "$ROLE" = "worker" ]; then
  echo "Starting Celery worker..."
  exec celery -A config worker --loglevel="${CELERY_LOGLEVEL:-info}" --concurrency="${CELERY_CONCURRENCY:-2}"
else
  echo "Unknown role: $ROLE"; exit 1
fi
