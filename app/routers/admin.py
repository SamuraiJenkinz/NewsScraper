"""
Admin interface router for BrasilIntel.

Provides web-based administration with HTTP Basic authentication.
Serves HTML pages using Jinja2 templates.
"""
import uuid
from datetime import datetime, timedelta
from io import BytesIO

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import get_settings, Settings
from app.dependencies import (
    get_db, verify_admin, verify_credentials,
    create_session_token, invalidate_session_token
)
from app.models.insurer import Insurer
from app.models.run import Run
from app.models.equity_ticker import EquityTicker
from app.models.api_event import ApiEvent, ApiEventType
from app.models.factiva_config import FactivaConfig
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


def _update_env_var(env_content: str, var_name: str, value: str) -> str:
    """Replace or append an environment variable in .env file content."""
    import re
    pattern = re.compile(f"^{re.escape(var_name)}=.*$", re.MULTILINE)
    if pattern.search(env_content):
        return pattern.sub(f"{var_name}={value}", env_content)
    else:
        if env_content and not env_content.endswith("\n"):
            env_content += "\n"
        return env_content + f"{var_name}={value}\n"


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


# ----- Login/Logout Routes -----

@router.get("/login", response_class=HTMLResponse, name="admin_login")
async def login_page(
    request: Request,
    error: str = None
) -> HTMLResponse:
    """
    Login page for admin dashboard.

    Shows HTML form for username/password entry.
    No authentication required to view this page.
    """
    return templates.TemplateResponse(
        "admin/login.html",
        {
            "request": request,
            "error": error,
            "username": ""
        }
    )


@router.post("/login", response_class=HTMLResponse, name="admin_login_post")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    settings: Settings = Depends(get_settings)
) -> RedirectResponse:
    """
    Handle login form submission.

    Validates credentials and creates session cookie on success.
    Redirects back to login with error on failure.
    """
    if verify_credentials(username, password, settings):
        # Create session and set cookie
        token = create_session_token(username)
        response = RedirectResponse(url="/admin/", status_code=303)
        response.set_cookie(
            key="brasilintel_session",
            value=token,
            httponly=True,
            max_age=86400,  # 24 hours
            samesite="lax"
        )
        return response

    # Invalid credentials - show error
    return templates.TemplateResponse(
        "admin/login.html",
        {
            "request": request,
            "error": "Invalid username or password",
            "username": username
        },
        status_code=401
    )


@router.get("/logout", name="admin_logout")
async def logout(
    request: Request,
    session_token: str = Cookie(None, alias="brasilintel_session")
) -> RedirectResponse:
    """
    Logout and clear session.

    Invalidates session token and clears cookie.
    Redirects to login page.
    """
    if session_token:
        invalidate_session_token(session_token)

    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie("brasilintel_session")
    return response


# ----- Dashboard Routes -----

def _get_enterprise_api_status(db: Session) -> list[dict]:
    """
    Get enterprise API health status for dashboard panel.

    Queries ApiEvent table for each enterprise API (auth, news, equity)
    to find most recent successful and failed events.

    Args:
        db: Database session

    Returns:
        List of dicts with api_name, display_name, status, last_success, last_failure, reason
    """
    FALLBACK_TYPES = {
        ApiEventType.NEWS_FALLBACK,
        ApiEventType.EQUITY_FALLBACK,
        ApiEventType.EMAIL_FALLBACK,
    }

    api_configs = [
        {"api_name": "auth", "display_name": "Authentication"},
        {"api_name": "news", "display_name": "News (Factiva)"},
        {"api_name": "equity", "display_name": "Equity Prices"},
    ]

    results = []
    for config in api_configs:
        api_name = config["api_name"]
        display_name = config["display_name"]

        # Get most recent successful event
        last_success = db.query(ApiEvent).filter(
            ApiEvent.api_name == api_name,
            ApiEvent.success == True
        ).order_by(ApiEvent.timestamp.desc()).first()

        # Get most recent failed event
        last_failure = db.query(ApiEvent).filter(
            ApiEvent.api_name == api_name,
            ApiEvent.success == False
        ).order_by(ApiEvent.timestamp.desc()).first()

        # Determine overall status from most recent event
        status = "unknown"
        reason = None

        # Get the absolute most recent event (success or failure)
        most_recent = db.query(ApiEvent).filter(
            ApiEvent.api_name == api_name
        ).order_by(ApiEvent.timestamp.desc()).first()

        if most_recent:
            if most_recent.success:
                status = "healthy"
            else:
                # Failed - check if it's a fallback
                if most_recent.event_type in FALLBACK_TYPES:
                    status = "degraded"
                else:
                    status = "offline"
                reason = most_recent.detail[:100] if most_recent.detail else None

        results.append({
            "api_name": api_name,
            "display_name": display_name,
            "status": status,
            "last_success": format_datetime(last_success.timestamp) if last_success else None,
            "last_failure": format_datetime(last_failure.timestamp) if last_failure else None,
            "reason": reason,
        })

    return results


def _get_fallback_events(db: Session, limit: int = 20) -> list[dict]:
    """
    Get recent fallback/failure events for dashboard log.

    Queries ApiEvent for fallback and critical failure events.

    Args:
        db: Database session
        limit: Maximum number of events to return

    Returns:
        List of dicts with timestamp, api_name, event_type (human-readable), reason
    """
    FALLBACK_EVENT_TYPES = [
        ApiEventType.NEWS_FALLBACK,
        ApiEventType.EQUITY_FALLBACK,
        ApiEventType.EMAIL_FALLBACK,
        ApiEventType.TOKEN_FAILED,
    ]

    EVENT_LABELS = {
        ApiEventType.NEWS_FALLBACK: "News Fallback",
        ApiEventType.EQUITY_FALLBACK: "Equity Fallback",
        ApiEventType.EMAIL_FALLBACK: "Email Fallback",
        ApiEventType.TOKEN_FAILED: "Token Failed",
    }

    events = db.query(ApiEvent).filter(
        ApiEvent.event_type.in_(FALLBACK_EVENT_TYPES)
    ).order_by(ApiEvent.timestamp.desc()).limit(limit).all()

    results = []
    for event in events:
        results.append({
            "timestamp": format_datetime(event.timestamp),
            "api_name": event.api_name,
            "event_type": EVENT_LABELS.get(event.event_type, str(event.event_type)),
            "reason": event.detail[:100] if event.detail else None,
        })

    return results


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

    # Get enterprise API status and fallback events
    enterprise_status = _get_enterprise_api_status(db)
    fallback_events = _get_fallback_events(db)

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
            "enterprise_status": enterprise_status,
            "fallback_events": fallback_events,
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
        ).order_by(Run.started_at.desc()).first()

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
    ).order_by(Run.started_at.desc()).first()

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


# ----- Equity Ticker Routes -----

@router.get("/equity", response_class=HTMLResponse, name="admin_equity")
async def equity(
    request: Request,
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """
    Equity ticker mapping management page.

    Lists all EquityTicker rows with add/edit/delete capability.
    Used by admin to configure entity-to-ticker mappings for equity price enrichment.

    Args:
        request: FastAPI request object
        username: Authenticated admin username
        db: Database session

    Returns:
        HTML equity ticker management page
    """
    tickers = db.query(EquityTicker).order_by(EquityTicker.entity_name).all()

    # Read optional flash messages from query params
    success = request.query_params.get("success")
    error = request.query_params.get("error")

    return templates.TemplateResponse(
        "admin/equity.html",
        {
            "request": request,
            "tickers": tickers,
            "active": "equity",
            "username": username,
            "success": success,
            "error": error,
        }
    )


@router.post("/equity", response_class=HTMLResponse, name="admin_equity_add")
async def equity_add(
    request: Request,
    entity_name: str = Form(""),
    ticker: str = Form(""),
    exchange: str = Form("BVMF"),
    enabled: str = Form("off"),
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db)
) -> RedirectResponse:
    """
    Add a new entity-to-ticker mapping.

    Validates entity_name is non-empty and unique (case-insensitive).
    Redirects to /admin/equity with success or error flash message.

    Args:
        request: FastAPI request object
        entity_name: Company name as extracted by AI classifier
        ticker: Exchange ticker symbol (e.g. "BBSE3")
        exchange: Exchange code (e.g. "BVMF")
        enabled: Checkbox value ("on", "true", "1", "yes" = True)
        username: Authenticated admin username
        db: Database session

    Returns:
        Redirect to equity list with flash message
    """
    entity_name = entity_name.strip()
    ticker_symbol = ticker.strip().upper()
    exchange_code = exchange.strip().upper() or "BVMF"
    is_enabled = enabled.lower() in ("on", "true", "1", "yes")

    # Validate required fields
    if not entity_name:
        return RedirectResponse(
            url="/admin/equity?error=Entity+name+is+required",
            status_code=303,
        )
    if not ticker_symbol:
        return RedirectResponse(
            url="/admin/equity?error=Ticker+symbol+is+required",
            status_code=303,
        )

    # Check uniqueness — case-insensitive match
    existing = db.query(EquityTicker).filter(
        func.lower(EquityTicker.entity_name) == entity_name.lower()
    ).first()
    if existing:
        return RedirectResponse(
            url=f"/admin/equity?error=A+mapping+for+'{entity_name}'+already+exists",
            status_code=303,
        )

    new_ticker = EquityTicker(
        entity_name=entity_name,
        ticker=ticker_symbol,
        exchange=exchange_code,
        enabled=is_enabled,
        updated_at=datetime.utcnow(),
        updated_by=username,
    )
    db.add(new_ticker)
    db.commit()

    return RedirectResponse(
        url=f"/admin/equity?success=Mapping+for+'{entity_name}'+added+successfully",
        status_code=303,
    )


@router.get("/equity/edit/{ticker_id}", response_class=HTMLResponse, name="admin_equity_edit")
async def equity_edit(
    request: Request,
    ticker_id: int,
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """
    Render edit form for a single equity ticker mapping.

    Args:
        request: FastAPI request object
        ticker_id: EquityTicker row id to edit
        username: Authenticated admin username
        db: Database session

    Returns:
        HTML edit page with fields pre-populated
    """
    from fastapi import HTTPException

    ticker_row = db.query(EquityTicker).filter(EquityTicker.id == ticker_id).first()
    if not ticker_row:
        raise HTTPException(status_code=404, detail="Ticker mapping not found")

    # Get all tickers for the list view
    tickers = db.query(EquityTicker).order_by(EquityTicker.entity_name).all()

    return templates.TemplateResponse(
        "admin/equity.html",
        {
            "request": request,
            "tickers": tickers,
            "edit_ticker": ticker_row,
            "active": "equity",
            "username": username,
        }
    )


@router.post("/equity/edit/{ticker_id}", response_class=HTMLResponse, name="admin_equity_update")
async def equity_update(
    request: Request,
    ticker_id: int,
    entity_name: str = Form(""),
    ticker: str = Form(""),
    exchange: str = Form("BVMF"),
    enabled: str = Form("off"),
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db)
) -> RedirectResponse:
    """
    Update an equity ticker mapping.

    Validates entity_name uniqueness (excluding current row).
    Redirects to /admin/equity with success flash message.

    Args:
        request: FastAPI request object
        ticker_id: EquityTicker row id to update
        entity_name: Updated company entity name
        ticker: Updated ticker symbol
        exchange: Updated exchange code
        enabled: Checkbox value
        username: Authenticated admin username
        db: Database session

    Returns:
        Redirect to equity list with flash message
    """
    from fastapi import HTTPException

    ticker_row = db.query(EquityTicker).filter(EquityTicker.id == ticker_id).first()
    if not ticker_row:
        raise HTTPException(status_code=404, detail="Ticker mapping not found")

    entity_name = entity_name.strip()
    ticker_symbol = ticker.strip().upper()
    exchange_code = exchange.strip().upper() or "BVMF"
    is_enabled = enabled.lower() in ("on", "true", "1", "yes")

    # Validate required fields
    if not entity_name:
        return RedirectResponse(
            url="/admin/equity?error=Entity+name+is+required",
            status_code=303,
        )
    if not ticker_symbol:
        return RedirectResponse(
            url="/admin/equity?error=Ticker+symbol+is+required",
            status_code=303,
        )

    # Check uniqueness — case-insensitive match excluding current row
    existing = db.query(EquityTicker).filter(
        func.lower(EquityTicker.entity_name) == entity_name.lower(),
        EquityTicker.id != ticker_id
    ).first()
    if existing:
        return RedirectResponse(
            url=f"/admin/equity?error=A+mapping+for+'{entity_name}'+already+exists",
            status_code=303,
        )

    # Update fields
    ticker_row.entity_name = entity_name
    ticker_row.ticker = ticker_symbol
    ticker_row.exchange = exchange_code
    ticker_row.enabled = is_enabled
    ticker_row.updated_at = datetime.utcnow()
    ticker_row.updated_by = username

    db.commit()

    return RedirectResponse(
        url=f"/admin/equity?success=Mapping+for+'{entity_name}'+updated",
        status_code=303,
    )


@router.post("/equity/delete/{ticker_id}", response_class=HTMLResponse, name="admin_equity_delete")
async def equity_delete(
    request: Request,
    ticker_id: int,
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db)
) -> RedirectResponse:
    """
    Delete an equity ticker mapping by id.

    Redirects to /admin/equity with success flash message.

    Args:
        request: FastAPI request object
        ticker_id: EquityTicker row id to delete
        username: Authenticated admin username
        db: Database session

    Returns:
        Redirect to equity list with flash message
    """
    from fastapi import HTTPException

    ticker_row = db.query(EquityTicker).filter(EquityTicker.id == ticker_id).first()
    if not ticker_row:
        raise HTTPException(status_code=404, detail="Ticker mapping not found")

    entity_name = ticker_row.entity_name
    db.delete(ticker_row)
    db.commit()

    return RedirectResponse(
        url=f"/admin/equity?success=Mapping+for+'{entity_name}'+deleted",
        status_code=303,
    )


@router.post("/equity/seed", response_class=HTMLResponse, name="admin_equity_seed")
async def equity_seed(
    request: Request,
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db)
) -> RedirectResponse:
    """
    Seed default Brazilian insurer tickers.

    Inserts 5 major Brazilian insurer tickers (only if they don't already exist).
    Redirects to /admin/equity with success message showing how many were added.

    Args:
        request: FastAPI request object
        username: Authenticated admin username
        db: Database session

    Returns:
        Redirect to equity list with count of seeded tickers
    """
    default_tickers = [
        {"entity_name": "BB Seguridade", "ticker": "BBSE3", "exchange": "BVMF"},
        {"entity_name": "SulAmerica", "ticker": "SULA11", "exchange": "BVMF"},
        {"entity_name": "Porto Seguro", "ticker": "PSSA3", "exchange": "BVMF"},
        {"entity_name": "IRB Brasil", "ticker": "IRBR3", "exchange": "BVMF"},
        {"entity_name": "Caixa Seguridade", "ticker": "CXSE3", "exchange": "BVMF"},
    ]

    added_count = 0
    for default in default_tickers:
        # Check if already exists (case-insensitive)
        existing = db.query(EquityTicker).filter(
            func.lower(EquityTicker.entity_name) == default["entity_name"].lower()
        ).first()

        if not existing:
            new_ticker = EquityTicker(
                entity_name=default["entity_name"],
                ticker=default["ticker"],
                exchange=default["exchange"],
                enabled=True,
                updated_at=datetime.utcnow(),
                updated_by=username,
            )
            db.add(new_ticker)
            added_count += 1

    db.commit()

    return RedirectResponse(
        url=f"/admin/equity?success={added_count}+default+ticker(s)+seeded",
        status_code=303,
    )


# ----- Enterprise Config Routes -----

@router.get("/enterprise-config", response_class=HTMLResponse, name="admin_enterprise_config")
async def enterprise_config(
    request: Request,
    username: str = Depends(verify_admin),
    settings: Settings = Depends(get_settings)
) -> HTMLResponse:
    """
    Enterprise configuration page for MMC Core API credentials.

    Allows admin to configure MMC API credentials (base URL, client ID, client secret,
    API key, sender email) through web UI without editing .env files directly.

    Args:
        request: FastAPI request object
        username: Authenticated admin username
        settings: Application settings

    Returns:
        Rendered enterprise config page with masked secrets
    """
    # Build config display dict with boolean flags for secrets
    config_display = {
        "mmc_api_base_url": settings.mmc_api_base_url,
        "mmc_api_client_id": settings.mmc_api_client_id,
        "mmc_api_client_secret_set": bool(settings.mmc_api_client_secret),
        "mmc_api_key_set": bool(settings.mmc_api_key),
        "mmc_sender_email": settings.mmc_sender_email,
    }

    return templates.TemplateResponse(
        "admin/enterprise_config.html",
        {
            "request": request,
            "username": username,
            "active": "enterprise_config",
            "config": config_display,
        }
    )


@router.post("/enterprise-config", response_class=HTMLResponse, name="admin_enterprise_config_post")
async def enterprise_config_save(
    request: Request,
    mmc_api_base_url: str = Form(""),
    mmc_api_client_id: str = Form(""),
    mmc_api_client_secret: str = Form(""),
    mmc_api_key: str = Form(""),
    mmc_sender_email: str = Form(""),
    username: str = Depends(verify_admin),
    settings: Settings = Depends(get_settings)
) -> HTMLResponse:
    """
    Save enterprise configuration credentials to .env file.

    Updates MMC Core API credentials. Non-secret fields always updated.
    Secret fields only updated if non-blank (to preserve existing secrets).
    Clears settings cache after save so pipeline picks up new values.

    Args:
        request: FastAPI request object
        mmc_api_base_url: MMC Core API base URL
        mmc_api_client_id: OAuth2 client ID
        mmc_api_client_secret: OAuth2 client secret (only updated if non-blank)
        mmc_api_key: X-Api-Key header value (only updated if non-blank)
        mmc_sender_email: Enterprise sender email address
        username: Authenticated admin username
        settings: Application settings

    Returns:
        Re-rendered page with success message
    """
    from pathlib import Path

    # Read current .env content
    env_path = Path(".env")
    if env_path.exists():
        env_content = env_path.read_text(encoding="utf-8")
    else:
        env_content = ""

    # Always update non-secret fields
    env_content = _update_env_var(env_content, "MMC_API_BASE_URL", mmc_api_base_url.strip())
    env_content = _update_env_var(env_content, "MMC_API_CLIENT_ID", mmc_api_client_id.strip())
    env_content = _update_env_var(env_content, "MMC_SENDER_EMAIL", mmc_sender_email.strip())

    # Only update secrets if non-blank (preserve existing if blank)
    if mmc_api_client_secret.strip():
        env_content = _update_env_var(env_content, "MMC_API_CLIENT_SECRET", mmc_api_client_secret.strip())

    if mmc_api_key.strip():
        env_content = _update_env_var(env_content, "MMC_API_KEY", mmc_api_key.strip())

    # Write updated .env
    env_path.write_text(env_content, encoding="utf-8")

    # Clear settings cache so pipeline reads fresh values
    get_settings.cache_clear()

    # Re-render with success message
    settings_refreshed = get_settings()
    config_display = {
        "mmc_api_base_url": settings_refreshed.mmc_api_base_url,
        "mmc_api_client_id": settings_refreshed.mmc_api_client_id,
        "mmc_api_client_secret_set": bool(settings_refreshed.mmc_api_client_secret),
        "mmc_api_key_set": bool(settings_refreshed.mmc_api_key),
        "mmc_sender_email": settings_refreshed.mmc_sender_email,
    }

    return templates.TemplateResponse(
        "admin/enterprise_config.html",
        {
            "request": request,
            "username": username,
            "active": "enterprise_config",
            "config": config_display,
            "success": "Enterprise configuration saved successfully. Changes will take effect on the next pipeline run.",
        }
    )


# ----- Factiva Config Routes -----

@router.get("/factiva", response_class=HTMLResponse, name="admin_factiva")
async def factiva_config(
    request: Request,
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """
    Factiva configuration page for query parameters.

    Allows admin to configure Factiva search parameters (industry codes,
    company codes, keywords, page size, date range) through web UI.

    Args:
        request: FastAPI request object
        username: Authenticated admin username
        db: Database session

    Returns:
        Rendered Factiva config page with current settings
    """
    # Query FactivaConfig row id=1 (create if missing)
    factiva_config = db.query(FactivaConfig).filter(FactivaConfig.id == 1).first()
    if not factiva_config:
        # Create default config row
        factiva_config = FactivaConfig(
            id=1,
            industry_codes="i82,i8200,i82001,i82002,i82003",
            company_codes="",
            keywords="seguro,seguradora,resseguro,resseguradora,previdência,saúde suplementar,plano de saúde,apólice,sinistro",
            page_size=50,
            date_range_hours=48,
            enabled=True,
        )
        db.add(factiva_config)
        db.commit()
        db.refresh(factiva_config)

    return templates.TemplateResponse(
        "admin/factiva.html",
        {
            "request": request,
            "username": username,
            "active": "factiva",
            "config": factiva_config,
        }
    )


@router.post("/factiva", response_class=HTMLResponse, name="admin_factiva_post")
async def factiva_config_save(
    request: Request,
    industry_codes: str = Form(""),
    company_codes: str = Form(""),
    keywords: str = Form(""),
    page_size: int = Form(25),
    date_range_hours: int = Form(48),
    enabled_hidden: str = Form("false"),
    enabled: str = Form("off"),
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """
    Save Factiva configuration parameters to database.

    Updates FactivaConfig row id=1 with new query parameters. Changes take
    effect on next pipeline run.

    Args:
        request: FastAPI request object
        industry_codes: Comma-separated Factiva industry codes
        company_codes: Comma-separated Factiva company codes
        keywords: Comma-separated search keywords
        page_size: Results per page (10, 25, 50, or 100)
        date_range_hours: Lookback window (24, 48, or 168)
        enabled_hidden: Hidden field default value
        enabled: Checkbox value (overrides hidden if present)
        username: Authenticated admin username
        db: Database session

    Returns:
        Re-rendered page with success message
    """
    # Query or create FactivaConfig row id=1
    factiva_config = db.query(FactivaConfig).filter(FactivaConfig.id == 1).first()
    if not factiva_config:
        factiva_config = FactivaConfig(id=1)
        db.add(factiva_config)

    # Clean comma-separated inputs
    factiva_config.industry_codes = ",".join(c.strip() for c in industry_codes.split(",") if c.strip())
    factiva_config.company_codes = ",".join(c.strip() for c in company_codes.split(",") if c.strip())
    factiva_config.keywords = ",".join(k.strip() for k in keywords.split(",") if k.strip())

    # Validate page_size
    valid_page_sizes = {10, 25, 50, 100}
    factiva_config.page_size = page_size if page_size in valid_page_sizes else 25

    # Validate date_range_hours
    valid_date_ranges = {24, 48, 168}
    factiva_config.date_range_hours = date_range_hours if date_range_hours in valid_date_ranges else 48

    # Handle enabled checkbox with hidden field pattern
    factiva_config.enabled = enabled.lower() in ("on", "true", "1", "yes")

    # Update audit fields
    factiva_config.updated_at = datetime.utcnow()
    factiva_config.updated_by = username

    db.commit()
    db.refresh(factiva_config)

    return templates.TemplateResponse(
        "admin/factiva.html",
        {
            "request": request,
            "username": username,
            "active": "factiva",
            "config": factiva_config,
            "success": "Factiva configuration saved successfully. Changes will take effect on the next pipeline run.",
        }
    )
