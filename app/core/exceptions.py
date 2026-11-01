from typing import Any
import logging
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("inventory_api.exceptions")


class AppException(Exception):
    """Base application exception for deterministic error handling."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_SERVER_ERROR",
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details


class EntityNotFoundException(AppException):
    """Raised when a requested resource is not found."""

    def __init__(self, entity_name: str, identifier: Any) -> None:
        super().__init__(
            message=f"{entity_name} with identifier '{identifier}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details={"entity": entity_name, "identifier": str(identifier)},
        )


class ConflictException(AppException):
    """Raised when an operation conflicts with existing state (e.g. unique constraint)."""

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            details=details,
        )


class InsufficientStockException(AppException):
    """Raised when an order request exceeds available inventory stock."""

    def __init__(
        self,
        product_id: str,
        requested_quantity: int,
        available_quantity: int,
    ) -> None:
        super().__init__(
            message=(
                f"Insufficient stock for product '{product_id}'. "
                f"Requested: {requested_quantity}, Available: {available_quantity}"
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INSUFFICIENT_STOCK",
            details={
                "product_id": str(product_id),
                "requested_quantity": requested_quantity,
                "available_quantity": available_quantity,
            },
        )


class AuthenticationFailedException(AppException):
    """Raised when authentication credentials are invalid or expired."""

    def __init__(self, message: str = "Invalid credentials", details: Any = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_FAILED",
            details=details,
        )


class PermissionDeniedException(AppException):
    """Raised when an authenticated user lacks permission for the resource."""

    def __init__(self, message: str = "Operation not permitted") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="PERMISSION_DENIED",
        )


class BadRequestException(AppException):
    """Raised when client sends an invalid request."""

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BAD_REQUEST",
            details=details,
        )


async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    """Handles domain-level application exceptions."""
    logger.warning("Application exception [%s]: %s (Details: %s)", exc.error_code, exc.message, exc.details)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles Pydantic request validation errors."""
    errors = exc.errors()
    logger.warning("Request validation error: %s", errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Input validation failed",
            "details": [
                {
                    "loc": err.get("loc"),
                    "msg": err.get("msg"),
                    "type": err.get("type"),
                }
                for err in errors
            ],
        },
    )


async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handles standard HTTP exceptions."""
    logger.warning("HTTP %d error: %s", exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP_{exc.status_code}",
            "message": exc.detail if isinstance(exc.detail, str) else "HTTP error",
            "details": exc.detail if not isinstance(exc.detail, str) else None,
        },
    )


async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected internal server errors."""
    logger.exception("Unhandled server exception: %s", str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected server error occurred. Please contact system administrator.",
            "details": None,
        },
    )
