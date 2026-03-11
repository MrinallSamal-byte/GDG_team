"""
Test settings — fast, hermetic, in-memory.

Usage:
    DJANGO_SETTINGS_MODULE=gdgProject.settings.test pytest
"""

from .base import *  # noqa: F401, F403

# ── Database ─────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "ATOMIC_REQUESTS": True,
    }
}

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# ── Passwords (faster hashing for tests) ─────────────────────────────────────
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# ── Cache — dummy (no side-effects between tests) ────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# ── Logging — suppress test noise ────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"]},
}

# ── Media ─────────────────────────────────────────────────────────────────────
DEFAULT_FILE_STORAGE = "django.core.files.storage.InMemoryStorage"

# ── Misc ──────────────────────────────────────────────────────────────────────
DEBUG = False
ALLOWED_HOSTS = ["*"]
SECRET_KEY = "test-secret-key-not-for-production"  # noqa: S105
