# Project State

## Project Reference
See: .planning/PROJECT.md (updated 2026-02-04)

**Core value:** Senior management at Marsh Brasil receives actionable intelligence reports on their monitored insurers daily, with zero manual effort.
**Current focus:** Phase 3 - News Collection Scale

## Current Position
Phase: 3 of 8 (News Collection Scale)
Plan: 3 of 6
Status: In progress
Progress: [███░░░░░░░] 30% (2.5/8 phases complete)
Last activity: 2026-02-04 - Completed 03-03-PLAN.md

## Performance Metrics

**Velocity:**
- Total plans completed: 16
- Average duration: ~4.7 minutes
- Total execution time: ~1.28 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 4 | ~26 min | ~6.5 min |
| 02-vertical-slice-validation | 9 | ~42 min | ~4.7 min |
| 03-news-collection-scale | 3 | ~10 min | ~3.3 min |

**Recent Trend:**
- Last 5 plans: 02-08 (~2 min), 02-09 (~20 min), 03-01 (~2 min), 03-02 (~4 min), 03-03 (~4 min)
- Trend: Wave 2 plans (03-02, 03-03) executed in parallel for news sources

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Python 3.11+ + FastAPI + SQLite stack chosen for Azure integration and Windows compatibility
- Windows Scheduled Task for production deployment (simpler than Windows Service)
- Apify SDK for web scraping (proven infrastructure with rate limiting)
- 3 separate scheduled jobs for staggered runs and independent failures
- 8-phase roadmap with vertical slice validation before horizontal scaling
- Search endpoint returns {total, results} structure for pagination-aware responses (01-02)
- PATCH endpoint uses model_dump(exclude_unset=True) for partial updates (01-02)
- IntegrityError caught and rolled back before raising HTTPException (01-02)
- In-memory session storage for MVP import preview (30-minute TTL) (01-03)
- Merge mode default for import - updates existing records (01-03)
- Portuguese category normalization auto-mapped to English standard (01-03)
- Export column names match import format for round-trip compatibility (01-04)
- StreamingResponse for efficient large file downloads (01-04)
- Run model tracks category for per-category scraping runs (02-01)
- NewsItem classification fields nullable for two-phase scrape→classify workflow (02-01)
- Run trigger_type enum supports scheduled and manual execution tracking (02-01)
- pydantic-settings for centralized configuration with validation (02-02)
- OR queries combine insurer name and ANS code for better search accuracy (02-03)
- ScrapedNewsItem dataclass for flexible Apify result field mapping (02-03)
- Non-blocking error handling returns empty lists on scraper failures (02-03)
- Azure OpenAI structured outputs with Pydantic response_format for guaranteed schema conformance (02-04)
- Portuguese system prompts for consistent Portuguese-language summarization output (02-04)
- temperature=0 for deterministic classification behavior (02-04)
- Fallback classification returns Monitor status when LLM unavailable (02-04)
- Token limit protection: aggregate classification limited to 10 news items (02-04)
- Microsoft Graph REST API instead of SDK to avoid Windows long path issues (02-05)
- Daemon authentication (ClientSecretCredential) for automated email without user interaction (02-05)
- Jinja2 FileSystemLoader for HTML template management (02-06)
- Status priority ordering (Critical, Watch, Monitor, Stable) for report grouping (02-06)
- Portuguese labels throughout report template for Brazilian audience (02-06)
- Async execute endpoint for GraphEmailService async operations (02-07)
- Atomic run status updates: pending -> running -> completed/failed (02-07)
- Per-item classification for granular status tracking (02-07)
- Optional email sending via send_email flag for testing flexibility (02-07)
- Pipeline orchestration pattern: Create run -> Get insurer -> Scrape -> Classify -> Store -> Report -> Email -> Update run (02-07)
- Windows Scheduled Task for production automation on Windows Server (02-09)
- SYSTEM account execution for proper permissions and service-like behavior (02-09)
- Staggered daily schedules to prevent resource contention (health 06:00, dental 07:00, group_life 08:00) (02-09)
- Comprehensive health check validates database, filesystem, and service configuration (02-09)
- ScrapedNewsItem as dataclass in base.py for unified representation (03-01)
- Async interface for NewsSource.search() for future batch processing (03-01)
- SourceRegistry uses class variables for global singleton pattern (03-01)
- Auto-registration on module import for simple source discovery (03-01)
- scraper.py delegates to GoogleNewsSource for backward compatibility (03-01)
- cheerio crawler for Valor (fast HTML parsing, no anti-bot needed) (03-03)
- playwright:firefox for CQCS (anti-bot compatibility) (03-03)
- max_concurrency=2 for CQCS to avoid rate limiting (03-03)
- Over-fetch then filter pattern for website crawlers (03-03)
- feedparser + aiohttp for RSS feed parsing with async fetching (03-02)
- GET instead of HEAD for health checks (some servers block HEAD) (03-02)
- G1 Economia RSS used for EstadaoSource (Estadao deprecated their feeds) (03-02)

### Pending Todos

None yet.

### Blockers/Concerns

**Phase 3 Research Findings:**
- No direct Apify actors for 5 additional Brazilian news sources
- Hybrid approach needed: RSS feeds for InfoMoney, Estadao, ANS + website crawlers for Valor, CQCS
- CQCS may have anti-bot protection (403 errors on direct access)
- Valor Economico exact search URL needs validation
- ANS gov.br RSS feed reliability uncertain

**Phase 5 Research Needs:**
- Portuguese sentiment analysis accuracy expectations
- Executive summary prompt engineering for insurance domain

**Phase 6+ Research Needs:**
- Marsh system integration APIs (if v2 advanced analytics pursued)
- Brazilian regulatory data sources classification

## Phase 1 Summary - COMPLETE

**All 4 plans complete across 3 execution waves:**

| Wave | Plans | Description | Status |
|------|-------|-------------|--------|
| 1 | 01-01 | Project scaffolding, database, models, schemas | DONE |
| 2 | 01-02, 01-03 | CRUD endpoints + Excel import | DONE |
| 3 | 01-04 | Excel export | DONE |

**DATA requirements fulfilled:**
- DATA-01: CRUD endpoints (01-02)
- DATA-02: Search/filter insurers (01-02)
- DATA-04: Upload Excel file (01-03)
- DATA-05: Preview before commit (01-03)
- DATA-06: Export as Excel (01-04)
- DATA-07: Validate required fields (01-03)
- DATA-08: Handle duplicates (01-03)

**Database populated:** 902 insurers from ByCat3.xlsx

## Phase 2 Progress - COMPLETE

**Plans complete: 9 of 9**

| Plan | Name | Status |
|------|------|--------|
| 02-01 | Database Models | DONE |
| 02-02 | Configuration | DONE |
| 02-03 | Scraper Service | DONE |
| 02-04 | Classification Service | DONE |
| 02-05 | Email Service | DONE |
| 02-06 | Report Generator | DONE |
| 02-07 | Run Orchestration | DONE |
| 02-08 | Import/Export | DONE |
| 02-09 | Deployment Automation | DONE |

## Phase 3 Planning - COMPLETE

**Plans: 6 plans in 4 waves**

| Wave | Plans | Description |
|------|-------|-------------|
| 1 | 03-01, 03-03 (partial) | Source abstraction + config |
| 2 | 03-02, 03-03 | RSS sources + crawler sources |
| 3 | 03-04, 03-05 | Batch processor + relevance scorer |
| 4 | 03-06 | Integration and endpoint update |

**Requirements covered:**
- NEWS-02: Valor Economico (03-03)
- NEWS-03: InfoMoney (03-02)
- NEWS-04: CQCS (03-03)
- NEWS-05: ANS releases (03-02)
- NEWS-06: Estadao/Broadcast (03-02)
- NEWS-07: Batch processing (03-04)
- NEWS-08: Complete metadata storage (03-06)
- NEWS-09: Insurer/run linking (03-06)
- NEWS-10: AI relevance scoring (03-05)

## Phase 3 Progress - IN PROGRESS

**Plans complete: 3 of 6**

| Plan | Name | Status |
|------|------|--------|
| 03-01 | Source Abstraction | DONE |
| 03-02 | RSS Sources | DONE |
| 03-03 | Crawler Sources | DONE |
| 03-04 | Batch Processor | PENDING |
| 03-05 | Relevance Scorer | PENDING |
| 03-06 | Integration | PENDING |

**Next:** Execute 03-04 (Batch Processor) and 03-05 (Relevance Scorer) in Wave 3

## Session Continuity

Last session: 2026-02-04
Stopped at: Completed 03-03-PLAN.md
Resume file: None

### What's Available Now

From Phase 1:
- `app.database.Base, engine, SessionLocal` - Database infrastructure
- `app.dependencies.get_db` - Session dependency
- `app.models.insurer.Insurer` - ORM model with 902 records
- `app.schemas.insurer.*` - Pydantic schemas
- `app.routers.insurers.router` - CRUD + search at /api/insurers
- `app.routers.import_export.router` - Import/export at /api/import
- `app.services.excel_service` - Excel parsing and generation
- `data/brasilintel.db` - SQLite database with insurers table

From Phase 2:
- `app.models.run.Run` - Run ORM model with status tracking (02-01)
- `app.models.news_item.NewsItem` - NewsItem ORM model with classification fields (02-01)
- `app.schemas.run.*` - Run schemas and enums (RunStatus, TriggerType) (02-01)
- `app.schemas.news.*` - NewsItem schemas and enums (InsurerStatus, Sentiment) (02-01)
- `app.config.Settings, get_settings` - Centralized configuration (02-02)
- `app.services.scraper.ApifyScraperService` - Google News scraper (02-03, delegates to sources)
- `app.services.scraper.ScrapedNewsItem` - Scraping result dataclass (02-03, re-exported from sources)

From Phase 3 (in progress):
- `app.services.sources.NewsSource` - Abstract base class for news sources (03-01)
- `app.services.sources.SourceRegistry` - Source discovery and management (03-01)
- `app.services.sources.ScrapedNewsItem` - Unified news item dataclass (03-01)
- `app.services.sources.GoogleNewsSource` - Google News implementation (03-01)
- `app.services.sources.RSSNewsSource` - Base RSS source class (03-02)
- `app.services.sources.InfoMoneySource` - InfoMoney RSS source (03-02)
- `app.services.sources.EstadaoSource` - Estadao RSS source (03-02)
- `app.services.sources.ANSSource` - ANS gov.br RSS source (03-02)
- `app.services.sources.ValorSource` - Valor Economico crawler (03-03)
- `app.services.sources.CQCSSource` - CQCS crawler (03-03)
- `app.config.batch_size, batch_delay_seconds, max_concurrent_sources` - Batch config (03-03)
- `app.services.classifier.ClassificationService` - Azure OpenAI classification (02-04)
- `app.schemas.classification.*` - NewsClassification, InsurerClassification (02-04)
- `app.services.emailer.GraphEmailService` - Microsoft Graph email sender (02-05)
- `app.services.reporter.ReportService` - HTML report generator with Jinja2 (02-06)
- `app.services.reporter.ReportData` - Report data container dataclass (02-06)
- `app.templates/report_basic.html` - Jinja2 template with Portuguese labels (02-06)
- `app.routers.runs.router` - Run orchestration endpoint at /api/runs (02-07)
- `app.routers.import_export.router` - Import/export insurers at /api/import (02-08)
- `deploy/setup_scheduled_task.ps1` - Windows Task Scheduler setup script (02-09)
- `deploy/manage_service.ps1` - Service management PowerShell script (02-09)
- `deploy/run_brasilintel.bat` - Batch execution template (02-09)
- Enhanced `/api/health` endpoint with dependency validation (02-09)
- Database tables: insurers, runs, news_items with relationships (02-01)

---
*Initialized: 2026-02-04*
*Last updated: 2026-02-04
