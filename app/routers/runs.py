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
from app.models.factiva_config import FactivaConfig
from app.models.equity_ticker import EquityTicker
from app.collectors.factiva import FactivaCollector
from app.services.deduplicator import ArticleDeduplicator
from app.services.insurer_matcher import InsurerMatcher
from app.services.classifier import ClassificationService
from app.services.emailer import GraphEmailService
from app.services.reporter import ReportService
from app.services.alert_service import CriticalAlertService
from app.services.equity_client import EquityPriceClient
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
    Execute a Factiva pipeline run.

    All runs now use batch Factiva collection + insurer matching.
    The insurer_id parameter is deprecated (batch collection doesn't filter by insurer).
    """
    # Deprecation warning for insurer_id
    if request.insurer_id:
        logger.warning(f"insurer_id parameter is deprecated in Factiva mode (was {request.insurer_id})")

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

    logger.info(f"Starting Factiva pipeline run {run.id} for category {request.category}")

    try:
        return await _execute_factiva_pipeline(request, run, db)

    except Exception as e:
        logger.error(f"Run {run.id} failed: {e}")
        run.status = RunStatus.FAILED.value
        run.completed_at = datetime.utcnow()
        run.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


def _enrich_equity_data(
    news_items: list[NewsItem],
    run_id: int,
    db: Session,
) -> dict[int, list[dict]]:
    """
    Enrich news items with equity price data for insurers that have ticker mappings.

    Args:
        news_items: List of NewsItem ORM objects from the current run
        run_id: Pipeline run ID for ApiEvent attribution
        db: Database session

    Returns:
        Dict mapping insurer_id -> list of equity price dicts
        Empty dict if no tickers configured or MMC API unconfigured
    """
    # Load all enabled ticker mappings
    ticker_rows = db.query(EquityTicker).filter(EquityTicker.enabled == True).all()
    if not ticker_rows:
        logger.info("No enabled equity tickers configured - skipping enrichment")
        return {}

    # Build ticker lookup map (case-insensitive entity name -> EquityTicker)
    ticker_map = {row.entity_name.lower(): row for row in ticker_rows}
    logger.info(f"Loaded {len(ticker_map)} enabled equity ticker mappings")

    # Check if equity client is configured
    equity_client = EquityPriceClient()
    if not equity_client.is_configured():
        logger.warning("MMC API not configured - skipping equity enrichment")
        return {}

    # Build set of unique insurer IDs from news items
    insurer_ids = {item.insurer_id for item in news_items if item.insurer_id}
    logger.info(f"Enriching equity data for {len(insurer_ids)} unique insurers")

    # Fetch prices with caching to avoid duplicate API calls
    equity_data = {}
    fetched_prices = {}  # Cache: "TICKER:EXCHANGE" -> price_dict

    for insurer_id in insurer_ids:
        # Query insurer name from DB
        insurer = db.query(Insurer).filter(Insurer.id == insurer_id).first()
        if not insurer:
            continue

        # Case-insensitive match against ticker map
        ticker_row = ticker_map.get(insurer.name.lower())
        if not ticker_row:
            continue

        # Check cache first
        cache_key = f"{ticker_row.ticker}:{ticker_row.exchange}"
        if cache_key in fetched_prices:
            logger.debug(f"Using cached price for {cache_key}")
            equity_data[insurer_id] = [fetched_prices[cache_key]]
            continue

        # Fetch price from MMC API
        price_dict = equity_client.get_price(
            ticker=ticker_row.ticker,
            exchange=ticker_row.exchange,
            run_id=run_id,
        )

        if price_dict:
            fetched_prices[cache_key] = price_dict
            equity_data[insurer_id] = [price_dict]
            logger.info(
                f"Fetched equity price for {insurer.name}: "
                f"{ticker_row.ticker} = {price_dict.get('price')}"
            )

    logger.info(f"Equity enrichment complete: {len(equity_data)} insurers with price data")
    return equity_data


async def _execute_factiva_pipeline(
    request: ExecuteRequest,
    run: Run,
    db: Session,
) -> ExecuteResponse:
    """Execute Factiva batch collection + matching + classification pipeline."""
    # Load FactivaConfig from DB
    factiva_config = db.query(FactivaConfig).filter(FactivaConfig.id == 1).first()
    if not factiva_config or not factiva_config.enabled:
        raise HTTPException(
            status_code=503,
            detail="Factiva collection is disabled or not configured"
        )

    query_params = {
        "industry_codes": factiva_config.industry_codes,
        "company_codes": factiva_config.company_codes,
        "keywords": factiva_config.keywords,
        "page_size": factiva_config.page_size,
    }

    # Collect articles from Factiva
    collector = FactivaCollector()
    if not collector.is_configured():
        raise HTTPException(
            status_code=503,
            detail="MMC API key not configured — cannot collect from Factiva"
        )

    logger.info(f"Collecting articles from Factiva for category {request.category}...")
    articles = collector.collect(query_params, run_id=run.id)
    logger.info(f"Factiva returned {len(articles)} articles")

    # URL deduplication (fast inline check before semantic dedup)
    seen_urls = set()
    url_deduped = []
    for article in articles:
        url = article.get("source_url", "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        url_deduped.append(article)

    logger.info(f"URL dedup: {len(articles)} -> {len(url_deduped)}")
    articles = url_deduped

    # Semantic deduplication
    logger.info("Running semantic deduplication...")
    deduplicator = ArticleDeduplicator()
    articles = deduplicator.deduplicate(articles)
    logger.info(f"After dedup: {len(articles)} unique articles")

    # Load insurers for matching (filter by category)
    insurers = db.query(Insurer).filter(
        Insurer.enabled == True,
        Insurer.category == request.category
    ).all()
    logger.info(f"Loaded {len(insurers)} enabled insurers for category {request.category}")

    # Ensure "General News" sentinel insurer exists for unmatched articles
    general_insurer = db.query(Insurer).filter(Insurer.ans_code == "000000").first()
    if not general_insurer:
        logger.info("Creating 'Noticias Gerais' sentinel insurer for unmatched articles")
        general_insurer = Insurer(
            ans_code="000000",
            name="Noticias Gerais",
            category=request.category,
            enabled=True,
            search_terms=None,
        )
        db.add(general_insurer)
        db.commit()
        db.refresh(general_insurer)

    # Match articles to insurers
    logger.info("Matching articles to insurers...")
    matcher = InsurerMatcher()
    match_results = matcher.match_batch(articles, insurers, run_id=run.id)

    # Store matched articles + classify
    logger.info("Storing and classifying articles...")
    classifier = ClassificationService()
    items_stored = 0
    insurers_with_news = set()

    for article, match in zip(articles, match_results):
        # Determine insurer IDs — use sentinel for unmatched
        target_ids = match.insurer_ids if match.insurer_ids else [general_insurer.id]

        # Cap at 3 insurers per article to prevent runaway duplication
        target_ids = target_ids[:3]

        for insurer_id in target_ids:
            insurer = db.query(Insurer).filter(Insurer.id == insurer_id).first()
            insurer_name = insurer.name if insurer else "Unknown"

            # Classify
            classification = classifier.classify_single_news(
                insurer_name=insurer_name,
                news_title=article["title"],
                news_description=article.get("description"),
            )

            # Create NewsItem
            news_item = NewsItem(
                run_id=run.id,
                insurer_id=insurer_id,
                title=article["title"],
                description=article.get("description"),
                source_url=article.get("source_url"),
                source_name=article.get("source_name", "Factiva"),
                published_at=article.get("published_at"),
                status=classification.status if classification else None,
                sentiment=classification.sentiment if classification else None,
                summary="\n".join(classification.summary_bullets) if classification else None,
                category_indicators=",".join(classification.category_indicators) if classification and classification.category_indicators else None,
            )
            db.add(news_item)
            items_stored += 1
            insurers_with_news.add(insurer_id)

    db.commit()
    logger.info(f"Stored {items_stored} news items for {len(insurers_with_news)} insurers")

    # Equity price enrichment
    logger.info("Enriching with equity price data...")
    all_run_items = db.query(NewsItem).filter(NewsItem.run_id == run.id).all()
    equity_data = _enrich_equity_data(all_run_items, run.id, db)
    logger.info(f"Equity enrichment: {len(equity_data)} insurers with price data")

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
        request.category, run.id, db, request.send_email, equity_data
    )

    # Update run status and delivery tracking
    run.status = RunStatus.COMPLETED.value
    run.completed_at = datetime.utcnow()
    run.insurers_processed = len(insurers_with_news)
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
        insurers_processed=len(insurers_with_news),
        items_found=items_stored,
        email_sent=delivery_result.get("email_sent", False),
        email_status=delivery_result.get("email_status", "pending"),
        pdf_generated=delivery_result.get("pdf_generated", False),
        pdf_size_bytes=delivery_result.get("pdf_size", 0),
        critical_alerts_sent=critical_alerts_sent,
        message=f"Factiva pipeline processed {len(insurers_with_news)} insurers with {items_stored} news items",
    )


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
    equity_data: dict[int, list[dict]] = None,
) -> dict[str, Any]:
    """Generate professional HTML report with PDF and optionally send via email."""
    logger.info("Generating professional HTML report...")
    report_service = ReportService()

    # Pass equity_data to reporter (will be used in Plan 12-03)
    if equity_data is None:
        equity_data = {}

    # Generate professional report with archival
    html_report, archive_path = report_service.generate_professional_report_from_db(
        category=category,
        run_id=run_id,
        db_session=db,
        use_ai_summary=True,
        archive_report=True,
        equity_data=equity_data,
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
    Execute a full category run using Factiva batch collection.

    Processes all insurers in the category using the Factiva pipeline.
    """
    # Create execute request
    execute_request = ExecuteRequest(
        category=request.category,
        send_email=request.send_email,
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
        return await _execute_factiva_pipeline(execute_request, run, db)
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
    trigger_type: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[Run]:
    """
    List runs with optional filtering.

    Filters:
    - category: Health, Dental, or Group Life
    - status: pending, running, completed, failed
    - trigger_type: scheduled or manual
    """
    query = db.query(Run)

    if category:
        query = query.filter(Run.category == category)

    if status:
        query = query.filter(Run.status == status)

    if trigger_type:
        query = query.filter(Run.trigger_type == trigger_type)

    runs = query.order_by(Run.started_at.desc()).limit(limit).all()

    return runs


@router.get("/latest", response_model=dict)
def get_latest_runs(
    db: Session = Depends(get_db),
) -> dict:
    """
    Get the latest run for each category.

    Useful for dashboard display showing last run status per category.
    """
    categories = ["Health", "Dental", "Group Life"]
    latest = {}

    for category in categories:
        run = db.query(Run).filter(
            Run.category == category
        ).order_by(Run.started_at.desc()).first()

        if run:
            latest[category] = {
                "id": run.id,
                "status": run.status,
                "trigger_type": run.trigger_type,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "items_found": run.items_found,
                "email_status": run.email_status,
            }
        else:
            latest[category] = None

    return {"latest_runs": latest}


@router.get("/stats", response_model=dict)
def get_run_stats(
    days: int = 7,
    db: Session = Depends(get_db),
) -> dict:
    """
    Get run statistics for the past N days.

    Returns counts by status, trigger_type, and category.
    """
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(days=days)

    runs = db.query(Run).filter(Run.started_at >= cutoff).all()

    stats = {
        "period_days": days,
        "total_runs": len(runs),
        "by_status": {},
        "by_trigger_type": {},
        "by_category": {},
    }

    for run in runs:
        # Count by status
        stats["by_status"][run.status] = stats["by_status"].get(run.status, 0) + 1
        # Count by trigger_type
        stats["by_trigger_type"][run.trigger_type] = stats["by_trigger_type"].get(run.trigger_type, 0) + 1
        # Count by category
        stats["by_category"][run.category] = stats["by_category"].get(run.category, 0) + 1

    return stats


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
    """Check health of Factiva news collection."""
    collector = FactivaCollector()
    return {
        "status": "ok" if collector.is_configured() else "unconfigured",
        "source": "factiva",
        "mmc_api_configured": collector.is_configured(),
    }
