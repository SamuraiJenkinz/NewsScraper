"""
Admin interface router for BrasilIntel.

Provides web-based administration with HTTP Basic authentication.
Serves HTML pages using Jinja2 templates.
"""
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.dependencies import get_db, verify_admin
from app.models.insurer import Insurer
from app.services.excel_service import parse_excel_insurers

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
        from io import BytesIO
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
