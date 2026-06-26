"""
Base Django settings shared by all environments.

Environment-specific overrides live in ``dev.py`` / ``prod.py`` / ``test.py``.
Configuration is driven entirely by environment variables (12-factor) so the
same image runs unchanged in docker-compose and Kubernetes.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

# -----------------------------------------------------------------------------
# Core
# -----------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# -----------------------------------------------------------------------------
# Applications
# -----------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_filters",
    "django_prometheus",
]

LOCAL_APPS = [
    "accounts",
    "submissions",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# -----------------------------------------------------------------------------
# Database — PostgreSQL (see docs/database.md for the rationale)
# -----------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django_prometheus.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="photoplatform"),
        "USER": env("POSTGRES_USER", default="photo"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="photo"),
        "HOST": env("POSTGRES_HOST", default="postgres"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
        "OPTIONS": {"connect_timeout": 5},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

# -----------------------------------------------------------------------------
# Cache + Celery (Redis)
# -----------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("CACHE_URL", default="redis://redis:6379/2"),
    }
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://redis:6379/1")
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # fair dispatch for slow GPU tasks
CELERY_TASK_TIME_LIMIT = 180
CELERY_TASK_SOFT_TIME_LIMIT = 150

# -----------------------------------------------------------------------------
# Password validation / auth
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Argon2 preferred, PBKDF2 fallback (both ship with Django)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "submissions:home"
LOGOUT_REDIRECT_URL = "accounts:login"

# -----------------------------------------------------------------------------
# DRF + OpenAPI/Swagger
# -----------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # Safety rule #4: throttle to mitigate brute-force / spam / DoS
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/minute",
        "user": "120/minute",
        "auth": "10/minute",
        "upload": "20/minute",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Photo Classification Platform API",
    "DESCRIPTION": "User registration, photo submission + classification, and admin retrieval.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# -----------------------------------------------------------------------------
# Object storage (MinIO / S3) — see common/storage.py
# -----------------------------------------------------------------------------
S3_ENDPOINT_URL = env("S3_ENDPOINT_URL", default="http://minio:9000")
S3_PUBLIC_ENDPOINT_URL = env("S3_PUBLIC_ENDPOINT_URL", default="http://localhost:47900")
S3_BUCKET = env("S3_BUCKET", default="photos")
S3_REGION = env("S3_REGION", default="us-east-1")
S3_ACCESS_KEY = env("MINIO_ROOT_USER", default="minioadmin")
S3_SECRET_KEY = env("MINIO_ROOT_PASSWORD", default="minioadmin")
S3_SIGNED_URL_TTL = env.int("S3_SIGNED_URL_TTL", default=900)

# -----------------------------------------------------------------------------
# Classifier microservice
# -----------------------------------------------------------------------------
CLASSIFIER_URL = env("CLASSIFIER_URL", default="http://classifier:8000")
CLASSIFIER_TIMEOUT = env.int("CLASSIFIER_TIMEOUT", default=60)

# Identity-verification gate: failed camera checks allowed before lock-out.
MAX_VERIFICATION_ATTEMPTS = env.int("MAX_VERIFICATION_ATTEMPTS", default=3)

# -----------------------------------------------------------------------------
# Upload safety limits (see docs/safety.md)
# -----------------------------------------------------------------------------
MAX_UPLOAD_BYTES = env.int("MAX_UPLOAD_BYTES", default=8 * 1024 * 1024)
ALLOWED_IMAGE_TYPES = env.list(
    "ALLOWED_IMAGE_TYPES",
    default=["image/jpeg", "image/png", "image/webp", "image/heic", "image/avif"],
)
# Cap Django's in-memory upload handling to the same limit
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_BYTES
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_BYTES

# -----------------------------------------------------------------------------
# i18n / tz / static
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# -----------------------------------------------------------------------------
# Structured JSON logging (observability)
# -----------------------------------------------------------------------------
LOG_LEVEL = env("DJANGO_LOG_LEVEL", default="INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
