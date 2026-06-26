"""Test settings — fast hashing, in-process Celery, no external services required."""

from .base import *  # noqa: F401,F403

DEBUG = False

# Fast password hashing for tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Run Celery tasks synchronously and surface exceptions.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Local-memory cache so tests don't need Redis.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Use SQLite by default for unit tests unless a Postgres host is provided (CI uses Postgres).
import os  # noqa: E402

if not os.environ.get("POSTGRES_HOST"):
    DATABASES = {  # noqa: F405
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
else:
    DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"  # noqa: F405

# Disable throttling in tests.
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
