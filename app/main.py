"""
BrasilIntel API - Competitive intelligence for Brazilian insurers.

FastAPI application entry point with database initialization and health check.
"""
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from app.database import Base, engine, SessionLocal
# Import models to register them with Base.metadata before create_all
from app.models import insurer, run, news_item  # noqa: F401
from app.routers import insurers, import_export, runs, reports, schedules
from app.services.scheduler_service import SchedulerService

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Creates database tables on startup, starts the scheduler,
    yields control during app lifetime, and handles cleanup on shutdown.
    """
    # Startup: Create data directory and database tables
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)

    # Start scheduler for automated category runs
    scheduler_service = SchedulerService()
    try:
        await scheduler_service.start()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        # Don't block app startup if scheduler fails

    yield

    # Shutdown: Stop scheduler gracefully
    try:
        scheduler_service.shutdown(wait=False)
        logger.info("Scheduler shutdown complete")
    except Exception as e:
        logger.error(f"Error during scheduler shutdown: {e}")


app = FastAPI(
    title="BrasilIntel API",
    description="Competitive intelligence for Brazilian insurers",
    version="0.1.0",
    lifespan=lifespan
)

# Register API routers
app.include_router(insurers.router)
app.include_router(import_export.router)
app.include_router(runs.router)
app.include_router(reports.router, prefix="/api")
app.include_router(schedules.router)


@app.get("/api/health", tags=["Health"])
def health_check() -> dict:
    """
    Health check endpoint.

    Returns service status for monitoring and load balancer health checks.
    Validates database connectivity, data directory writability, and service configuration.
    """
    checks = {}
    overall_status = "healthy"

    # Check database connectivity
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        checks["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        overall_status = "unhealthy"

    # Check data directory writability
    data_dir = "data"
    try:
        os.makedirs(data_dir, exist_ok=True)
        test_file = os.path.join(data_dir, ".health_check")
        with open(test_file, "w") as f:
            f.write("health_check")
        os.remove(test_file)
        checks["data_directory"] = {
            "status": "healthy",
            "message": f"Data directory writable: {os.path.abspath(data_dir)}"
        }
    except Exception as e:
        checks["data_directory"] = {
            "status": "unhealthy",
            "message": f"Data directory not writable: {str(e)}"
        }
        overall_status = "unhealthy"

    # Check external services configuration
    services_config = {
        "azure_openai": {
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
            "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT")
        },
        "microsoft_graph": {
            "client_id": os.getenv("MICROSOFT_CLIENT_ID"),
            "client_secret": os.getenv("MICROSOFT_CLIENT_SECRET"),
            "tenant_id": os.getenv("MICROSOFT_TENANT_ID")
        },
        "apify": {
            "api_token": os.getenv("APIFY_API_TOKEN")
        }
    }

    checks["external_services"] = {}
    for service_name, config in services_config.items():
        missing_keys = [k for k, v in config.items() if not v]
        if missing_keys:
            checks["external_services"][service_name] = {
                "status": "warning",
                "message": f"Missing configuration: {', '.join(missing_keys)}"
            }
            if overall_status == "healthy":
                overall_status = "degraded"
        else:
            checks["external_services"][service_name] = {
                "status": "configured",
                "message": "All configuration keys present"
            }

    # Check scheduler status
    try:
        scheduler_service = SchedulerService()
        if scheduler_service._scheduler and scheduler_service._scheduler.running:
            jobs_count = len(scheduler_service._scheduler.get_jobs())
            checks["scheduler"] = {
                "status": "healthy",
                "message": f"Scheduler running with {jobs_count} jobs"
            }
        else:
            checks["scheduler"] = {
                "status": "warning",
                "message": "Scheduler not running"
            }
            if overall_status == "healthy":
                overall_status = "degraded"
    except Exception as e:
        checks["scheduler"] = {
            "status": "unhealthy",
            "message": f"Scheduler error: {str(e)}"
        }
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "service": "brasilintel",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }


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
