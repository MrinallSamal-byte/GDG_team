# ═══════════════════════════════════════════════════════════════════════════════
# CampusArena — Procfile
#
# Used by: Heroku, Railway (non-Docker mode), Render, Dokku
#
# The `release` dyno runs once before each new deployment (runs migrations).
# The `web` dyno starts the ASGI server.
# ═══════════════════════════════════════════════════════════════════════════════

release: cd gdgProject && python manage.py migrate --noinput
web: cd gdgProject && daphne --bind 0.0.0.0 --port ${PORT:-8000} --proxy-headers --access-log - gdgProject.asgi:application
