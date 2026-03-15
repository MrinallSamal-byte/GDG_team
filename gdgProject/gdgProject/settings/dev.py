"""
Development settings — extends base.py.

Usage:
    DJANGO_SETTINGS_MODULE=gdgProject.settings.dev python manage.py runserver

Database:
    Uses POSTGRES_URL when set in the environment / .env file.
    If POSTGRES_URL is not configured, automatically falls back to SQLite so
    the project runs for front-end / feature work without a running DB server.
"""

import os

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CACHES["default"]["BACKEND"] = "django.core.cache.backends.locmem.LocMemCache"  # noqa: F405

CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]

# ─── Database — PostgreSQL with automatic SQLite fallback ─────────────────────
# base.py already defaults to sqlite:///db.sqlite3 when POSTGRES_URL is absent.
# Log a notice so developers know which database is active.
if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":  # noqa: F405
    import warnings

    warnings.warn(
        "\n\n  ℹ️  POSTGRES_URL is not set.\n"
        "  Falling back to SQLite for this session.\n"
        "  Set POSTGRES_URL in your .env file to connect to PostgreSQL.\n",
        stacklevel=2,
    )

# ─── Django Channels — Redis if available, in-memory fallback ────────────────
_redis_url = os.environ.get("REDIS_URL", "")
if not _redis_url:
    try:
        from decouple import config as _cfg
        _redis_url = _cfg("REDIS_URL", default="")
    except ModuleNotFoundError:
        pass

if _redis_url:
    CHANNEL_LAYERS = {  # noqa: F405
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [_redis_url]},
        }
    }
# else: base.py already set InMemoryChannelLayer — no override needed

LOGGING["handlers"]["console"]["formatter"] = "verbose"  # noqa: F405
