---
phase: 03-news-collection-scale
plan: 06
subsystem: scraping-infrastructure
tags: [integration, scraper, batch-processing, api, fastapi]

dependency_graph:
  requires: ["03-01", "03-02", "03-03", "03-04", "03-05"]
  provides: ["unified-scraper-service", "category-processing-api"]
  affects: ["04-scheduling"]

tech_stack:
  added: []
  patterns:
    - "service-facade"
    - "batch-processing"
    - "async-api"

key_files:
  created: []
  modified:
    - app/services/scraper.py
    - app/routers/runs.py

decisions:
  - id: "scraper-service-facade"
    choice: "ScraperService as unified facade over components"
    rationale: "Clean separation, single entry point for all scraping needs"
  - id: "backward-compatibility"
    choice: "Keep ApifyScraperService for Phase 2 compatibility"
    rationale: "No breaking changes to existing code"
  - id: "batch-then-classify"
    choice: "Scrape all items first, then classify in batch"
    rationale: "More efficient for 897 insurers, reduces API round-trips"

metrics:
  duration: "~15 minutes"
  completed: "2026-02-04"
---

# Phase 03 Plan 06: Integration and API Updates Summary

**One-liner:** Unified ScraperService integrating 6 sources with batch processor and relevance scorer, plus category processing API endpoints.

## What Was Built

### ScraperService (app/services/scraper.py)

The new unified scraper service provides a single entry point for all Phase 3 scraping capabilities:

```python
class ScraperService:
    """
    Integrates:
    - 6 news sources (Google News, InfoMoney, Estadao, ANS, Valor, CQCS)
    - Batch processing for 897 insurers
    - Relevance scoring pre-filter
    """

    async def scrape_insurer(self, insurer, max_results_per_source=10)
    async def process_category(self, category, db, run, enabled_only=True)
    async def process_insurers(self, insurers, run, db)
    def health_check() -> dict
```

Key features:
- Configurable source selection (default: all 6)
- Optional relevance scoring toggle
- Full health check of all components
- Async-first design with sync wrappers

### ApifyScraperService (Backward Compatibility)

Maintained for Phase 2 code compatibility - same interface, delegates to GoogleNewsSource internally.

### Run API Endpoints (app/routers/runs.py)

**Updated `/api/runs/execute`:**
- Added `process_all` boolean flag
- Single insurer mode now uses all 6 sources
- Category mode triggers batch processing

**New `/api/runs/execute/category`:**
- Dedicated Phase 3 endpoint
- Processes all insurers in category
- Uses batch processor with progress tracking

**New `/api/runs/health/scraper`:**
- Reports status of all 6 sources
- Shows batch processor configuration
- Shows relevance scorer status

### Workflow Changes

**Single Insurer Mode (process_all=False):**
1. Get insurer from DB
2. ScraperService.scrape_insurer() - all 6 sources
3. Classify each item
4. Store with classification
5. Generate report, send email

**Category Mode (process_all=True):**
1. ScraperService.process_category() - batch processing
2. Classify all stored items (batch)
3. Generate report, send email

The batch-then-classify approach is more efficient for large volumes.

## Technical Decisions

### 1. Service Facade Pattern

ScraperService acts as a facade over:
- SourceRegistry (6 sources)
- BatchProcessor (concurrency control)
- RelevanceScorer (pre-filtering)

Benefits:
- Clean separation of concerns
- Single configuration point
- Easy to test components independently

### 2. Backward Compatibility

ApifyScraperService preserved with identical interface:
- Existing code continues to work
- No migration required for Phase 2 features
- Gradual adoption of ScraperService

### 3. Batch-Then-Classify Workflow

For category processing:
- Scrape all items first (async batch)
- Classify stored items after (sequential)

Rationale:
- Batch processor handles rate limiting
- Classification can be parallelized later
- Database transactions are cleaner

## Integration Points

### Imports Verified

```python
# scraper.py imports
from app.services.batch_processor import BatchProcessor, BatchProgress
from app.services.relevance_scorer import RelevanceScorer

# runs.py imports
from app.services.scraper import ApifyScraperService, ScraperService
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/runs/execute` | POST | Execute run (single or category) |
| `/api/runs/execute/category` | POST | Execute full category run |
| `/api/runs/health/scraper` | GET | Scraper component health |

## Verification Results

All success criteria met:
1. ScraperService integrates all 6 sources
2. Batch processor handles category-wide processing
3. Relevance scorer pre-filters items
4. /execute endpoint supports both single and category modes
5. /execute/category dedicated endpoint for Phase 3
6. Health endpoint reports all component status
7. Backward compatibility with Phase 2 code maintained

## Files Changed

| File | Changes |
|------|---------|
| `app/services/scraper.py` | +223/-16 lines - Added ScraperService class |
| `app/routers/runs.py` | +287/-121 lines - Added category processing |

## Commits

| Hash | Message |
|------|---------|
| d94ec8f | feat(03-06): add unified ScraperService with multi-source support |
| 1dc9bd9 | feat(03-06): add category processing and health endpoints |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Phase 3 is now complete. All components integrated:
- 6 news sources registered and functional
- Batch processor with rate limiting
- Relevance scorer for pre-filtering
- Unified scraper service
- Category processing API

Ready for Phase 4 (Scheduling) to add automated daily runs.
