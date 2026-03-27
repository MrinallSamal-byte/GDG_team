#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# CampusArena — Docker entrypoint
# Runs database migrations then hands off to the server process (CMD).
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

echo "──────────────────────────────────────────"
echo " CampusArena — starting up"
echo " DJANGO_SETTINGS_MODULE: ${DJANGO_SETTINGS_MODULE:-not set}"
echo "──────────────────────────────────────────"

db_host="${DB_HOST:-}"
db_port="${DB_PORT:-}"

if { [ -z "${db_host}" ] || [ -z "${db_port}" ]; } && [ -n "${DATABASE_URL:-}" ]; then
    parsed_db="$(python - <<'PY'
import os
from urllib.parse import urlparse

parsed = urlparse(os.environ["DATABASE_URL"])
print(parsed.hostname or "")
print(parsed.port or "")
PY
)"
    db_host="$(printf '%s\n' "${parsed_db}" | sed -n '1p')"
    db_port="$(printf '%s\n' "${parsed_db}" | sed -n '2p')"
fi

# Wait for the database to be ready (simple TCP probe, max 60 s)
if [ -n "${db_host}" ] && [ -n "${db_port}" ]; then
    echo "[entrypoint] Waiting for database at ${db_host}:${db_port} ..."
    for i in $(seq 1 30); do
        if bash -c "echo > /dev/tcp/${db_host}/${db_port}" 2>/dev/null; then
            echo "[entrypoint] Database is reachable (attempt ${i})."
            break
        fi
        if [ "${i}" -eq 30 ]; then
            echo "[entrypoint] ERROR: database never became reachable. Aborting."
            exit 1
        fi
        echo "[entrypoint] Attempt ${i}/30 — retrying in 2 s..."
        sleep 2
    done
fi

echo "[entrypoint] Running database migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Starting server: $*"
exec "$@"
