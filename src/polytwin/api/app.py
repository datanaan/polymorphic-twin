"""FastAPI application factory for the Polymorphic-Twin integration layer.

Wires together TOM, Core, Lab, Bridge, production, audit, webhook, and
WebSocket route modules into a single FastAPI application.
"""

from __future__ import annotations

from fastapi import FastAPI

from polytwin.api.errors import register_error_handlers
from polytwin.api.routes import audit_prod, bridge, core, lab, tom, tom_prod, webhooks
from polytwin.api.websocket import router as ws_router


def create_app(test_mode: bool = False) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        test_mode: When True, uses in-memory singletons without external
            dependencies (no PostgreSQL, no file system access).

    Returns:
        Configured FastAPI instance with all route modules mounted.
    """
    application = FastAPI(title="Polymorphic-Twin", version="0.1.0")
    application.state.test_mode = test_mode

    # Core routes
    application.include_router(tom.router, prefix="/api/v1/tom", tags=["TOM"])
    application.include_router(core.router, prefix="/api/v1/core", tags=["Core"])
    application.include_router(lab.router, prefix="/api/v1/lab", tags=["Lab"])
    application.include_router(bridge.router, prefix="/api/v1/bridge", tags=["Bridge"])

    # Production routes
    application.include_router(tom_prod.router, prefix="/api/v1/prod/tom", tags=["TOM (Production)"])
    application.include_router(audit_prod.router, prefix="/api/v1/prod/audit", tags=["Audit (Production)"])
    application.include_router(webhooks.router, prefix="/api/v1/prod/webhooks", tags=["Webhooks"])

    # WebSocket
    application.include_router(ws_router)

    # Error handlers
    register_error_handlers(application)

    return application
