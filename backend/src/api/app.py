"""FastAPI application factory and configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.accounts.endpoints import router as accounts_router
from src.api.auth.endpoints import router as auth_router
from src.api.connections.endpoints import router as connections_router
from src.api.transactions.endpoints import router as transactions_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    :returns: Configured FastAPI application.
    """
    app = FastAPI(
        title="Personal Finances API",
        description="API for personal finance management and bank account aggregation",
        version="0.1.0",
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

    # Include routers
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(accounts_router, prefix="/api/accounts", tags=["accounts"])
    app.include_router(connections_router, prefix="/api/connections", tags=["connections"])
    app.include_router(transactions_router, prefix="/api/transactions", tags=["transactions"])

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


app = create_app()
