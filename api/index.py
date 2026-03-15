"""
Vercel serverless entry point for CampusArena.

Vercel invokes this file for every HTTP request and looks for a WSGI
callable named `app`.

Directory layout (repo root):
    api/index.py          ← this file
    gdgProject/           ← Django project root (contains manage.py)
        gdgProject/       ← Django config package
            settings/
                vercel.py ← Vercel-specific settings
            wsgi.py
            asgi.py
        static/
        templates/
        ...apps...
"""

import os
import sys

# ── Make the Django project importable ───────────────────────────────────────
# Add  <repo_root>/gdgProject/  to sys.path so that
#   "from gdgProject.settings.vercel import ..."  resolves correctly.
_repo_root  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_django_dir = os.path.join(_repo_root, "gdgProject")

if _django_dir not in sys.path:
    sys.path.insert(0, _django_dir)

# ── Point Django at the Vercel settings module ───────────────────────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gdgProject.settings.vercel")

# ── Build the WSGI application ────────────────────────────────────────────────
# NOTE: Vercel is a serverless platform — each function invocation is
# stateless. Django Channels / WebSockets are NOT supported here.
# Use Railway, Render, or Fly.io if you need persistent WebSocket connections.

def _make_startup_error_app(exc):
    """Return a minimal WSGI app that explains the startup failure.

    The full traceback is written to the server log only (not the HTTP
    response) so that implementation details are not exposed to end users.
    """
    import logging as _logging
    import traceback as _tb

    _logging.getLogger("django").critical(
        "Django failed to start: %s\n%s", exc, _tb.format_exc()
    )
    _body = (
        "503 Service Unavailable — Django failed to start on Vercel.\n\n"
        f"{type(exc).__name__}: {exc}\n\n"
        "Common causes:\n"
        "  • SECRET_KEY not set  → Vercel Dashboard → Project → Settings → "
        "Environment Variables → Add SECRET_KEY\n"
        "  • DATABASE_URL not set → Add a PostgreSQL URL "
        "(e.g. from Neon https://neon.tech or Supabase)\n"
        "  • Missing package     → check api/requirements.txt\n"
    ).encode()

    def _error_app(environ, start_response):
        start_response(
            "503 Service Unavailable",
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", str(len(_body))),
            ],
        )
        return [_body]

    return _error_app


try:
    import django  # noqa: E402
    # django.setup() is called explicitly here (rather than letting
    # get_wsgi_application() do it) because collectstatic must run *before*
    # get_wsgi_application() builds the middleware chain — WhiteNoise needs the
    # files to exist in STATIC_ROOT when it initialises.
    django.setup()

    # ── Collect static files into /tmp on every cold start ───────────────────
    # Vercel's production filesystem is read-only.  WhiteNoise needs the files
    # to exist in STATIC_ROOT before the middleware initialises, so we run
    # collectstatic here (before get_wsgi_application builds the middleware
    # chain).  A sentinel file prevents re-running on warm invocations within
    # the same container instance, keeping subsequent requests fast.
    from django.conf import settings as _settings  # noqa: E402
    _sentinel = os.path.join(_settings.STATIC_ROOT, ".collected")
    if not os.path.exists(_sentinel):
        from django.core.management import call_command  # noqa: E402
        call_command("collectstatic", "--noinput", verbosity=0)
        # Write the sentinel so warm requests skip this step.
        with open(_sentinel, "w") as _f:
            _f.write("ok")

    from django.core.wsgi import get_wsgi_application  # noqa: E402

    app = get_wsgi_application()
except Exception as _startup_exc:  # noqa: BLE001
    app = _make_startup_error_app(_startup_exc)
