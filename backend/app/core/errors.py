"""Error handling schemas and custom HTTP exceptions."""

from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse


class RivalScopeError(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Any | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


# Aliased for standard convention
AppError = RivalScopeError


class AuthenticationError(RivalScopeError):
    def __init__(self, message: str = "Invalid or expired authentication credentials"):
        super().__init__(
            message=message,
            code="UNAUTHENTICATED",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class PermissionDeniedError(RivalScopeError):
    def __init__(self, message: str = "Operation not permitted"):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
        )


# Aliased
AuthorizationError = PermissionDeniedError


class NotFoundError(RivalScopeError):
    def __init__(self, message: str = "Requested resource not found"):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class RateLimitExceededError(RivalScopeError):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class ValidationError(RivalScopeError):
    def __init__(self, message: str = "Validation failed", details: Any | None = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class SSRFSecurityError(RivalScopeError):
    def __init__(self, message: str = "Destination IP address is blocked by security policy"):
        super().__init__(
            message=message,
            code="SSRF_PROHIBITED",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


def format_error_response(
    message: str,
    code: str,
    details: Any | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Return standard API error dictionary."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id,
        }
    }


async def rivalscope_exception_handler(request: Request, exc: RivalScopeError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            message=exc.message,
            code=exc.code,
            details=exc.details,
            request_id=request_id,
        ),
    )
