"""
Run orchestration router for BrasilIntel.

Provides endpoints to execute the end-to-end pipeline:
- Single insurer processing (Phase 2 compatibility)
- Full category processing (Phase 3 scale)
- Critical alerts and PDF delivery (Phase 6)
"""
import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.run import Run
from app.models.news_item import NewsItem
from app.models.insurer import Insurer
from app.services.scraper import ApifyScraperService, ScraperService
from app.services.classifier import ClassificationService
from app.services.emailer import GraphEmailService
from app.services.reporter import ReportService
from app.services.alert_service import CriticalAlertService
from app.schemas.run import RunRead, RunStatus
from app.schemas.news import NewsItemWithClassification
from app.schemas.delivery import DeliveryStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/runs", tags=["Runs"])


class ExecuteRequest(BaseModel):
    """Request model for execute endpoint."""
    category: str = Field(description="Category: Health, Dental, or Group Life")
    insurer_id: Optional[int] = Field(None, description="Specific insurer ID (or all in category if None)")
    send_email: bool = Field(True, description="Whether to send email report")
    max_news_items: int = Field(10, ge=1, le=50, description="Max news items per insurer per source")
    process_all: bool = Field(False, description="Process all insurers in category (Phase 3 mode)")


class ExecuteResponse(BaseModel):
    """Response model for execute endpoint."""
    run_id: int
    status: str
    insurers_processed: int
    items_found: int
    email_sent: bool
    email_status: str = "pending"
    pdf_generated: bool = False
    pdf_size_bytes: int = 0
    critical_alerts_sent: int = 0
    message: str
    errors: list[str] = Field(default_factory=list)


class CategoryExecuteRequest(BaseModel):
    """Request model for category execute endpoint."""
    category: str = Field(description="Category: Health, Dental, or Group Life")
    send_email: bool = Field(True, description="Whether to send email report")
    enabled_only: bool = Field(True, description="Only process enabled insurers")


@router.post("/execute", response_model=ExecuteResponse)
async def execute_run(
    request: ExecuteRequest,
    db: Session = Depends(get_db),
) -> ExecuteResponse:
    """
    Execute a scraping run.

    Supports two modes:
    - Single insurer: Provide insurer_id or process_all=False (uses first enabled)
    - Full category: Set process_all=True to process all insurers in category
    """
    # Create run record
    run = Run(
        category=request.category,
        trigger_type="manual",
        status=RunStatus.RUNNING.value,
        started_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    logger.info(f"Starting run {run.id} for category {request.category}")

    try:
        if request.process_all:
            # Phase 3: Process all insurers in category
            return await _execute_category_run(request, run, db)
        elif request.insurer_id:
            # Specific insurer
            return await _execute_single_insurer_run(request, run, db)
        else:
            # First enabled insurer (Phase 2 behavior)
            return await _execute_single_insurer_run(request, run, db)

    except Exception as e:
        logger.error(f"Run {run.id} failed: {e}")
        run.status = RunStatus.FAILED.value
        run.completed_at = datetime.utcnow()
        run.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


async def _execute_single_insurer_run(
    request: ExecuteRequest,
    run: Run,
    db: Session,
) -> ExecuteResponse:
    """Execute run for a single insurer (Phase 2 mode with all 6 sources)."""
    # Get insurer
    if request.insurer_id:
        insurer = db.query(Insurer).filter(Insurer.id == request.insurer_id).first()
        if not insurer:
            raise HTTPException(status_code=404, detail=f"Insurer {request.insurer_id} not found")
    else:
        insurer = db.query(Insurer).filter(
            Insurer.category == request.category,
            Insurer.enabled == True
        ).first()
        if not insurer:
            raise HTTPException(status_code=404, detail=f"No enabled insurers in {request.category}")

    logger.info(f"Processing insurer: {insurer.name} (ANS: {insurer.ans_code})")

    # Use new ScraperService for single insurer (all 6 sources)
    scraper = ScraperService()
    classifier = ClassificationService()

    # Scrape all sources
    logger.info(f"Scraping news for {insurer.name}...")
    scraped_items = await scraper.scrape_insurer(
        insurer=insurer,
        max_results_per_source=request.max_news_items,
    )

    logger.info(f"Found {len(scraped_items)} news items from {len(scraper.sources)} sources")

    items_stored = 0

    # Classify and store each news item
    for scraped in scraped_items:
        logger.info(f"Classifying: {scraped.title[:100]}...")

        classification = classifier.classify_single_news(
            insurer_name=insurer.name,
            news_title=scraped.title,
            news_description=scraped.description,
        )

        news_item = NewsItem(
            run_id=run.id,
            insurer_id=insurer.id,
            title=scraped.title,
            description=scraped.description,
            source_url=scraped.url,
            source_name=scraped.source,
            published_at=scraped.published_at,
            status=classification.status if classification else None,
            sentiment=classification.sentiment if classification else None,
            summary="\n".join(classification.summary_bullets) if classification else None,
            category_indicators=",".join(classification.category_indicators) if classification and classification.category_indicators else None,
        )
        db.add(news_item)
        items_stored += 1

    db.commit()
    logger.info(f"Stored {items_stored} news items")

    # Check for critical alerts and send immediately
    logger.info("Checking for critical alerts...")
    alert_service = CriticalAlertService()
    alert_result = await alert_service.check_and_send_alert(
        run_id=run.id,
        category=request.category,
        db_session=db,
    )
    critical_alerts_sent = alert_result.get("critical_count", 0)
    if critical_alerts_sent > 0:
        logger.info(f"Critical alert sent for {critical_alerts_sent} insurer(s)")

    # Generate and send report
    delivery_result = await _generate_and_send_report(
        request.category, run.id, db, request.send_email
    )

    # Update run status and delivery tracking
    run.status = RunStatus.COMPLETED.value
    run.completed_at = datetime.utcnow()
    run.insurers_processed = 1
    run.items_found = items_stored
    run.email_status = delivery_result.get("email_status")
    run.email_sent_at = datetime.utcnow() if delivery_result.get("email_sent") else None
    run.email_recipients_count = delivery_result.get("recipients", 0)
    run.email_error_message = delivery_result.get("error_message")
    run.pdf_generated = delivery_result.get("pdf_generated", False)
    run.pdf_size_bytes = delivery_result.get("pdf_size", 0)
    db.commit()

    return ExecuteResponse(
        run_id=run.id,
        status=run.status,
        insurers_processed=1,
        items_found=items_stored,
        email_sent=delivery_result.get("email_sent", False),
        email_status=delivery_result.get("email_status", "pending"),
        pdf_generated=delivery_result.get("pdf_generated", False),
        pdf_size_bytes=delivery_result.get("pdf_size", 0),
        critical_alerts_sent=critical_alerts_sent,
        message=f"Successfully processed {insurer.name} with {items_stored} news items",
    )


async def _execute_category_run(
    request: ExecuteRequest,
    run: Run,
    db: Session,
) -> ExecuteResponse:
    """Execute run for entire category (Phase 3 mode)."""
    logger.info(f"Processing all insurers in category {request.category}")

    scraper = ScraperService()
    classifier = ClassificationService()

    # Process all insurers using batch processor
    progress = await scraper.process_category(
        category=request.category,
        db=db,
        run=run,
        enabled_only=True,
    )

    logger.info(
        f"Batch processing complete: {progress.processed_insurers} insurers, "
        f"{progress.total_items_found} items"
    )

    # Classify stored items (batch classification)
    logger.info("Classifying news items...")
    news_items = db.query(NewsItem).filter(
        NewsItem.run_id == run.id,
        NewsItem.status == None,  # Unclassified items
    ).all()

    for item in news_items:
        insurer = db.query(Insurer).filter(Insurer.id == item.insurer_id).first()
        if not insurer:
            continue

        classification = classifier.classify_single_news(
            insurer_name=insurer.name,
            news_title=item.title,
            news_description=item.description,
        )

        if classification:
            item.status = classification.status
            item.sentiment = classification.sentiment
            item.summary = "\n".join(classification.summary_bullets)
            item.category_indicators = ",".join(classification.category_indicators) if classification.category_indicators else None

    db.commit()
    logger.info(f"Classified {len(news_items)} items")

    # Check for critical alerts and send immediately
    logger.info("Checking for critical alerts...")
    alert_service = CriticalAlertService()
    alert_result = await alert_service.check_and_send_alert(
        run_id=run.id,
        category=request.category,
        db_session=db,
    )
    critical_alerts_sent = alert_result.get("critical_count", 0)
    if critical_alerts_sent > 0:
        logger.info(f"Critical alert sent for {critical_alerts_sent} insurer(s)")

    # Generate and send report
    delivery_result = await _generate_and_send_report(
        request.category, run.id, db, request.send_email
    )

    # Update run status and delivery tracking
    run.status = RunStatus.COMPLETED.value
    run.completed_at = datetime.utcnow()
    run.email_status = delivery_result.get("email_status")
    run.email_sent_at = datetime.utcnow() if delivery_result.get("email_sent") else None
    run.email_recipients_count = delivery_result.get("recipients", 0)
    run.email_error_message = delivery_result.get("error_message")
    run.pdf_generated = delivery_result.get("pdf_generated", False)
    run.pdf_size_bytes = delivery_result.get("pdf_size", 0)
    db.commit()

    return ExecuteResponse(
        run_id=run.id,
        status=run.status,
        insurers_processed=progress.processed_insurers,
        items_found=progress.total_items_found,
        email_sent=delivery_result.get("email_sent", False),
        email_status=delivery_result.get("email_status", "pending"),
        pdf_generated=delivery_result.get("pdf_generated", False),
        pdf_size_bytes=delivery_result.get("pdf_size", 0),
        critical_alerts_sent=critical_alerts_sent,
        message=f"Processed {progress.processed_insurers} insurers with {progress.total_items_found} news items",
        errors=progress.errors[:10],  # Limit errors in response
    )


async def _generate_and_send_report(
    category: str,
    run_id: int,
    db: Session,
    send_email: bool,
) -> dict[str, Any]:
    """Generate professional HTML report with PDF and optionally send via email."""
    logger.info("Generating professional HTML report...")
    report_service = ReportService()

    # Generate professional report with archival
    html_report, archive_path = report_service.generate_professional_report_from_db(
        category=category,
        run_id=run_id,
        db_session=db,
        use_ai_summary=True,
        archive_report=True,
    )

    result = {
        "email_sent": False,
        "email_status": DeliveryStatus.SKIPPED.value if not send_email else DeliveryStatus.PENDING.value,
        "pdf_size": 0,
        "pdf_generated": False,
        "archive_path": str(archive_path) if archive_path else None,
        "recipients": 0,
    }

    if send_email:
        logger.info("Sending email report with PDF attachment...")
        email_service = GraphEmailService()
        report_date = datetime.now().strftime("%Y-%m-%d")

        email_result = await email_service.send_report_email_with_pdf(
            category=category,
            html_content=html_report,
            report_date=report_date,
        )

        result["email_sent"] = email_result.get("status") in ["ok", "sent"]
        result["email_status"] = DeliveryStatus.SENT.value if result["email_sent"] else DeliveryStatus.FAILED.value
        result["pdf_size"] = email_result.get("pdf_size", 0)
        result["pdf_generated"] = email_result.get("pdf_generated", False)
        result["recipients"] = email_result.get("recipients", 0)
        result["error_message"] = email_result.get("message") if not result["email_sent"] else None

        if result["email_sent"]:
            logger.info(f"Email sent successfully with PDF ({result['pdf_size']} bytes)")
        else:
            logger.warning(f"Email not sent: {email_result.get('message')}")

    return result


@router.post("/execute/category", response_model=ExecuteResponse)
async def execute_category_run(
    request: CategoryExecuteRequest,
    db: Session = Depends(get_db),
) -> ExecuteResponse:
    """
    Execute a full category run (Phase 3 dedicated endpoint).

    Processes all insurers in the category using batch processing.
    """
    # Create execute request with process_all=True
    execute_request = ExecuteRequest(
        category=request.category,
        send_email=request.send_email,
        process_all=True,
    )

    # Create run record
    run = Run(
        category=request.category,
        trigger_type="manual",
        status=RunStatus.RUNNING.value,
        started_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        return await _execute_category_run(execute_request, run, db)
    except Exception as e:
        run.status = RunStatus.FAILED.value
        run.completed_at = datetime.utcnow()
        run.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[RunRead])
def list_runs(
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[Run]:
    """List runs with optional filtering."""
    query = db.query(Run)

    if category:
        query = query.filter(Run.category == category)

    if status:
        query = query.filter(Run.status == status)

    runs = query.order_by(Run.started_at.desc()).limit(limit).all()

    return runs


@router.get("/{run_id}", response_model=RunRead)
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
) -> Run:
    """Get a specific run by ID."""
    run = db.query(Run).filter(Run.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return run


@router.get("/{run_id}/news", response_model=list[NewsItemWithClassification])
def get_run_news(
    run_id: int,
    db: Session = Depends(get_db),
) -> list[NewsItem]:
    """Get news items for a specific run."""
    run = db.query(Run).filter(Run.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    news_items = db.query(NewsItem).filter(NewsItem.run_id == run_id).all()

    return news_items


@router.get("/{run_id}/delivery", response_model=dict)
def get_run_delivery_status(
    run_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    Get delivery status for a specific run.

    Returns email delivery details, PDF generation status,
    and critical alert information.
    """
    run = db.query(Run).filter(Run.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return {
        "run_id": run.id,
        "category": run.category,
        "status": run.status,
        "email": {
            "status": run.email_status,
            "sent_at": run.email_sent_at.isoformat() if run.email_sent_at else None,
            "recipients_count": run.email_recipients_count or 0,
            "error_message": run.email_error_message,
        },
        "pdf": {
            "generated": run.pdf_generated or False,
            "size_bytes": run.pdf_size_bytes or 0,
        },
        "critical_alert": {
            "sent": run.critical_alert_sent or False,
            "sent_at": run.critical_alert_sent_at.isoformat() if run.critical_alert_sent_at else None,
            "insurers_count": run.critical_insurers_count or 0,
        }
    }


@router.get("/health/scraper", tags=["Health"])
def scraper_health() -> dict:
    """
    Check health of all scraper components.

    Returns status of:
    - All 6 news sources
    - Batch processor configuration
    - Relevance scorer
    """
    scraper = ScraperService()
    return scraper.health_check()
