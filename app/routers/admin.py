"""
Admin interface router for BrasilIntel.

Provides web-based administration with HTTP Basic authentication.
Serves HTML pages using Jinja2 templates.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import verify_admin

router = APIRouter(prefix="/admin", tags=["Admin"])

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, name="admin_dashboard")
@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(
    request: Request,
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    Admin dashboard page.

    Shows system overview with run statistics, recent activity,
    and quick actions. Content detailed in Plan 08-02.

    Args:
        request: FastAPI request object
        username: Authenticated admin username

    Returns:
        Rendered dashboard HTML page
    """
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "username": username,
            "active": "dashboard"
        }
    )


@router.get("/insurers", response_class=HTMLResponse, name="admin_insurers")
async def insurers(
    request: Request,
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    Insurers management page.

    Lists all insurers with filtering and management capabilities.
    Content detailed in Plan 08-03.
    """
    return templates.TemplateResponse(
        "admin/placeholder.html",
        {
            "request": request,
            "username": username,
            "active": "insurers",
            "page_title": "Insurers",
            "page_icon": "bi-building",
            "plan_number": "08-03"
        }
    )


@router.get("/import", response_class=HTMLResponse, name="admin_import")
async def import_page(
    request: Request,
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    Import management page.

    Handles Excel file uploads and preview.
    Content detailed in Plan 08-03.
    """
    return templates.TemplateResponse(
        "admin/placeholder.html",
        {
            "request": request,
            "username": username,
            "active": "import",
            "page_title": "Import",
            "page_icon": "bi-upload",
            "plan_number": "08-03"
        }
    )


@router.get("/recipients", response_class=HTMLResponse, name="admin_recipients")
async def recipients(
    request: Request,
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    Email recipients management page.

    Configure report recipients per category.
    Content detailed in Plan 08-04.
    """
    return templates.TemplateResponse(
        "admin/placeholder.html",
        {
            "request": request,
            "username": username,
            "active": "recipients",
            "page_title": "Recipients",
            "page_icon": "bi-people",
            "plan_number": "08-04"
        }
    )


@router.get("/schedules", response_class=HTMLResponse, name="admin_schedules")
async def schedules(
    request: Request,
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    Schedule management page.

    View and modify category run schedules.
    Content detailed in Plan 08-05.
    """
    return templates.TemplateResponse(
        "admin/placeholder.html",
        {
            "request": request,
            "username": username,
            "active": "schedules",
            "page_title": "Schedules",
            "page_icon": "bi-calendar-check",
            "plan_number": "08-05"
        }
    )


@router.get("/settings", response_class=HTMLResponse, name="admin_settings")
async def settings(
    request: Request,
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    Settings page.

    System configuration and status.
    Content detailed in Plan 08-06.
    """
    return templates.TemplateResponse(
        "admin/placeholder.html",
        {
            "request": request,
            "username": username,
            "active": "settings",
            "page_title": "Settings",
            "page_icon": "bi-gear",
            "plan_number": "08-06"
        }
    )
