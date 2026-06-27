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

# Check if the database is reachable before running migrations
_db_reachable="false"
if [ -n "${DATABASE_URL:-}" ]; then
    echo "[entrypoint] Checking database connection..."
    if python3 - <<'PYEOF'
import os, socket, sys
from urllib.parse import urlparse

url = os.environ.get("DATABASE_URL", "")
try:
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or 5432
    if host:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect((host, port))
        s.close()
        sys.exit(0)
except Exception as e:
    sys.stderr.write(f"[entrypoint] Database connection failed: {e}\n")
    sys.exit(1)
PYEOF
    then
        _db_reachable="true"
    fi
fi

if [ "${_db_reachable}" = "true" ]; then
    echo "[entrypoint] Running database migrations..."
    python manage.py migrate --noinput

    if [ "${AUTO_SEED_DEMO_DATA:-false}" = "true" ] || [ "${AUTO_SEED_DEMO_DATA:-0}" = "1" ]; then
        echo "[entrypoint] Bootstrapping demo data..."
        python manage.py bootstrap_demo_data
    fi
else
    echo "[entrypoint] WARNING: database is not reachable. Skipping migrations and seeding."
fi

echo "[entrypoint] Starting server: $*"
exec "$@"
