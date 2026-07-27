"""Global error handlers for the Polymorphic-Twin FastAPI application.

Maps the SDK exception hierarchy to appropriate HTTP status codes so that
all responses follow a uniform ``{"error": ..., "detail": ...}`` shape.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from polytwin.exceptions import (
    ConstraintViolationError,
    DomainPackValidationError,
    IdentityDriftError,
    PermissionDeniedError,
    PolymorphicTwinError,
    SafetyFallbackError,
    ValidationError,
)


def register_error_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to a FastAPI application.

    Must be called after the app is created but before it starts serving.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(PolymorphicTwinError)
    async def polymorphic_twin_error_handler(
        request: Request,
        exc: PolymorphicTwinError,
    ) -> JSONResponse:
        status = 500
        if isinstance(exc, PermissionDeniedError):
            status = 403
        elif isinstance(exc, (ValidationError, DomainPackValidationError)):
            status = 400
        elif isinstance(exc, ConstraintViolationError):
            status = 422
        elif isinstance(exc, SafetyFallbackError):
            status = 503
        elif isinstance(exc, IdentityDriftError):
            status = 409
        return JSONResponse(
            status_code=status,
            content={"error": type(exc).__name__, "detail": str(exc)},
        )
