"""Celery application factory.

The same image runs as web (gunicorn) or worker (`celery -A config worker`).
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("photoplatform")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):  # pragma: no cover - utility
    print(f"Request: {self.request!r}")
