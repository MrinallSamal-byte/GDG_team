"""
Development settings — extends base.py.

Usage:
    DJANGO_SETTINGS_MODULE=gdgProject.settings.dev python manage.py runserver

Database:
    Tries to connect to MySQL (from .env / environment).
    If MySQL is unreachable, automatically falls back to SQLite so the
    project runs for front-end / feature work without a running DB server.
"""

import os
import socket

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CACHES["default"]["BACKEND"] = "django.core.cache.backends.locmem.LocMemCache"  # noqa: F405

CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]

# ─── Database — MySQL with automatic SQLite fallback ─────────────────────────
def _mysql_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if something is listening on host:port."""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


_db = DATABASES["default"]  # noqa: F405 — pulled from base.py

if _db["ENGINE"] == "django.db.backends.mysql" and not _mysql_reachable(
    _db.get("HOST", "127.0.0.1"), _db.get("PORT", 3306)
):
    import warnings

    warnings.warn(
        "\n\n  ⚠️  MySQL is not reachable at "
        f"{_db.get('HOST', '127.0.0.1')}:{_db.get('PORT', 3306)}.\n"
        "  Falling back to SQLite for this session.\n"
        "  Start MySQL and restart the server to use the real database.\n",
        stacklevel=2,
    )
    DATABASES = {  # noqa: F405
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db_dev_fallback.sqlite3",  # noqa: F405
        }
    }

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
