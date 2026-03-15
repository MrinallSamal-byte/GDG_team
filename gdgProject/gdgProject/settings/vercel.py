"""
Vercel serverless settings for CampusArena.

⚠️  IMPORTANT LIMITATIONS on Vercel:
    1. WebSockets / Django Channels are NOT supported.
       (Vercel is stateless HTTP — no persistent TCP connections.)
       Channel layer falls back to InMemoryChannelLayer (single-instance only).
    2. The filesystem is read-only except /tmp.
       Media file uploads must go to cloud storage (Cloudinary, S3, etc.).
    3. Function timeout is 10 s (Hobby) / 300 s (Pro) — keep views fast.
    4. Cold-start penalty applies — avoid heavy module-level imports.

Required environment variables (set in Vercel Dashboard → Settings → Env Vars):
    SECRET_KEY          — Django secret key (generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
    DATABASE_URL        — PostgreSQL URL from Neon / Supabase  e.g. postgresql://user:pass@host/db?sslmode=require
    ALLOWED_HOSTS       — comma-separated  e.g. campusarena.vercel.app,campusarena.com
    REDIS_URL           — Upstash Redis URL  e.g. redis://default:token@host:port
    EMAIL_HOST_USER     — SMTP user
    EMAIL_HOST_PASSWORD — SMTP app-password
    SITE_URL            — https://campusarena.vercel.app

Recommended free-tier providers for Vercel:
    Database : Neon (https://neon.tech)  — serverless PostgreSQL
    Redis    : Upstash (https://upstash.com) — serverless Redis
    Media    : Cloudinary (https://cloudinary.com) — file / image hosting
"""

import os

import dj_database_url

from .base import *  # noqa: F401, F403

# ── Core ─────────────────────────────────────────────────────────────────────
DEBUG = False

# SECRET_KEY must be set in Vercel Dashboard → Project → Settings → Environment
# Variables.  An insecure fallback is provided so the process can start and
# return a meaningful error page rather than a raw Python traceback, but any
# deployment running on the fallback key is INSECURE: sessions, CSRF tokens,
# password-reset links and signed cookies will all be compromised.
_secret_key = os.environ.get("SECRET_KEY", "").strip()
if not _secret_key:
    import logging as _logging
    import secrets as _secrets
    _secret_key = _secrets.token_urlsafe(50)
    _logging.getLogger("django").critical(
        "SECRET_KEY environment variable is not set. "
        "Add it in Vercel Dashboard → Project → Settings → Environment Variables. "
        "The application is running with an INSECURE ephemeral key — "
        "sessions and CSRF tokens will be invalidated on every cold start."
    )
SECRET_KEY = _secret_key

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", ".vercel.app").split(",")
    if h.strip()
]

# Trust Vercel's TLS termination proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT      = False   # Vercel handles HTTPS at the edge
SECURE_HSTS_SECONDS      = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD      = True
SECURE_CONTENT_TYPE_NOSNIFF = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE    = True

CSRF_TRUSTED_ORIGINS = (
    [f"https://{h}" for h in ALLOWED_HOSTS if not h.startswith(".")]
    + ["https://*.vercel.app"]
)

# ── Database — PostgreSQL via DATABASE_URL ───────────────────────────────────
# Free options: Neon (https://neon.tech), Supabase (https://supabase.com)
#
# IMPORTANT: Always override the MySQL default inherited from base.py.
# Vercel build images do not have the MySQL C headers required by mysqlclient,
# so keeping the MySQL engine would cause an ImproperlyConfigured crash on
# every cold-start even before a request is served.
#
# Fallback chain:
#   1. DATABASE_URL set  → PostgreSQL (psycopg2-binary, included in api/requirements.txt)
#   2. DATABASE_URL unset → SQLite in /tmp so Django can start and return the
#      helpful 503 error page rather than a raw Python traceback.
#
DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "/tmp/db.sqlite3",
    }
}

_database_url = os.environ.get("DATABASE_URL", "").strip()
if _database_url:
    DATABASES["default"] = dj_database_url.config(
        default=_database_url,
        conn_max_age=0,          # serverless: don't persist connections
        conn_health_checks=True,
        ssl_require=True,
    )

# ── Cache — Upstash Redis (HTTP mode, works with serverless) ─────────────────
_redis_url = os.environ.get("REDIS_URL", "")
if _redis_url:
    CACHES["default"] = {  # noqa: F405
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": _redis_url,
        "OPTIONS": {
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
        },
    }

# ── Django Channels — WebSockets NOT supported on Vercel ─────────────────────
# InMemoryChannelLayer is single-process only. Real-time features will not
# work across multiple serverless instances.
# → Deploy to Railway / Render / Fly.io for full WebSocket support.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# ── Static files — WhiteNoise (served directly by the WSGI process) ──────────
# Vercel's production filesystem is read-only; only /tmp is writable.
# api/index.py calls `collectstatic` on each cold start and writes into /tmp.
STATIC_ROOT = Path("/tmp/staticfiles")  # noqa: F405  (Path imported via base.*)

if "whitenoise.middleware.WhiteNoiseMiddleware" not in MIDDLEWARE:  # noqa: F405
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405

STORAGES = {
    "staticfiles": {
        # CompressedStaticFilesStorage: gzip/brotli-compresses files but does
        # NOT use a hashed-filename manifest, so missing files never raise
        # ValueError at request time.
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND       = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST          = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT          = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL  = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)

# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING["handlers"]["console"]["formatter"] = "verbose"  # noqa: F405
