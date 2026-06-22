"""
Custom exceptions for the IUNA API.
"""


class IunaBaseError(Exception):
    """Base exception for all IUNA domain errors."""

    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None, status_code: int | None = None):
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.detail)


class NotFoundError(IunaBaseError):
    """Resource not found (404)."""

    status_code = 404
    detail = "Resource not found"


class ConflictError(IunaBaseError):
    """Conflict with current state (409)."""

    status_code = 409
    detail = "Conflict"


class ValidationError(IunaBaseError):
    """Validation error (422)."""

    status_code = 422
    detail = "Validation error"


class ServiceUnavailableError(IunaBaseError):
    """Dependency service unavailable (503)."""

    status_code = 503
    detail = "Service unavailable"


class UnauthorizedError(IunaBaseError):
    """Authentication required or failed (401)."""

    status_code = 401
    detail = "Unauthorized"
