"""Development settings — used by docker-compose and local `manage.py`."""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True

# Relaxed cookie security for plain-HTTP local development.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Email backend prints to console in dev.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

INTERNAL_IPS = ["127.0.0.1"]

# Allow overriding allowed hosts loosely in dev if needed.
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "webapp", "0.0.0.0"],  # noqa: S104
)
