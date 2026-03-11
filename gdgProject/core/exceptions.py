"""
Error Taxonomy — unified exception hierarchy for CampusArena.

Seven error classes covering the entire application surface.
Each exception carries a machine-readable `code`, an HTTP `status_code`,
and a user-safe `message`.
"""


class AppError(Exception):
    """Base application error. All custom exceptions inherit from this."""

    status_code: int = 500
    code: str = "internal_error"
    log_level: str = "error"  # error | warning | info

    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        details: dict | None = None,
    ):
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        payload = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.details:
            payload["error"]["details"] = self.details
        return payload


# ── 1. Validation Error ─────────────────────────────────────────────────────
class ValidationError(AppError):
    """Input validation failed (form data, query params, payload)."""

    status_code = 400
    code = "validation_error"
    log_level = "warning"


# ── 2. Authentication Error ─────────────────────────────────────────────────
class AuthenticationError(AppError):
    """User is not authenticated or credentials are invalid."""

    status_code = 401
    code = "authentication_error"
    log_level = "warning"


# ── 3. Permission Denied Error ──────────────────────────────────────────────
class PermissionDeniedError(AppError):
    """User is authenticated but lacks the required role/permission."""

    status_code = 403
    code = "permission_denied"
    log_level = "warning"


# ── 4. Not Found Error ─────────────────────────────────────────────────────
class NotFoundError(AppError):
    """Requested resource does not exist or has been soft-deleted."""

    status_code = 404
    code = "not_found"
    log_level = "info"


# ── 5. Conflict / Business Rule Error ──────────────────────────────────────
class ConflictError(AppError):
    """
    Operation violates a business invariant or produces a duplicate.
    Examples: duplicate registration, team already full, deadline passed.
    """

    status_code = 409
    code = "conflict"
    log_level = "warning"


# ── 6. Rate Limit Error ────────────────────────────────────────────────────
class RateLimitError(AppError):
    """Client has sent too many requests in a given time window."""

    status_code = 429
    code = "rate_limit_exceeded"
    log_level = "warning"


# ── 7. External Service Error ──────────────────────────────────────────────
class ExternalServiceError(AppError):
    """
    An external dependency (email provider, payment gateway, etc.) failed.
    Triggers circuit-breaker / retry logic.
    """

    status_code = 502
    code = "external_service_error"
    log_level = "error"
