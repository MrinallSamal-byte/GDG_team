"""
Production settings — extends base.py.

All secrets MUST come from environment variables or a secrets manager.
"""

import os

from decouple import config
from django.core.exceptions import ImproperlyConfigured

from ._prod_db import resolve_production_database
from .base import *  # noqa: F401,F403

# ─── Security Hardening ─────────────────────────────────────────────────────
DEBUG = False

secret_key = os.environ.get("SECRET_KEY", "").strip()
if not secret_key:
    raise ImproperlyConfigured("SECRET_KEY must be set when using production settings.")
SECRET_KEY = secret_key

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
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

render_external_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if (
    render_external_hostname and render_external_hostname not in ALLOWED_HOSTS
):  # noqa: F405
    ALLOWED_HOSTS.append(render_external_hostname)  # noqa: F405

site_url = config("SITE_URL", default="").strip()
csrf_trusted_origins = set()
if site_url.startswith(("http://", "https://")):
    csrf_trusted_origins.add(site_url.rstrip("/"))
if render_external_hostname:
    csrf_trusted_origins.add(f"https://{render_external_hostname}")
if csrf_trusted_origins:
    CSRF_TRUSTED_ORIGINS = sorted(csrf_trusted_origins)

# ─── Database (DATABASE_URL with MySQL fallback) ─────────────────────────────
effective_db_env = {}
for key in (
    "DATABASE_URL",
    "PGHOST",
    "PGPORT",
    "PGDATABASE",
    "PGUSER",
    "PGPASSWORD",
    "PGSSLMODE",
    "ALLOW_LOCALHOST_DB",
):
    value = os.environ.get(key)
    if not value:
        value = config(key, default="")
    if value:
        effective_db_env[key] = str(value).strip()

DATABASES["default"] = resolve_production_database(  # noqa: F405
    DATABASES["default"],
    effective_db_env,
)

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
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=False, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="").strip()
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="").strip()
DEFAULT_FROM_EMAIL = (
    config("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER).strip() or EMAIL_HOST_USER
)

# ─── Static files (WhiteNoise) ────────────────────────────────────────────────
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ─── Logging — JSON in production ────────────────────────────────────────────
LOGGING["handlers"]["console"]["formatter"] = "json"  # noqa: F405
