# Architecture Patterns

**Domain:** Competitive Intelligence / News Monitoring System
**Researched:** 2026-02-04
**Confidence:** MEDIUM

## Executive Summary

Competitive intelligence and news monitoring systems in 2026 follow a **multi-stage ETL pipeline architecture** with distinct separation between data collection, processing, classification, and delivery. The architecture emphasizes **continuous monitoring** over periodic checks, **AI-driven classification** for intelligence extraction, and **queue-based delivery** for reliability.

**Key architectural principle:** Decouple collection from processing from delivery to enable independent scaling, failure recovery, and maintainability.

## Recommended Architecture for BrasilIntel

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                         │
│  (Windows Scheduled Task / Docker Cron - 3 daily runs per category) │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ├──────────────┬──────────────┬──────────────┐
                 │              │              │              │
                 v              v              v              v
         ┌──────────────────────────────────────────────────────────┐
         │              DATA COLLECTION LAYER                       │
         │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
         │  │ Web      │  │ RSS/Atom │  │ Social   │              │
         │  │ Scraping │  │ Feeds    │  │ Media    │              │
         │  │ (Apify)  │  │          │  │ APIs     │              │
         │  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
         │       └──────────────┴──────────────┘                   │
         │                      │                                   │
         │                      v                                   │
         │           ┌─────────────────────┐                       │
         │           │ Raw Content Store   │                       │
         │           │   (Staging Table)   │                       │
         │           └──────────┬──────────┘                       │
         └──────────────────────┼──────────────────────────────────┘
                                │
                                v
         ┌──────────────────────────────────────────────────────────┐
         │            PROCESSING & CLASSIFICATION LAYER             │
         │  ┌──────────────────────────────────────────────────┐   │
         │  │  Data Normalization & Deduplication              │   │
         │  │  (Extract, Clean, Standardize)                   │   │
         │  └────────────────────┬─────────────────────────────┘   │
         │                       v                                  │
         │  ┌──────────────────────────────────────────────────┐   │
         │  │  Multi-Stage LLM Classification Pipeline        │   │
         │  │  ┌──────────────────────────────────────────┐   │   │
         │  │  │ Stage 1: Relevance Filter (Fast/Cheap)  │   │   │
         │  │  │ Stage 2: Category Classification         │   │   │
         │  │  │ Stage 3: Entity Extraction & Enrichment │   │   │
         │  │  └─────────────┬────────────────────────────┘   │   │
         │  └────────────────┼─────────────────────────────────┘   │
         │                   v                                      │
         │  ┌──────────────────────────────────────────────────┐   │
         │  │        Persistence Layer (SQLite)                │   │
         │  │  - Articles (classified & enriched)              │   │
         │  │  - Insurers (897 entities)                       │   │
         │  │  - Categories (Health, Dental, Group Life)       │   │
         │  │  - Classification History & Audit Log            │   │
         │  └────────────────────┬─────────────────────────────┘   │
         └────────────────────────┼────────────────────────────────┘
                                  │
                                  v
         ┌──────────────────────────────────────────────────────────┐
         │              DELIVERY & NOTIFICATION LAYER               │
         │  ┌──────────────────────────────────────────────────┐   │
         │  │  Report Aggregation & Formatting                 │   │
         │  │  (Group by category, insurer, priority)          │   │
         │  └────────────────────┬─────────────────────────────┘   │
         │                       v                                  │
         │  ┌──────────────────────────────────────────────────┐   │
         │  │  Notification Queue                              │   │
         │  │  (Decouples processing from delivery)            │   │
         │  └────────────────────┬─────────────────────────────┘   │
         │                       v                                  │
         │  ┌──────────────────────────────────────────────────┐   │
         │  │  Email Delivery Service                          │   │
         │  │  (Microsoft Graph API)                           │   │
         │  │  - Retry logic                                   │   │
         │  │  - Delivery confirmation                         │   │
         │  │  - Failure alerting                              │   │
         │  └─────────────────────────────────────────────────┘    │
         └──────────────────────────────────────────────────────────┘
                                  │
                                  v
         ┌──────────────────────────────────────────────────────────┐
         │            ADMIN & MONITORING LAYER                      │
         │  ┌──────────────────────────────────────────────────┐   │
         │  │  FastAPI Web UI & REST API                       │   │
         │  │  - Configuration management                      │   │
         │  │  - Manual article review/reclassification        │   │
         │  │  - Insurer management (897 entities)             │   │
         │  │  - Pipeline status & health monitoring           │   │
         │  │  - Historical analytics & reporting              │   │
         │  └─────────────────────────────────────────────────┘    │
         └──────────────────────────────────────────────────────────┘
```

## Component Boundaries

| Component | Responsibility | Input | Output | Communicates With |
|-----------|---------------|-------|--------|-------------------|
| **Orchestrator** | Schedules and triggers pipeline runs per category | Schedule config (Health/Dental/Life) | Trigger events | All layers (coordinates) |
| **Web Scraper** | Fetches raw content from insurer websites via Apify | Insurer URLs, scraping configs | Raw HTML/JSON content | Raw Content Store |
| **Raw Content Store** | Temporary staging of unprocessed content | Raw scraped data | Raw records for processing | Normalization Engine |
| **Normalization Engine** | Cleans, standardizes, deduplicates content | Raw content records | Normalized article objects | Classification Pipeline |
| **LLM Classification Pipeline** | Multi-stage relevance filtering and categorization | Normalized articles | Classified & enriched articles | Persistence Layer |
| **Persistence Layer (SQLite)** | Stores all entities, articles, audit logs | Structured data objects | Query results | All components (central data store) |
| **Report Aggregator** | Builds category-specific intelligence reports | Classified articles, filters | Formatted report structures | Notification Queue |
| **Notification Queue** | Buffers reports for reliable delivery | Report objects | Queued notifications | Email Delivery Service |
| **Email Delivery Service** | Sends reports via Microsoft Graph API | Notification payloads | Delivery status | Monitoring Layer |
| **Admin Web UI** | Provides human oversight and configuration | HTTP requests | Web pages, API responses | Persistence Layer |
| **Monitoring Dashboard** | Tracks pipeline health and performance | System metrics, logs | Status displays, alerts | All components (observability) |

## Data Flow

### Primary Pipeline Flow (Automated - 3x Daily per Category)

```
1. TRIGGER
   Orchestrator → Initiates pipeline run for category (Health, Dental, or Group Life)

2. COLLECTION
   Web Scraper (Apify) → Fetches content from 897 insurer websites
   ↓
   Raw Content Store → Stages unprocessed articles with metadata

3. PROCESSING
   Normalization Engine → Extracts text, cleans HTML, removes duplicates
   ↓
   Stage 1 Classification → Fast relevance filter (is this insurance news?)
   ↓
   Stage 2 Classification → Category assignment (Health/Dental/Life match)
   ↓
   Stage 3 Enrichment → Entity extraction (which insurers mentioned?)
   ↓
   Persistence Layer → Saves classified articles with relationships

4. DELIVERY
   Report Aggregator → Groups articles by priority and insurer
   ↓
   Notification Queue → Buffers formatted reports
   ↓
   Email Delivery Service → Sends via Microsoft Graph API
   ↓
   Monitoring → Logs delivery status and errors
```

### Secondary Flow (Admin Management)

```
Admin User → Web UI (FastAPI)
             ↓
             Persistence Layer (SQLite)
             ↓
             CRUD Operations:
             - View/reclassify articles
             - Manage insurer list (897 entities)
             - Configure scraping rules
             - Monitor pipeline health
             - View historical analytics
```

### Error & Retry Flow

```
Any Component → Error Detected
                ↓
                Monitoring Layer → Logs error with context
                ↓
                Retry Logic → Attempts recovery (with exponential backoff)
                ↓
                If persistent failure:
                  - Alert administrators
                  - Queue for manual review
                  - Continue processing other items
```

## Patterns to Follow

### Pattern 1: Multi-Stage LLM Classification Pipeline
**What:** Cascaded classifier chain using different models at each stage for cost optimization and accuracy.

**Why:** Full-size LLMs are expensive for every classification task. Use small/fast models for coarse filtering, reserve expensive models for complex analysis.

**When:** Processing large volumes (897 insurers × multiple articles daily) where most content needs filtering.

**Implementation:**
```python
class ClassificationPipeline:
    """Multi-stage classification optimized for cost and accuracy."""

    def __init__(self):
        self.stage1_filter = FastClassifier()  # Cheap binary relevance check
        self.stage2_categorizer = AzureOpenAI()  # Category assignment
        self.stage3_enricher = AzureOpenAI()  # Entity extraction

    async def classify(self, article: Article) -> ClassifiedArticle:
        # Stage 1: Fast filter (95% throughput, 5% pass to stage 2)
        if not await self.stage1_filter.is_relevant(article):
            return ClassifiedArticle(relevant=False, confidence="high")

        # Stage 2: Category classification (only 5% reach here)
        category = await self.stage2_categorizer.categorize(
            article,
            categories=["Health", "Dental", "Group Life"]
        )

        # Stage 3: Entity extraction (only relevant articles)
        entities = await self.stage3_enricher.extract_entities(
            article,
            entity_list=self.insurers
        )

        return ClassifiedArticle(
            relevant=True,
            category=category,
            entities=entities,
            confidence="high"
        )
```

**Sources:**
- [Multi-Stage LLM Classification Pipeline - Emergent Mind](https://www.emergentmind.com/topics/multi-stage-llm-based-classification-pipeline)
- [LLM Orchestration in 2026 - AIMultiple](https://research.aimultiple.com/llm-orchestration/)

### Pattern 2: Queue-Based Notification Delivery
**What:** Decouple report generation from email delivery using an in-memory or database-backed queue.

**Why:** Email delivery can fail due to network issues, API limits, or transient errors. Queue ensures no reports are lost.

**When:** Production systems requiring delivery guarantees and retry capabilities.

**Implementation:**
```python
class NotificationQueue:
    """Reliable notification delivery with retry logic."""

    def __init__(self, db: Database):
        self.db = db
        self.max_retries = 3
        self.retry_delays = [60, 300, 900]  # 1min, 5min, 15min

    async def enqueue(self, report: Report):
        """Add report to delivery queue."""
        await self.db.execute(
            """
            INSERT INTO notification_queue
            (report_id, category, recipients, payload, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (report.id, report.category, report.recipients,
             report.to_json(), datetime.utcnow())
        )

    async def process_queue(self):
        """Process pending notifications with retry logic."""
        pending = await self.db.fetch_all(
            "SELECT * FROM notification_queue WHERE status = 'pending'"
        )

        for notification in pending:
            try:
                await self.email_service.send(notification)
                await self._mark_delivered(notification.id)
            except Exception as e:
                await self._handle_failure(notification, e)

    async def _handle_failure(self, notification, error):
        """Implement exponential backoff retry."""
        retry_count = notification.retry_count + 1

        if retry_count > self.max_retries:
            await self._mark_failed(notification.id, str(error))
            await self._alert_admin(notification, error)
        else:
            next_attempt = datetime.utcnow() + timedelta(
                seconds=self.retry_delays[retry_count - 1]
            )
            await self._schedule_retry(notification.id, next_attempt)
```

**Sources:**
- [Design a Scalable Notification Service - AlgoMaster](https://blog.algomaster.io/p/design-a-scalable-notification-service)
- [Notification System Architecture With AWS - Medium](https://medium.com/@joudwawad/notification-system-architecture-with-aws-968103c2c730)

### Pattern 3: Session-Per-Request Database Pattern
**What:** Use FastAPI dependency injection to provide one database session per HTTP request.

**Why:** Ensures proper transaction boundaries, resource cleanup, and thread safety with SQLite.

**When:** Building web APIs that interact with databases.

**Implementation:**
```python
from fastapi import Depends, FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./brasilintel.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Critical for FastAPI
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency
def get_db():
    """Provide database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Usage in routes
app = FastAPI()

@app.get("/articles/{article_id}")
async def get_article(article_id: int, db: Session = Depends(get_db)):
    """Retrieve article with automatic session management."""
    article = db.query(Article).filter(Article.id == article_id).first()
    return article
```

**Sources:**
- [SQL (Relational) Databases - FastAPI](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [Modern FastAPI Architecture Patterns - Medium](https://medium.com/algomart/modern-fastapi-architecture-patterns-for-scalable-production-systems-41a87b165a8b)

### Pattern 4: Configuration-Driven Pipeline Orchestration
**What:** Separate pipeline logic from configuration (insurers, categories, scraping rules).

**Why:** Non-technical users can manage configurations without code changes. Enables A/B testing and gradual rollouts.

**When:** Systems with frequently changing business rules or entity lists.

**Implementation:**
```python
class PipelineConfig:
    """Centralized configuration management."""

    def __init__(self, db: Database):
        self.db = db
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes

    async def get_active_insurers(self, category: str) -> List[Insurer]:
        """Retrieve active insurers for category."""
        cache_key = f"insurers:{category}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        insurers = await self.db.fetch_all(
            """
            SELECT * FROM insurers
            WHERE category = ? AND active = true
            ORDER BY priority DESC
            """,
            (category,)
        )

        self._cache[cache_key] = insurers
        return insurers

    async def get_classification_prompt(self, stage: str) -> str:
        """Retrieve stage-specific LLM prompt."""
        return await self.db.fetch_one(
            "SELECT prompt_text FROM llm_prompts WHERE stage = ?",
            (stage,)
        )

# Admin UI for configuration management
@app.put("/admin/insurers/{insurer_id}")
async def update_insurer(
    insurer_id: int,
    updates: InsurerUpdate,
    db: Session = Depends(get_db)
):
    """Allow non-technical users to manage insurer configurations."""
    insurer = db.query(Insurer).filter(Insurer.id == insurer_id).first()
    for field, value in updates.dict(exclude_unset=True).items():
        setattr(insurer, field, value)
    db.commit()
    return {"status": "updated"}
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Synchronous Processing Without Queues
**What:** Processing articles and sending emails in a single synchronous flow.

**Why bad:**
- Email delivery failures block entire pipeline
- No retry capability for transient failures
- Cannot scale independently (scraping vs delivery)
- Difficult to monitor and debug

**Consequences:**
- Lost reports when email fails
- Pipeline hangs on network issues
- Poor user experience (slow responses)
- Cascading failures

**Instead:** Use queue-based architecture to decouple stages. Process and persist articles first, then queue notifications for asynchronous delivery with retry logic.

**Detection:** Monitor for pipeline timeouts, email delivery blocking database transactions, or reports disappearing during failures.

**Sources:**
- [Design a Scalable Notification Service - AlgoMaster](https://blog.algomaster.io/p/design-a-scalable-notification-service)
- [Competitive Intelligence Automation: The 2026 Playbook](https://arisegtm.com/blog/competitive-intelligence-automation-2026-playbook)

### Anti-Pattern 2: Using Expensive LLMs for All Classification
**What:** Sending every scraped article to GPT-4 or equivalent for classification.

**Why bad:**
- Extremely high API costs (897 insurers × multiple articles × 3 runs daily)
- Slow processing times (LLM calls are 1-5 seconds each)
- Unnecessary for simple relevance filtering

**Consequences:**
- Monthly Azure OpenAI costs of $1000+ for simple filtering tasks
- Pipeline takes hours instead of minutes
- Budget constraints force cutting scope

**Instead:** Implement multi-stage cascaded classification. Use fast heuristics or small models for relevance filtering (Stage 1), reserve expensive LLMs for complex categorization (Stage 2+). Expected cost reduction: 60-80%.

**Detection:** High Azure OpenAI billing, slow pipeline execution, most LLM calls returning "not relevant."

**Sources:**
- [Multi-Stage LLM Classification Pipeline - Emergent Mind](https://www.emergentmind.com/topics/multi-stage-llm-based-classification-pipeline)
- [LLM deployment pipeline - Northflank](https://northflank.com/blog/llm-deployment-pipeline)

### Anti-Pattern 3: No Idempotency in Scheduled Tasks
**What:** Pipeline runs without checking for duplicate processing or partial completion.

**Why bad:**
- Duplicate email notifications confuse users
- Wasted processing on already-classified articles
- Cannot safely retry failed runs

**Consequences:**
- Users receive same report multiple times
- Database bloat from duplicate records
- Cannot recover from partial failures

**Instead:** Implement idempotency keys for each pipeline run. Store processing state in database. Check for existing classifications before processing. Design retry logic to be safe.

**Detection:** Duplicate notifications, multiple database entries for same article, user complaints about repeated emails.

**Sources:**
- [ETL Frameworks in 2026 - Integrate.io](https://www.integrate.io/blog/etl-frameworks-in-2025-designing-robust-future-proof-data-pipelines/)
- [Data Pipeline Architecture - Monte Carlo Data](https://www.montecarlodata.com/blog-data-pipeline-architecture-explained/)

### Anti-Pattern 4: Hardcoded Business Logic
**What:** Embedding insurer lists, categories, and classification rules directly in code.

**Why bad:**
- Every change requires code deployment
- Cannot A/B test rule changes
- Business users depend on engineers for updates
- Difficult to maintain 897 insurer configurations in code

**Consequences:**
- Slow iteration cycles (days instead of minutes)
- Engineer bottleneck for business changes
- Configuration drift between environments
- High maintenance burden

**Instead:** Store all business logic in database tables with admin UI for management. Use configuration-driven pipeline that loads rules at runtime. Enable hot-reloading without restarts.

**Detection:** Frequent code commits for "config changes," business users blocked waiting for deploys, environment-specific code branches.

**Sources:**
- [Admin Dashboard: Ultimate Guide - WeWeb](https://www.weweb.io/blog/admin-dashboard-ultimate-guide-templates-examples)
- [Competitive Intelligence Data Analysis - Group BWT](https://groupbwt.com/blog/competitive-intelligence-data-analysis/)

### Anti-Pattern 5: SQLite for High-Concurrency Production
**What:** Using SQLite with default settings for production with high write concurrency.

**Why bad:**
- SQLite locks entire database for writes (not row-level)
- Poor performance under concurrent write load
- Limited horizontal scaling capabilities
- Write-ahead logging (WAL) mode required but not always used

**Consequences:**
- Admin UI locks up during pipeline runs
- "Database is locked" errors
- Cannot scale beyond single machine
- Poor user experience

**Instead:** For BrasilIntel's use case (low concurrency, 3 scheduled runs daily), SQLite with WAL mode is acceptable. For higher concurrency, migrate to PostgreSQL. Use read replicas for analytics queries.

**Note for BrasilIntel:** Current architecture (3 daily runs, admin UI) fits SQLite's strengths. Monitor for "database locked" errors. If adding real-time monitoring or multiple concurrent pipeline runs, plan PostgreSQL migration.

**Detection:** "Database is locked" errors, slow admin UI during processing, inability to run simultaneous pipelines.

**Sources:**
- [FastAPI SQLite Production Architecture - Medium](https://medium.com/@faizulkhan56/building-a-scalable-fastapi-application-with-sqlmodel-a-complete-guide-to-three-layer-architecture-3c33ec981922)
- [SQL (Relational) Databases - FastAPI](https://fastapi.tiangolo.com/tutorial/sql-databases/)

## Build Order Recommendations

### Phase Structure Based on Dependencies

The architecture suggests a **bottom-up build approach** with clear dependency chains:

```
Foundation (Phase 1)
├─ Database schema & models (SQLite)
├─ Basic FastAPI app structure
└─ Configuration management tables

↓

Data Layer (Phase 2)
├─ Web scraping integration (Apify)
├─ Raw content ingestion
└─ Normalization engine

↓

Intelligence Layer (Phase 3)
├─ LLM classification pipeline (Azure OpenAI)
├─ Entity extraction
└─ Article persistence

↓

Delivery Layer (Phase 4)
├─ Report aggregation
├─ Notification queue
└─ Email delivery (Microsoft Graph API)

↓

Admin Layer (Phase 5)
├─ Web UI for configuration management
├─ Article review & reclassification
└─ Pipeline monitoring dashboard

↓

Orchestration Layer (Phase 6)
├─ Scheduled task coordination
└─ Error handling & alerting
```

### Critical Path: Vertical Slice First

**Recommendation:** Build a **minimal vertical slice** through all layers before expanding horizontally.

**Why:** Validates architecture end-to-end, identifies integration issues early, provides working demo quickly.

**Minimal vertical slice:**
1. Single insurer scraping (Apify)
2. Simple LLM classification (Azure OpenAI)
3. SQLite storage
4. Basic email delivery (Microsoft Graph API)
5. Manual trigger (no scheduling yet)

**Then expand:**
- Add 897 insurers
- Implement multi-stage classification
- Build admin UI
- Add scheduling
- Implement monitoring

### Component Dependencies

| Component | Depends On | Can Start Before | Blocks |
|-----------|------------|------------------|--------|
| Database Schema | None | - | Everything |
| Web Scraper | Database Schema | - | Normalization |
| Normalization | Database, Scraper | Scraper prototype | Classification |
| Classification | Normalization, Azure OpenAI setup | Prompt engineering | Report Aggregation |
| Persistence | Database Schema | Classification design | Admin UI, Delivery |
| Report Aggregation | Persistence | - | Notification Queue |
| Notification Queue | Persistence | Report design | Email Delivery |
| Email Delivery | Queue, Microsoft Graph API | Queue design | Monitoring |
| Admin UI | Persistence | Database schema | None (parallel) |
| Monitoring | All components | Early instrumentation | None (parallel) |
| Orchestration | All components | Pipeline design | Production deployment |

### Parallel Development Opportunities

These components can be developed simultaneously by different team members:

**Track 1 (Backend Pipeline):**
- Web scraping → Normalization → Classification → Persistence

**Track 2 (Delivery):**
- Email delivery service (can mock inputs initially)
- Notification queue design

**Track 3 (Admin UI):**
- FastAPI routes and UI (can use SQLite test data)
- Configuration management interface

**Track 4 (Infrastructure):**
- Monitoring and logging setup
- Orchestration framework (Windows Scheduled Task)

**Integration point:** Bring tracks together after each completes its vertical slice.

## Scalability Considerations

| Concern | Current (897 insurers) | At 5K insurers | At 50K insurers |
|---------|------------------------|----------------|-----------------|
| **Scraping** | Apify handles well (parallel execution) | Same approach, increase Apify concurrency | Consider distributed scraping or self-hosted |
| **Classification** | Multi-stage pipeline sufficient | Add caching for repeat classifications | Implement batch processing, consider fine-tuned models |
| **Storage** | SQLite adequate (low write concurrency) | SQLite with WAL mode still viable | Migrate to PostgreSQL for better concurrency |
| **Delivery** | Microsoft Graph API handles 3 emails/day easily | Queue ensures reliability at scale | May need rate limiting and batch email sending |
| **Orchestration** | Windows Scheduled Task sufficient | Same approach, monitor execution time | Consider Apache Airflow or Prefect for complex DAG workflows |
| **Admin UI** | FastAPI + SQLite handles single admin user | Add authentication and caching | Add read replicas, implement API rate limiting |

### Performance Budgets for BrasilIntel

Based on current scope (897 insurers × 3 categories × daily runs):

**Collection Phase:**
- Target: <15 minutes per category run
- Bottleneck: Apify scraping speed (parallel workers)

**Processing Phase:**
- Target: <30 minutes per category run
- Bottleneck: LLM API calls (implement multi-stage to reduce)

**Delivery Phase:**
- Target: <5 minutes per category run
- Bottleneck: Email delivery (Microsoft Graph API rate limits)

**Total Pipeline:**
- Target: <1 hour per category run (3 hours total daily)
- Current parallel opportunity: Run all 3 categories simultaneously if resources allow

## Monitoring & Observability Architecture

Essential monitoring points for reliable operation:

```
┌─────────────────────────────────────────────────────────────┐
│                   MONITORING DASHBOARD                       │
│  ┌────────────────┬────────────────┬────────────────────┐  │
│  │ Pipeline Health│ Classification │ Delivery Status    │  │
│  │ - Run status   │ - Accuracy     │ - Success rate     │  │
│  │ - Duration     │ - Cost/article │ - Failed emails    │  │
│  │ - Errors       │ - Throughput   │ - Retry queue size │  │
│  └────────────────┴────────────────┴────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         v                    v                    v
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ Collection     │  │ Processing     │  │ Delivery       │
│ Metrics        │  │ Metrics        │  │ Metrics        │
│                │  │                │  │                │
│ - Articles     │  │ - LLM calls    │  │ - Emails sent  │
│   scraped      │  │ - Token usage  │  │ - Failures     │
│ - Duplicates   │  │ - Processing   │  │ - Retries      │
│ - Failures     │  │   time         │  │ - Queue depth  │
└────────────────┘  └────────────────┘  └────────────────┘
```

**Key metrics to track:**
1. **Pipeline Execution:** Success rate, duration, error counts per category
2. **Classification Quality:** Accuracy (requires manual review sample), cost per article
3. **Delivery Reliability:** Email success rate, retry counts, queue depth
4. **System Health:** Database size growth, API rate limit headroom, disk space

**Alerting priorities:**
- CRITICAL: Pipeline failures, delivery failures (all emails)
- HIGH: Classification accuracy drops, cost spikes
- MEDIUM: Slow pipeline execution, high retry counts
- LOW: Individual article scraping failures

## Integration with External Services

| Service | Purpose | Critical Path | Failure Mode | Mitigation |
|---------|---------|---------------|--------------|------------|
| **Apify** | Web scraping | Yes | Cannot collect data | Retry logic, fallback to manual scraping, queue failed insurers |
| **Azure OpenAI** | LLM classification | Yes | Cannot classify articles | Cache previous classifications, queue for later, alert admin |
| **Microsoft Graph API** | Email delivery | Yes | Cannot send reports | Queue in database, retry with exponential backoff, alert admin |
| **Windows Scheduled Task** | Orchestration | Yes | Pipeline not triggered | Monitoring alerts, manual trigger capability via admin UI |

## Confidence Assessment

**Architecture Confidence:** MEDIUM

**Sources of confidence:**
- Multiple authoritative sources on modern CI system architecture
- Clear patterns from 2026 data pipeline best practices
- Validated LLM classification pipeline patterns
- Proven notification delivery architectures

**Sources of uncertainty:**
- Specific Apify integration patterns (documented but not extensively)
- Microsoft Graph API rate limits for specific use case (need validation)
- Optimal multi-stage classification thresholds (requires experimentation)
- SQLite performance limits for this exact workload (897 insurers × 3 categories)

**Recommendations for validation:**
1. Prototype vertical slice to validate Azure OpenAI classification cost/performance
2. Test Microsoft Graph API email delivery under realistic load
3. Benchmark SQLite write performance with WAL mode enabled
4. Validate Apify scraping speed and cost for 897 insurers

## Sources

### Competitive Intelligence & News Monitoring Architecture
- [7 Competitive Intelligence Challenges & Solutions in 2026](https://research.aimultiple.com/competitive-intelligence-challenges/)
- [Competitive Intelligence Automation: The 2026 Playbook](https://arisegtm.com/blog/competitive-intelligence-automation-2026-playbook)
- [The Best Competitive Intelligence Products in 2026](https://parano.ai/blog/the-best-competitive-intelligence-products-in-2026)
- [Competitive Intelligence Data Analysis: Strategy & System](https://groupbwt.com/blog/competitive-intelligence-data-analysis/)

### Data Pipeline Architecture
- [How to Build Modern Data Pipelines for Analytics and AI in 2026](https://www.alation.com/blog/building-data-pipelines/)
- [Data Pipeline Architecture Explained: 6 Diagrams And Best Practices](https://www.montecarlodata.com/blog-data-pipeline-architecture-explained/)
- [Data Pipelines 101: Architecture and Implementation - Coalesce](https://coalesce.io/data-insights/data-pipelines-101-architecture-and-implementation/)
- [ETL Frameworks in 2026 for Future-Proof Data Pipelines](https://www.integrate.io/blog/etl-frameworks-in-2025-designing-robust-future-proof-data-pipelines/)

### Web Scraping & ETL
- [Building an ETL Pipeline for Web Scraping Using Python](https://dev.to/techwithqasim/building-an-etl-pipeline-for-web-scraping-using-python-2381)
- [ETL Pipeline: A Complete Guide for Web Scraping Data](https://www.ipway.com/blog/etl-pipeline-web-scraping/)
- [ETL for Web Scraping – A Comprehensive Guide](https://blog.pline.ai/etl-for-web-scraping/)

### LLM Classification Pipeline
- [Multi-Stage LLM Classification Pipeline](https://www.emergentmind.com/topics/multi-stage-llm-based-classification-pipeline)
- [LLM deployment pipeline: Complete overview and requirements](https://northflank.com/blog/llm-deployment-pipeline)
- [Ultimate Guide to Preprocessing Pipelines for LLMs](https://latitude-blog.ghost.io/blog/ultimate-guide-to-preprocessing-pipelines-for-llms/)
- [LLM Orchestration in 2026: Top 12 frameworks and 10 gateways](https://research.aimultiple.com/llm-orchestration/)

### Notification & Email Delivery
- [Design a Scalable Notification Service - System Design Interview](https://blog.algomaster.io/p/design-a-scalable-notification-service)
- [Designing a Scalable Notification System: From HLD to LLD](https://medium.com/@tanushree2102/designing-a-scalable-notification-system-from-hld-to-lld-e2ed4b3fb348)
- [How to Design a Notification System: A Complete Guide](https://www.systemdesignhandbook.com/guides/design-a-notification-system/)
- [Notification System Architecture With AWS](https://medium.com/@joudwawad/notification-system-architecture-with-aws-968103c2c730)

### FastAPI & SQLite
- [SQL (Relational) Databases - FastAPI](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [Modern FastAPI Architecture Patterns for Scalable Production Systems](https://medium.com/algomart/modern-fastapi-architecture-patterns-for-scalable-production-systems-41a87b165a8b)
- [Building a Scalable FastAPI Application with SQLModel: A Complete Guide to Three-Layer Architecture](https://medium.com/@faizulkhan56/building-a-scalable-fastapi-application-with-sqlmodel-a-complete-guide-to-three-layer-architecture-3c33ec981922)
- [FastAPI Performance Tuning & Caching Strategy 101](https://blog.greeden.me/en/2026/02/03/fastapi-performance-tuning-caching-strategy-101-a-practical-recipe-for-growing-a-slow-api-into-a-lightweight-fast-api/)

### Admin Dashboard Architecture
- [Admin Dashboard: Ultimate Guide, Templates & Examples (2026)](https://www.weweb.io/blog/admin-dashboard-ultimate-guide-templates-examples)
- [Understanding Business Intelligence Architecture (BI Architecture) in 2026](https://swovo.com/blog/business-intelligence-architecture/)

### Data Aggregation & Multi-Source Integration
- [6 Best Data Aggregation Tools for 2026: Features & Use Cases](https://airbyte.com/top-etl-tools-for-sources/best-data-aggregation-tools)
- [10 Common Data Integration Patterns: A Complete Guide for 2026](https://blog.skyvia.com/common-data-integration-patterns/)
