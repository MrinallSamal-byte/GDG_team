"""
Development settings — extends base.py.

Usage:
    DJANGO_SETTINGS_MODULE=gdgProject.settings.dev python manage.py runserver

Or place a .env file in the project root with:
    DJANGO_SETTINGS_MODULE=gdgProject.settings.dev
"""
from .base import *  # noqa: F401,F403

# ─── Overrides ───────────────────────────────────────────────────────────────
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# ─── Database (SQLite for rapid local dev) ───────────────────────────────────
DATABASES["default"]["ENGINE"] = "django.db.backends.sqlite3"  # noqa: F405
DATABASES["default"]["NAME"] = BASE_DIR / "db.sqlite3"  # noqa: F405

# ─── Email — console in dev ─────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ─── Cache — in-memory for dev ───────────────────────────────────────────────
CACHES["default"]["BACKEND"] = "django.core.cache.backends.locmem.LocMemCache"  # noqa: F405

# ─── CORS / CSRF relaxation for local dev ────────────────────────────────────
CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]

# ─── Debug toolbar (uncomment when installed) ────────────────────────────────
# INSTALLED_APPS += ["debug_toolbar"]
# MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
# INTERNAL_IPS = ["127.0.0.1"]

# ─── Logging — human-readable in dev ────────────────────────────────────────
LOGGING["handlers"]["console"]["formatter"] = "verbose"  # noqa: F405
