"""
Helpers for resolving production database configuration.

Production must never silently fall back to the placeholder localhost MySQL
settings from ``base.py``. These helpers keep that logic explicit and testable.
"""

from __future__ import annotations

import os
import re
from copy import deepcopy

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

_RENDER_SHORT_PG_HOST = re.compile(r"^dpg-[a-z0-9]+-[a-z0-9]+$")


def _expand_render_postgres_host(host: str) -> str:
    """
    Render Docker services cannot resolve Render's short internal Postgres
    hostname (e.g. ``dpg-xxx-a``) via DNS because Docker containers run in
    a separate network namespace that doesn't have Render's private DNS
    resolver injected.

    When ``RENDER_POSTGRES_REGION`` is set (e.g. ``singapore``), expand the
    short hostname to the full external form that public DNS can resolve:

        dpg-xxx-a  →  dpg-xxx-a.<region>-postgres.render.com
    """
    if not _RENDER_SHORT_PG_HOST.match(host):
        return host
    region = _clean(os.environ.get("RENDER_POSTGRES_REGION", ""))
    if not region:
        return host
    return f"{host}.{region}-postgres.render.com"

PLACEHOLDER_MYSQL_DEFAULTS = {
    "ENGINE": "django.db.backends.mysql",
    "NAME": "campusarena",
    "USER": "campusarena",
    "PASSWORD": "changeme",
    "HOST": "127.0.0.1",
    "PORT": "3306",
}


def _clean(value) -> str:
    """Normalize env-style values into comparable stripped strings."""
    if value is None:
        return ""
    return str(value).strip()


def _looks_like_placeholder_mysql(db_config: dict) -> bool:
    """Return True when the config still matches base.py's placeholder values."""
    return all(
        _clean(db_config.get(key)) == expected
        for key, expected in PLACEHOLDER_MYSQL_DEFAULTS.items()
    )


def _truthy(value) -> bool:
    """Interpret common environment truthy strings."""
    return _clean(value).lower() in {"1", "true", "yes", "on"}


def _uses_localhost_mysql(db_config: dict) -> bool:
    """Return True when production would try to use a local MySQL socket/TCP host."""
    return (
        _clean(db_config.get("ENGINE")) == "django.db.backends.mysql"
        and _clean(db_config.get("HOST")).lower() in {"", "127.0.0.1", "localhost"}
    )


def _database_from_url(database_url: str) -> dict:
    """Parse DATABASE_URL into a Django DATABASES entry."""
    db_config = dj_database_url.parse(
        database_url,
        conn_max_age=600,
        conn_health_checks=True,
    )
    db_config["ATOMIC_REQUESTS"] = True
    if db_config.get("ENGINE") == "django.db.backends.postgresql":
        original_host = db_config.get("HOST", "")
        expanded_host = _expand_render_postgres_host(original_host)
        if expanded_host != original_host:
            db_config["HOST"] = expanded_host
            db_config.setdefault("OPTIONS", {})["sslmode"] = "require"
    return db_config


def _database_from_pg_env(env: dict) -> dict | None:
    """Build a PostgreSQL config from PG* environment variables."""
    host = _clean(env.get("PGHOST"))
    name = _clean(env.get("PGDATABASE"))
    user = _clean(env.get("PGUSER"))

    if not (host and name and user):
        return None

    expanded_host = _expand_render_postgres_host(host)

    db_config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": name,
        "USER": user,
        "PASSWORD": _clean(env.get("PGPASSWORD")),
        "HOST": expanded_host,
        "PORT": _clean(env.get("PGPORT")) or "5432",
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": 600,
        "CONN_HEALTH_CHECKS": True,
    }

    sslmode = _clean(env.get("PGSSLMODE"))
    if sslmode:
        db_config["OPTIONS"] = {"sslmode": sslmode}
    elif expanded_host != host:
        db_config["OPTIONS"] = {"sslmode": "require"}

    return db_config


def resolve_production_database(default_db: dict, env: dict) -> dict:
    """
    Resolve the production DB config.

    Resolution order:
    1. ``DATABASE_URL``
    2. ``PG*`` variables
    3. Explicit ``DB_*`` / default_db values, as long as they are not the
       placeholder localhost MySQL defaults from ``base.py``
    """
    database_url = _clean(env.get("DATABASE_URL"))
    if database_url:
        return _database_from_url(database_url)

    pg_config = _database_from_pg_env(env)
    if pg_config:
        return pg_config

    db_config = deepcopy(default_db)
    db_config["CONN_MAX_AGE"] = 600
    db_config["CONN_HEALTH_CHECKS"] = True

    if db_config.get("ENGINE") == "django.db.backends.mysql":
        db_config["OPTIONS"] = {
            **db_config.get("OPTIONS", {}),
            "connect_timeout": 5,
        }

    if _looks_like_placeholder_mysql(db_config):
        raise ImproperlyConfigured(
            "Production database is not configured. Set DATABASE_URL for "
            "Render/Postgres, provide PGHOST/PGDATABASE/PGUSER/PGPASSWORD, "
            "or override the DB_* settings for your production database."
        )

    if _uses_localhost_mysql(db_config) and not _truthy(env.get("ALLOW_LOCALHOST_DB")):
        raise ImproperlyConfigured(
            "Production MySQL configuration points to localhost. This is almost "
            "certainly incorrect in Render. Remove stale DB_* variables and set "
            "DATABASE_URL, or set ALLOW_LOCALHOST_DB=true only if localhost "
            "MySQL is truly intentional."
        )

    return db_config
