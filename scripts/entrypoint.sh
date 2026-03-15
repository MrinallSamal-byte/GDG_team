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

# Wait for the database to be ready (simple TCP probe, max 60 s)
if [ -n "${DB_HOST:-}" ] && [ -n "${DB_PORT:-}" ]; then
    echo "[entrypoint] Waiting for database at ${DB_HOST}:${DB_PORT} ..."
    for i in $(seq 1 30); do
        if bash -c "echo > /dev/tcp/${DB_HOST}/${DB_PORT}" 2>/dev/null; then
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
