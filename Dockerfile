# ═══════════════════════════════════════════════════════════════════════════════
# CampusArena — Production Dockerfile  (FIXED)
#
# Multi-stage build: builder → runtime
# Server: Daphne ASGI (HTTP + WebSockets via Django Channels)
# DB:     MySQL (mysqlclient)
#
# Key fixes vs. original:
#   • Builder now installs MySQL headers, not PostgreSQL (libpq-dev)
#   • Runtime uses libmariadb3 (shared lib only, no dev headers)
#   • CMD switched from gunicorn (WSGI) → daphne (ASGI) for WebSocket support
#   • entrypoint.sh runs migrations before server start
#   • collectstatic no longer silently swallowed — uses --skip-checks
#   • Non-root user created with proper chown
# ═══════════════════════════════════════════════════════════════════════════════

# ── Stage 1 : Builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# MySQL client headers + C compiler (needed to compile mysqlclient wheel)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2 : Runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=gdgProject.settings.prod \
    PORT=8000

WORKDIR /app

# MySQL shared library only (no dev headers needed at runtime)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libmariadb3 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy Django project source
COPY gdgProject/ ./

# ── Static file collection ───────────────────────────────────────────────────
# SECRET_KEY is required by Django's settings loader, but this value is
# NEVER used in production — real SECRET_KEY comes from the .env / env vars.
ARG SECRET_KEY=build-time-placeholder-not-used-at-runtime
ARG DEBUG=False

RUN SECRET_KEY=${SECRET_KEY} \
    DEBUG=${DEBUG} \
    python manage.py collectstatic --noinput --clear --skip-checks

# ── Security: non-root user ──────────────────────────────────────────────────
RUN addgroup --system campusarena \
    && adduser --system --no-create-home --ingroup campusarena campusarena \
    && chown -R campusarena:campusarena /app

# Entrypoint script (runs migrations before server starts)
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER campusarena

EXPOSE 8000

# ── Health check ─────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -sf http://localhost:8000/health/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]

# ── Daphne ASGI server ───────────────────────────────────────────────────────
# Daphne handles both HTTP and WebSocket (Django Channels) connections.
# Use --proxy-headers so HTTPS/IP are correctly forwarded by nginx/load-balancer.
CMD ["daphne", \
     "--bind", "0.0.0.0", \
     "--port", "8000", \
     "--access-log", "-", \
     "--proxy-headers", \
     "gdgProject.asgi:application"]
