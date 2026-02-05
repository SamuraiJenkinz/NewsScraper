"""
Admin interface router for BrasilIntel.

Provides web-based administration with HTTP Basic authentication.
Serves HTML pages using Jinja2 templates.
"""
import uuid
from datetime import datetime, timedelta
from io import BytesIO

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import get_settings, Settings
from app.dependencies import get_db, verify_admin
from app.models.insurer import Insurer
from app.models.run import Run
from app.services.excel_service import parse_excel_insurers
from app.services.scheduler_service import SchedulerService
from app.services.report_archiver import ReportArchiver

router = APIRouter(prefix="/admin", tags=["Admin"])

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# In-memory storage for import previews
# Key: session_id, Value: {"data": [...], "errors": [...], "expires": datetime}
import_sessions: dict[str, dict] = {}


def cleanup_expired_sessions() -> None:
    """Remove expired preview sessions."""
    now = datetime.now()
    expired = [k for k, v in import_sessions.items() if v["expires"] < now]
    for k in expired:
        del import_sessions[k]


# ----- Template Filters -----

def format_datetime(value) -> str:
    """Format datetime for display."""
    if not value:
        return "Never"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    return value.strftime("%d/%m/%Y %H:%M")


def timeago(value) -> str:
    """Convert datetime to relative time string."""
    if not value:
        return "Never"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value

    # Handle timezone-aware datetimes
    now = datetime.now()
    if value.tzinfo is not None:
        value = value.replace(tzinfo=None)

    delta = now - value

    if delta < timedelta(minutes=1):
        return "Just now"
    elif delta < timedelta(hours=1):
        minutes = int(delta.seconds / 60)
        return f"{minutes} min ago"
    elif delta < timedelta(days=1):
        hours = int(delta.seconds / 3600)
        return f"{hours} hours ago"
    else:
        return f"{delta.days} days ago"


def status_color(status) -> str:
    """Map status to Bootstrap color class."""
    colors = {
        "completed": "success",
        "failed": "danger",
        "running": "primary",
        "pending": "secondary",
        "healthy": "success",
        "warning": "warning",
        "error": "danger",
        "sent": "success",
        "skipped": "secondary",
    }
    return colors.get(str(status).lower(), "secondary")


# Register filters with templates
templates.env.filters["format_datetime"] = format_datetime
templates.env.filters["timeago"] = timeago
templates.env.filters["status_color"] = status_color


# ----- Helper Functions -----

def get_category_stats(db: Session, category: str) -> dict:
    """
    Get statistics for a category.

    Args:
        db: Database session
        category: Category name (Health, Dental, Group Life)

    Returns:
        Dictionary with insurer_count, last_run info, next_run, enabled
    """
    # Get insurer count for category (enabled only)
    insurer_count = db.query(func.count(Insurer.id)).filter(
        Insurer.category == category,
        Insurer.enabled == True
    ).scalar() or 0

    # Get latest run for category
    last_run = db.query(Run).filter(
        Run.category == category
    ).order_by(Run.started_at.desc()).first()

    last_run_info = None
    if last_run:
        last_run_info = {
            "id": last_run.id,
            "status": last_run.status,
            "time": last_run.started_at,
            "insurers_processed": last_run.insurers_processed or 0,
            "items_found": last_run.items_found or 0,
        }

    # Get schedule info from SchedulerService
    scheduler = SchedulerService()
    schedule = scheduler.get_schedule(category)

    next_run = None
    enabled = True
    if schedule:
        next_run = schedule.get("next_run_time")
        enabled = not schedule.get("paused", False)

    return {
        "category": category,
        "insurer_count": insurer_count,
        "last_run": last_run_info,
        "next_run": next_run,
        "enabled": enabled,
    }


def get_system_health(settings: Settings) -> dict:
    """
    Get overall system health status.

    Returns:
        Dictionary with status (healthy/warning/error) and service details
    """
    services = {}
    issues = []

    # Check database (if we got here, it's working)
    services["database"] = {"status": "healthy", "message": "Connected"}

    # Check scheduler
    scheduler = SchedulerService()
    if scheduler.is_running:
        services["scheduler"] = {"status": "healthy", "message": "Running"}
    else:
        services["scheduler"] = {"status": "warning", "message": "Not running"}
        issues.append("Scheduler not running")

    # Check Azure OpenAI
    if settings.is_azure_openai_configured():
        services["azure_openai"] = {"status": "healthy", "message": "Configured"}
    else:
        services["azure_openai"] = {"status": "warning", "message": "Not configured"}
        issues.append("Azure OpenAI not configured")

    # Check Graph Email
    if settings.is_graph_configured():
        services["graph_email"] = {"status": "healthy", "message": "Configured"}
    else:
        services["graph_email"] = {"status": "warning", "message": "Not configured"}
        issues.append("Graph Email not configured")

    # Check Apify
    if settings.is_apify_configured():
        services["apify"] = {"status": "healthy", "message": "Configured"}
    else:
        services["apify"] = {"status": "warning", "message": "Not configured"}
        issues.append("Apify not configured")

    # Determine overall status
    error_count = sum(1 for s in services.values() if s["status"] == "error")
    warning_count = sum(1 for s in services.values() if s["status"] == "warning")

    if error_count > 0:
        overall = "error"
    elif warning_count > 0:
        overall = "warning"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "services": services,
        "issues": issues,
    }


def get_recent_reports(limit: int = 5) -> list[dict]:
    """
    Get recent archived reports.

    Args:
        limit: Maximum number of reports to return

    Returns:
        List of report metadata dicts with date, category, filename, view_url
    """
    archiver = ReportArchiver()
    reports = archiver.browse_reports(limit=limit)

    result = []
    for report in reports:
        result.append({
            "date": report.get("date", ""),
            "category": report.get("category", ""),
            "filename": report.get("filename", ""),
            "timestamp": report.get("timestamp", ""),
            "view_url": f"/api/reports/archive/{report.get('date', '')}/{report.get('filename', '')}",
            "size_kb": report.get("size_kb", 0),
        })

    return result


# ----- Dashboard Routes -----

@router.get("/", response_class=HTMLResponse, name="admin_dashboard")
@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(
    request: Request,
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
) -> HTMLResponse:
    """
    Admin dashboard page.

    Shows system overview with category cards, system status,
    and recent reports list.

    Args:
        request: FastAPI request object
        username: Authenticated admin username
        db: Database session
        settings: Application settings

    Returns:
        Rendered dashboard HTML page
    """
    # Gather data for all categories
    categories = ["Health", "Dental", "Group Life"]
    category_stats = {cat: get_category_stats(db, cat) for cat in categories}

    # Get system health
    system_health = get_system_health(settings)

    # Get recent reports
    recent_reports = get_recent_reports(limit=5)

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "username": username,
            "active": "dashboard",
            "categories": categories,
            "category_stats": category_stats,
            "system_health": system_health,
            "recent_reports": recent_reports,
        }
    )


@router.get("/dashboard/card/{category}", response_class=HTMLResponse, name="admin_dashboard_card")
async def dashboard_card(
    request: Request,
    category: str,
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """
    HTMX partial for category card refresh.

    Args:
        request: FastAPI request object
        category: Category name (Health, Dental, Group Life)
        username: Authenticated admin username
        db: Database session

    Returns:
        Rendered category card partial
    """
    # Normalize category name
    category_map = {
        "health": "Health",
        "dental": "Dental",
        "group_life": "Group Life",
        "group life": "Group Life",
    }
    normalized = category_map.get(category.lower(), category)

    stats = get_category_stats(db, normalized)

    return templates.TemplateResponse(
        "admin/partials/category_card.html",
        {
            "request": request,
            "stats": stats,
        }
    )


@router.get("/dashboard/reports", response_class=HTMLResponse, name="admin_dashboard_reports")
async def dashboard_reports(
    request: Request,
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    HTMX partial for recent reports list refresh.

    Args:
        request: FastAPI request object
        username: Authenticated admin username

    Returns:
        Rendered recent reports partial
    """
    recent_reports = get_recent_reports(limit=5)

    return templates.TemplateResponse(
        "admin/partials/recent_reports.html",
        {
            "request": request,
            "reports": recent_reports,
        }
    )


# ----- Insurers Routes -----

@router.get("/insurers", response_class=HTMLResponse, name="admin_insurers")
async def insurers(
    request: Request,
    category: str | None = None,
    search: str | None = None,
    enabled: str | None = None,
    page: int = 1,
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """
    Insurers management page.

    Lists all insurers with filtering, search, and management capabilities.
    Supports HTMX partial updates for category tabs, search, and status filter.

    Args:
        request: FastAPI request object
        category: Filter by category (Health, Dental, Group Life)
        search: Search term for name or ANS code
        enabled: Filter by enabled status ("true", "false", or None for all)
        page: Pagination page number
        username: Authenticated admin username
        db: Database session

    Returns:
        Full page for direct navigation, partial for HTMX requests
    """
    # Build query with filters
    q = db.query(Insurer)

    if category:
        q = q.filter(Insurer.category == category)
    if search:
        search_pattern = f"%{search}%"
        q = q.filter(or_(
            Insurer.name.ilike(search_pattern),
            Insurer.ans_code.contains(search)
        ))
    if enabled is not None and enabled != "":
        enabled_bool = enabled.lower() == "true"
        q = q.filter(Insurer.enabled == enabled_bool)

    # Order by name for consistent display
    q = q.order_by(Insurer.name)

    # Pagination
    per_page = 50
    total = q.count()
    insurers_list = q.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    context = {
        "request": request,
        "username": username,
        "active": "insurers",
        "insurers": insurers_list,
        "category": category,
        "search": search or "",
        "enabled_filter": enabled,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "categories": ["Health", "Dental", "Group Life"],
    }

    # Return partial for HTMX, full page for direct navigation
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("admin/partials/insurer_table.html", context)
    return templates.TemplateResponse("admin/insurers.html", context)


@router.post("/insurers/bulk-enable", response_class=HTMLResponse, name="admin_bulk_enable")
async def admin_bulk_enable(
    request: Request,
    selected: list[str] = Form(default=[]),
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """
    Bulk enable selected insurers.

    Args:
        request: FastAPI request object
        selected: List of ANS codes to enable
        username: Authenticated admin username
        db: Database session

    Returns:
        HTML alert with result message
    """
    if not selected:
        return HTMLResponse(
            '<div class="alert alert-warning alert-dismissible fade show" role="alert">'
            'No insurers selected'
            '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>'
            '</div>'
        )

    updated = db.query(Insurer).filter(Insurer.ans_code.in_(selected)).update(
        {"enabled": True}, synchronize_session=False
    )
    db.commit()

    return HTMLResponse(
        f'<div class="alert alert-success alert-dismissible fade show" role="alert">'
        f'<i class="bi bi-check-circle me-2"></i>Enabled {updated} insurer(s)'
        f'<button type="button" class="btn-close" data-bs-dismiss="alert"></button>'
        f'</div>'
    )


@router.post("/insurers/bulk-disable", response_class=HTMLResponse, name="admin_bulk_disable")
async def admin_bulk_disable(
    request: Request,
    selected: list[str] = Form(default=[]),
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """
    Bulk disable selected insurers.

    Args:
        request: FastAPI request object
        selected: List of ANS codes to disable
        username: Authenticated admin username
        db: Database session

    Returns:
        HTML alert with result message
    """
    if not selected:
        return HTMLResponse(
            '<div class="alert alert-warning alert-dismissible fade show" role="alert">'
            'No insurers selected'
            '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>'
            '</div>'
        )

    updated = db.query(Insurer).filter(Insurer.ans_code.in_(selected)).update(
        {"enabled": False}, synchronize_session=False
    )
    db.commit()

    return HTMLResponse(
        f'<div class="alert alert-warning alert-dismissible fade show" role="alert">'
        f'<i class="bi bi-exclamation-triangle me-2"></i>Disabled {updated} insurer(s)'
        f'<button type="button" class="btn-close" data-bs-dismiss="alert"></button>'
        f'</div>'
    )


# ----- Import Routes -----

@router.get("/import", response_class=HTMLResponse, name="admin_import")
async def import_page(
    request: Request,
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    Import management page.

    Provides drag-and-drop file upload for Excel insurer data.
    Supports ADMN-08 (drag-drop upload) and ADMN-09 (preview with validation).
    """
    return templates.TemplateResponse(
        "admin/import.html",
        {
            "request": request,
            "username": username,
            "active": "import"
        }
    )


@router.post("/import/preview", response_class=HTMLResponse, name="admin_import_preview")
async def admin_import_preview(
    request: Request,
    file: UploadFile = File(...),
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    Parse uploaded Excel file and return preview partial.

    Validates file type, parses contents, stores in session for later commit.
    Returns preview table with validation errors inline.

    Args:
        request: FastAPI request object
        file: Uploaded Excel file
        username: Authenticated admin username

    Returns:
        Rendered preview partial HTML
    """
    cleanup_expired_sessions()

    # Validate file type
    if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
        return templates.TemplateResponse(
            "admin/partials/import_preview.html",
            {"request": request, "error": "Please upload an Excel file (.xlsx or .xls)"}
        )

    # Parse Excel file
    try:
        content = await file.read()
        insurers_data, errors = parse_excel_insurers(BytesIO(content))
    except Exception as e:
        return templates.TemplateResponse(
            "admin/partials/import_preview.html",
            {"request": request, "error": f"Failed to parse file: {str(e)}"}
        )

    # Store in session for commit
    session_id = str(uuid.uuid4())
    import_sessions[session_id] = {
        "data": insurers_data,
        "errors": errors,
        "expires": datetime.now() + timedelta(minutes=30)
    }

    return templates.TemplateResponse(
        "admin/partials/import_preview.html",
        {
            "request": request,
            "session_id": session_id,
            "insurers": insurers_data[:100],  # Preview first 100
            "total": len(insurers_data),
            "errors": errors,
            "has_errors": len(errors) > 0,
        }
    )


@router.post("/import/commit", response_class=HTMLResponse, name="admin_import_commit")
async def admin_import_commit(
    request: Request,
    session_id: str = Form(...),
    mode: str = Form("merge"),
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """
    Commit previewed import data to database.

    Takes session_id from preview, imports data with merge or skip mode.
    Merge mode updates existing records, skip mode ignores them.

    Args:
        request: FastAPI request object
        session_id: Session ID from preview
        mode: Import mode - "merge" updates existing, "skip" ignores existing
        username: Authenticated admin username
        db: Database session

    Returns:
        Success or error message HTML
    """
    # Get session data
    session = import_sessions.get(session_id)
    if not session:
        return HTMLResponse(
            '<div class="alert alert-danger">Session expired. Please upload again.</div>'
        )

    insurers_data = session["data"]
    created, updated, skipped = 0, 0, 0

    try:
        for data in insurers_data:
            existing = db.query(Insurer).filter(Insurer.ans_code == data["ans_code"]).first()
            if existing:
                if mode == "merge":
                    for key, value in data.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    skipped += 1
            else:
                db.add(Insurer(**data))
                created += 1

        db.commit()

        # Clear session
        del import_sessions[session_id]

        return HTMLResponse(f'''
        <div class="alert alert-success">
            <strong>Import complete!</strong><br>
            Created: {created}, Updated: {updated}, Skipped: {skipped}
        </div>
        ''')
    except Exception as e:
        db.rollback()
        return HTMLResponse(f'''
        <div class="alert alert-danger">
            <strong>Import failed:</strong> {str(e)}
        </div>
        ''')


# ----- Other Admin Pages -----

@router.get("/recipients", response_class=HTMLResponse, name="admin_recipients")
async def recipients(
    request: Request,
    username: str = Depends(verify_admin),
    settings: Settings = Depends(get_settings)
) -> HTMLResponse:
    """
    Email recipients management page.

    Shows current recipients per category (TO/CC/BCC) and
    provides reference for environment variable configuration.

    Args:
        request: FastAPI request object
        username: Authenticated admin username
        settings: Application settings

    Returns:
        Rendered recipients HTML page
    """
    categories = ["Health", "Dental", "Group Life"]
    recipients_data = {}

    for cat in categories:
        email_recipients = settings.get_email_recipients(cat)
        recipients_data[cat] = {
            "to": email_recipients.to,
            "cc": email_recipients.cc,
            "bcc": email_recipients.bcc,
            "has_recipients": email_recipients.has_recipients,
        }

    return templates.TemplateResponse(
        "admin/recipients.html",
        {
            "request": request,
            "username": username,
            "active": "recipients",
            "categories": categories,
            "recipients": recipients_data,
        }
    )


@router.get("/schedules", response_class=HTMLResponse, name="admin_schedules")
async def admin_schedules(
    request: Request,
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
) -> HTMLResponse:
    """
    Schedule management page.

    View and modify category run schedules with toggle
    and manual trigger controls.

    Args:
        request: FastAPI request object
        username: Authenticated admin username
        db: Database session
        settings: Application settings

    Returns:
        Rendered schedules HTML page
    """
    scheduler = SchedulerService()
    categories = ["Health", "Dental", "Group Life"]
    schedules_data = []

    for cat in categories:
        schedule_info = scheduler.get_schedule(cat)
        config = settings.get_schedule_config(cat)

        # Get latest run for this category
        latest_run = db.query(Run).filter(
            Run.category == cat
        ).order_by(Run.created_at.desc()).first()

        schedules_data.append({
            "category": cat,
            "cron_expression": config.get("cron", "Not configured"),
            "enabled": not schedule_info.get("paused", True) if schedule_info else False,
            "next_run_time": schedule_info.get("next_run_time") if schedule_info else None,
            "last_run": latest_run,
        })

    return templates.TemplateResponse(
        "admin/schedules.html",
        {
            "request": request,
            "username": username,
            "active": "schedules",
            "schedules": schedules_data,
        }
    )


@router.post("/schedules/{category}/toggle", response_class=HTMLResponse, name="admin_toggle_schedule")
async def admin_toggle_schedule(
    request: Request,
    category: str,
    enabled: bool = Form(...),
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
) -> HTMLResponse:
    """
    Toggle schedule enabled/disabled via HTMX.

    Args:
        request: FastAPI request object
        category: Category name (Health, Dental, Group Life)
        enabled: Target state (True to enable, False to disable)
        username: Authenticated admin username
        db: Database session
        settings: Application settings

    Returns:
        Rendered schedule card partial for HTMX swap
    """
    # Normalize category name
    category_map = {
        "health": "Health",
        "dental": "Dental",
        "group_life": "Group Life",
        "group-life": "Group Life",
        "group life": "Group Life",
    }
    normalized = category_map.get(category.lower(), category)

    scheduler = SchedulerService()

    try:
        if enabled:
            scheduler.resume_job(normalized)
        else:
            scheduler.pause_job(normalized)
    except ValueError:
        # Job may not exist, log but continue
        pass

    # Get updated schedule info
    schedule_info = scheduler.get_schedule(normalized)
    config = settings.get_schedule_config(normalized)
    latest_run = db.query(Run).filter(
        Run.category == normalized
    ).order_by(Run.created_at.desc()).first()

    return templates.TemplateResponse(
        "admin/partials/schedule_card.html",
        {
            "request": request,
            "schedule": {
                "category": normalized,
                "cron_expression": config.get("cron", "Not configured"),
                "enabled": not schedule_info.get("paused", True) if schedule_info else False,
                "next_run_time": schedule_info.get("next_run_time") if schedule_info else None,
                "last_run": latest_run,
            },
            "index": normalized.lower().replace(" ", "-"),
        }
    )


@router.post("/schedules/{category}/trigger", response_class=HTMLResponse, name="admin_trigger_run")
async def admin_trigger_run(
    request: Request,
    category: str,
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    Trigger immediate manual run via HTMX.

    Args:
        request: FastAPI request object
        category: Category name (Health, Dental, Group Life)
        username: Authenticated admin username

    Returns:
        HTML snippet with success/error message
    """
    # Normalize category name
    category_map = {
        "health": "Health",
        "dental": "Dental",
        "group_life": "Group Life",
        "group-life": "Group Life",
        "group life": "Group Life",
    }
    normalized = category_map.get(category.lower(), category)

    scheduler = SchedulerService()

    try:
        await scheduler.trigger_now(normalized)
        return HTMLResponse(
            f'<span class="text-success"><i class="bi bi-check-circle me-1"></i>Run started for {normalized}</span>'
        )
    except Exception as e:
        return HTMLResponse(
            f'<span class="text-danger"><i class="bi bi-exclamation-triangle me-1"></i>Error: {str(e)}</span>'
        )


# ----- Helper Functions: Settings -----

def mask_key(value: str, show_chars: int = 4) -> str:
    """
    Mask API key showing only last N characters.

    Args:
        value: The API key or secret to mask
        show_chars: Number of characters to show at the end

    Returns:
        Masked string with asterisks hiding most of the value
    """
    if not value:
        return "(not configured)"
    if len(value) <= show_chars:
        return "*" * len(value)
    return "*" * (len(value) - show_chars) + value[-show_chars:]


@router.get("/settings", response_class=HTMLResponse, name="admin_settings")
async def settings_page(
    request: Request,
    username: str = Depends(verify_admin),
    settings: Settings = Depends(get_settings)
) -> HTMLResponse:
    """
    Settings page.

    Shows system configuration with read-only display and secure API key masking.
    Addresses ADMN-14 (company branding), ADMN-15 (scraping config), ADMN-16 (masked API keys).

    Args:
        request: FastAPI request object
        username: Authenticated admin username
        settings: Application settings

    Returns:
        Rendered settings page with configuration values
    """
    # Company branding settings (ADMN-14)
    branding = {
        "company_name": settings.company_name,
        "classification_level": "CONFIDENTIAL",
    }

    # Scraping configuration (ADMN-15)
    scraping_config = {
        "batch_size": settings.batch_size,
        "batch_delay_seconds": settings.batch_delay_seconds,
        "max_concurrent_sources": settings.max_concurrent_sources,
        "scrape_timeout_seconds": settings.scrape_timeout_seconds,
        "scrape_max_results": settings.scrape_max_results,
    }

    # API keys - masked and unmasked for reveal toggle (ADMN-16)
    api_keys = {
        "Azure OpenAI Endpoint": {
            "masked": mask_key(settings.azure_openai_endpoint, 10),
            "value": settings.azure_openai_endpoint,
            "configured": bool(settings.azure_openai_endpoint),
        },
        "Azure OpenAI API Key": {
            "masked": mask_key(settings.azure_openai_api_key),
            "value": settings.azure_openai_api_key,
            "configured": bool(settings.azure_openai_api_key),
        },
        "Azure OpenAI Deployment": {
            "masked": settings.azure_openai_deployment,  # Not sensitive
            "value": settings.azure_openai_deployment,
            "configured": bool(settings.azure_openai_deployment),
        },
        "Microsoft Tenant ID": {
            "masked": mask_key(settings.azure_tenant_id, 8),
            "value": settings.azure_tenant_id,
            "configured": bool(settings.azure_tenant_id),
        },
        "Microsoft Client ID": {
            "masked": mask_key(settings.azure_client_id, 8),
            "value": settings.azure_client_id,
            "configured": bool(settings.azure_client_id),
        },
        "Microsoft Client Secret": {
            "masked": mask_key(settings.azure_client_secret),
            "value": settings.azure_client_secret,
            "configured": bool(settings.azure_client_secret),
        },
        "Apify Token": {
            "masked": mask_key(settings.apify_token),
            "value": settings.apify_token,
            "configured": bool(settings.apify_token),
        },
        "Sender Email": {
            "masked": settings.sender_email,  # Email not sensitive
            "value": settings.sender_email,
            "configured": bool(settings.sender_email),
        },
    }

    # Relevance scoring configuration
    relevance_config = {
        "use_ai_relevance_scoring": settings.use_ai_relevance_scoring,
        "relevance_keyword_threshold": settings.relevance_keyword_threshold,
        "relevance_ai_batch_size": settings.relevance_ai_batch_size,
    }

    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "username": username,
            "active": "settings",
            "branding": branding,
            "scraping_config": scraping_config,
            "api_keys": api_keys,
            "relevance_config": relevance_config,
            "use_llm_summary": settings.use_llm_summary,
        }
    )
