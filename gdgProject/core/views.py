"""
Health-check endpoint — Deliverable #10.

Returns HTTP 200 with component status when the system is healthy.
Returns HTTP 503 with details when a critical component is down.
"""

import time

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    """
    Liveness + readiness probe.
    Checks: database connectivity, response time.
    """
    checks = {}
    healthy = True

    # ── Database ───────────────────────────────────────────────────────
    try:
        start = time.monotonic()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_ms = round((time.monotonic() - start) * 1000, 2)
        checks["database"] = {"status": "ok", "response_ms": db_ms}
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)}
        healthy = False

    # ── Cache (optional — skip if not configured) ─────────────────────
    try:
        from django.core.cache import cache

        cache.set("_health_check", "1", timeout=5)
        val = cache.get("_health_check")
        if val == "1":
            checks["cache"] = {"status": "ok"}
        else:
            checks["cache"] = {"status": "degraded", "detail": "Read-back mismatch"}
    except Exception as exc:
        checks["cache"] = {"status": "error", "detail": str(exc)}
        # Cache failure is non-critical — don't set healthy=False

    status = 200 if healthy else 503
    return JsonResponse(
        {
            "status": "healthy" if healthy else "unhealthy",
            "checks": checks,
            "version": "0.1.0",
        },
        status=status,
    )
