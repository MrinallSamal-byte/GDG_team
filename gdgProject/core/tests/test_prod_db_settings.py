"""
Regression tests for production database resolution.
"""

from gdgProject.settings._prod_db import resolve_production_database
from django.core.exceptions import ImproperlyConfigured


PLACEHOLDER_MYSQL = {
    "ENGINE": "django.db.backends.mysql",
    "NAME": "campusarena",
    "USER": "campusarena",
    "PASSWORD": "changeme",
    "HOST": "127.0.0.1",
    "PORT": "3306",
    "ATOMIC_REQUESTS": True,
    "OPTIONS": {
        "charset": "utf8mb4",
        "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
    },
}


def test_resolve_production_database_prefers_database_url():
    db_config = resolve_production_database(
        PLACEHOLDER_MYSQL,
        {
            "DATABASE_URL": "postgresql://render_user:secret@render-db.internal:5432/campusarena",
        },
    )

    assert db_config["ENGINE"] == "django.db.backends.postgresql"
    assert db_config["NAME"] == "campusarena"
    assert db_config["USER"] == "render_user"
    assert db_config["HOST"] == "render-db.internal"
    assert db_config["PORT"] == 5432
    assert db_config["ATOMIC_REQUESTS"] is True


def test_resolve_production_database_accepts_pg_environment_variables():
    db_config = resolve_production_database(
        PLACEHOLDER_MYSQL,
        {
            "PGHOST": "render-db.internal",
            "PGPORT": "5432",
            "PGDATABASE": "campusarena",
            "PGUSER": "render_user",
            "PGPASSWORD": "secret",
            "PGSSLMODE": "require",
        },
    )

    assert db_config["ENGINE"] == "django.db.backends.postgresql"
    assert db_config["NAME"] == "campusarena"
    assert db_config["USER"] == "render_user"
    assert db_config["HOST"] == "render-db.internal"
    assert db_config["PORT"] == "5432"
    assert db_config["OPTIONS"]["sslmode"] == "require"


def test_resolve_production_database_rejects_placeholder_mysql_defaults():
    try:
        resolve_production_database(PLACEHOLDER_MYSQL, {})
    except ImproperlyConfigured as exc:
        assert "Production database is not configured" in str(exc)
    else:
        raise AssertionError("Expected ImproperlyConfigured for placeholder MySQL config")
