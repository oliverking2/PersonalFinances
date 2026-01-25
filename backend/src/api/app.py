"""FastAPI application factory and configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.accounts.endpoints import router as accounts_router
from src.api.analytics.endpoints import router as analytics_router
from src.api.auth.endpoints import router as auth_router
from src.api.connections.endpoints import router as connections_router
from src.api.institutions.endpoints import router as institutions_router
from src.api.jobs.endpoints import router as jobs_router
from src.api.middleware import RequestTimingMiddleware
from src.api.tags.endpoints import router as tags_router
from src.api.transactions.endpoints import router as transactions_router
from src.utils.definitions import is_api_docs_disabled
from src.utils.logging import configure_logging


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    :returns: Configured FastAPI application.
    """
    configure_logging()

    # Disable docs in production if configured
    docs_url = None if is_api_docs_disabled() else "/docs"
    redoc_url = None if is_api_docs_disabled() else "/redoc"

    app = FastAPI(
        title="Personal Finances API",
        description="API for personal finance management and bank account aggregation",
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
    )

    # Configure CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://frontend:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request timing middleware (logs at DEBUG level)
    app.add_middleware(RequestTimingMiddleware)

    # Include routers
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(accounts_router, prefix="/api/accounts", tags=["accounts"])
    app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
    app.include_router(connections_router, prefix="/api/connections", tags=["connections"])
    app.include_router(institutions_router, prefix="/api/institutions", tags=["institutions"])
    app.include_router(jobs_router, prefix="/api/jobs", tags=["jobs"])
    app.include_router(tags_router, prefix="/api/tags", tags=["tags"])
    app.include_router(transactions_router, prefix="/api/transactions", tags=["transactions"])

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


app = create_app()
