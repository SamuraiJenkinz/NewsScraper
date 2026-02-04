"""
BrasilIntel API - Competitive intelligence for Brazilian insurers.

FastAPI application entry point with database initialization and health check.
"""
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.database import Base, engine
# Import models to register them with Base.metadata before create_all
from app.models import insurer  # noqa: F401

# Load environment variables from .env file
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Creates database tables on startup, yields control during app lifetime,
    and handles cleanup on shutdown.
    """
    # Startup: Create data directory and database tables
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: Nothing to clean up for SQLite


app = FastAPI(
    title="BrasilIntel API",
    description="Competitive intelligence for Brazilian insurers",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/api/health", tags=["Health"])
def health_check() -> dict:
    """
    Health check endpoint.

    Returns service status for monitoring and load balancer health checks.
    """
    return {"status": "healthy", "service": "brasilintel"}


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect root to API documentation."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    uvicorn.run("app.main:app", host=host, port=port, reload=debug)
