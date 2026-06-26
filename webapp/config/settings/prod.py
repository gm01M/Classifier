"""Production settings — hardened cookies, TLS, secrets from the environment.

The HTTPS-enforcement toggles are env-driven so the same prod image can run
behind TLS in Kubernetes (all enabled) and over plain HTTP in the local
docker-compose demo (relaxed via .env). Defaults are secure.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# Argon2 first in production (requires the `argon2-cffi` extra; PBKDF2 fallback stays).
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# TLS is terminated at the ingress; trust the forwarded proto header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = env.bool("DJANGO_SESSION_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env.bool("DJANGO_CSRF_COOKIE_SECURE", default=True)
SESSION_COOKIE_HTTPONLY = True
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
