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
from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()
