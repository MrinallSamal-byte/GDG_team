"""
Production settings — extends base.py.

All secrets MUST come from environment variables or a secrets manager.
"""

from decouple import config

from .base import *  # noqa: F401,F403

# ─── Security Hardening ─────────────────────────────────────────────────────
DEBUG = False
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# ─── Database (PostgreSQL via POSTGRES_URL) ──────────────────────────────────
# base.py already configures DATABASES from POSTGRES_URL using dj_database_url.
# Override only the connection pool settings appropriate for a long-running server.
DATABASES["default"]["CONN_MAX_AGE"] = 600  # noqa: F405
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True  # noqa: F405

# ─── Cache (Redis) ───────────────────────────────────────────────────────────
CACHES["default"] = {  # noqa: F405
    "BACKEND": "django.core.cache.backends.redis.RedisCache",
    "LOCATION": config("REDIS_URL", default="redis://redis:6379/0"),
}

# ─── Django Channels — Redis channel layer (required in production) ──────────
# InMemoryChannelLayer only works in single-process development; use Redis in prod.
CHANNEL_LAYERS = {  # noqa: F405
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [config("REDIS_URL", default="redis://redis:6379/0")],
        },
    }
}

# ─── Email (SMTP) ────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")

# ─── Static files (WhiteNoise) ────────────────────────────────────────────────
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ─── Logging — JSON in production ────────────────────────────────────────────
LOGGING["handlers"]["console"]["formatter"] = "json"  # noqa: F405
