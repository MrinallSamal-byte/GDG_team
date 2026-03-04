"""
Global exception-handler middleware.

Catches AppError subclasses and unhandled exceptions, returning either
JSON (for XHR/API requests) or rendered HTML error pages.
"""
import logging
import traceback
import uuid

from django.http import JsonResponse
from django.shortcuts import render

from core.exceptions import AppError

logger = logging.getLogger("campusarena.middleware")


class ErrorHandlerMiddleware:
    """
    Unified error handler — maps AppError subtypes to structured responses.

    JSON response contract:
    {
        "error": {
            "code": "validation_error",
            "message": "Human-readable message.",
            "request_id": "uuid",
            "details": {}           // optional
        }
    }

    HTML response:
    Renders templates/400.html, templates/404.html, templates/500.html
    with the same context variables.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        request_id = str(uuid.uuid4())

        if isinstance(exception, AppError):
            return self._handle_app_error(request, exception, request_id)

        # Unhandled exception → 500
        logger.error(
            "unhandled_exception",
            extra={
                "request_id": request_id,
                "path": request.path,
                "method": request.method,
                "exception": str(exception),
                "traceback": traceback.format_exc(),
            },
        )
        return self._respond(
            request,
            status=500,
            code="internal_error",
            message="An unexpected error occurred. Please try again later.",
            request_id=request_id,
        )

    def _handle_app_error(self, request, exc: AppError, request_id: str):
        log_method = getattr(logger, exc.log_level, logger.warning)
        log_method(
            exc.code,
            extra={
                "request_id": request_id,
                "path": request.path,
                "method": request.method,
                "message": exc.message,
                "details": exc.details,
            },
        )
        return self._respond(
            request,
            status=exc.status_code,
            code=exc.code,
            message=exc.message,
            request_id=request_id,
            details=exc.details,
        )

    def _respond(self, request, *, status, code, message, request_id, details=None):
        if self._wants_json(request):
            payload = {
                "error": {
                    "code": code,
                    "message": message,
                    "request_id": request_id,
                }
            }
            if details:
                payload["error"]["details"] = details
            return JsonResponse(payload, status=status)

        # HTML fallback
        template = f"{status}.html" if status in (400, 404, 500) else "500.html"
        return render(
            request,
            template,
            {
                "error_code": code,
                "error_message": message,
                "request_id": request_id,
                "status_code": status,
            },
            status=status,
        )

    @staticmethod
    def _wants_json(request) -> bool:
        accept = request.META.get("HTTP_ACCEPT", "")
        return (
            "application/json" in accept
            or request.content_type == "application/json"
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        )
