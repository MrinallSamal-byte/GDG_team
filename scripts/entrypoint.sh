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

# ── Render Docker: expand internal Postgres hostname ─────────────────────────
# Render's fromDatabase.connectionString injects the private-network short
# hostname (dpg-xxx-a). Docker containers don't receive Render's internal DNS
# resolver, so the short hostname is unresolvable. We probe each Render
# region's public domain via socket, rewrite DATABASE_URL in-place with the
# first hostname that resolves, and add sslmode=require for the TLS handshake.
if [[ "${RENDER:-}" != "true" ]] && [[ "${DATABASE_URL:-}" == *"@dpg-"* ]]; then
    _new_db_url="$(python3 - <<'PYEOF'
import os, re, socket, sys
from urllib.parse import urlparse

url = os.environ.get("DATABASE_URL", "")
if not url:
    sys.exit(0)

try:
    parsed = urlparse(url)
except Exception:
    sys.stdout.write(url)
    sys.exit(0)

host = parsed.hostname
if not host or not re.match(r"^dpg-[a-z0-9]+-[a-z0-9]+$", host):
    sys.stdout.write(url)
    sys.exit(0)

port = parsed.port or 5432

try:
    socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    sys.stdout.write(url)
    sys.exit(0)
except OSError:
    pass

regions = list(dict.fromkeys(filter(None, [
    os.environ.get("RENDER_POSTGRES_REGION", ""),
    "singapore", "oregon", "frankfurt", "ohio",
])))
for region in regions:
    candidate = f"{host}.{region}-postgres.render.com"
    try:
        socket.getaddrinfo(candidate, port, type=socket.SOCK_STREAM)
        new_url = url.replace(host, candidate, 1)
        if "sslmode" not in new_url:
            sep = "&" if "?" in new_url else "?"
            new_url += f"{sep}sslmode=require"
        sys.stderr.write(f"[entrypoint] Postgres host expanded: {host} -> {candidate}\n")
        sys.stdout.write(new_url)
        sys.exit(0)
    except OSError:
        continue

sys.stderr.write(f"[entrypoint] WARN: could not resolve Render Postgres host {host}\n")
sys.stdout.write(url)
PYEOF
)"
    if [[ -n "${_new_db_url}" ]]; then
        DATABASE_URL="${_new_db_url}"
        export DATABASE_URL
    fi
    unset _new_db_url
fi

db_host="${DB_HOST:-${PGHOST:-}}"
db_port="${DB_PORT:-${PGPORT:-}}"

if { [ -z "${db_host}" ] || [ -z "${db_port}" ]; } && [ -n "${DATABASE_URL:-}" ]; then
    parsed_db="$(python3 - <<'PY'
import os
from urllib.parse import urlparse

parsed = urlparse(os.environ.get("DATABASE_URL", ""))
print(parsed.hostname or "")
port = parsed.port
if not port and parsed.scheme in ("postgres", "postgresql"):
    port = 5432
print(port or "")
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

if [ "${AUTO_SEED_DEMO_DATA:-false}" = "true" ] || [ "${AUTO_SEED_DEMO_DATA:-0}" = "1" ]; then
    echo "[entrypoint] Bootstrapping demo data..."
    python manage.py bootstrap_demo_data
fi

echo "[entrypoint] Starting server: $*"
exec "$@"
