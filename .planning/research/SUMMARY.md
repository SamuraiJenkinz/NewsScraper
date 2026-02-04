# Project Research Summary

**Project:** BrasilIntel - Competitive Intelligence System
**Domain:** Automated news monitoring, LLM classification, scheduled reporting
**Researched:** 2026-02-04
**Confidence:** HIGH

## Executive Summary

BrasilIntel is a competitive intelligence automation system for monitoring 897 Brazilian insurance companies across three segments (Health, Dental, Group Life). The system collects news from multiple sources, classifies content using LLM-based relevance scoring, and delivers daily intelligence reports to executives via email. This is a mature domain with established architectural patterns: ETL pipeline → AI classification → queue-based delivery → admin oversight.

**Recommended approach:** Build a multi-stage pipeline with FastAPI + SQLite foundation, Apify for scraping, Azure OpenAI for classification, and Microsoft Graph API for delivery. Use a bottom-up implementation strategy starting with a minimal vertical slice through all layers, then expand horizontally. The 2026 standard emphasizes resilient async operations, structured logging, type safety with Pydantic v2, and Docker containerization. Critical success factors include preventing scraping silent failures, detecting LLM accuracy drift, and avoiding alert fatigue through intelligent prioritization.

**Key risks and mitigation:** (1) **Scraping reliability** — implement health checks and baseline monitoring from day one; (2) **LLM accuracy drift** — establish validation dataset and continuous monitoring; (3) **Alert fatigue** — deploy relevance scoring and deduplication early to maintain 90%+ signal-to-noise ratio. These three risks account for majority of CI system failures in production.

## Key Findings

### Recommended Stack

Modern Python 3.12 async stack optimized for production reliability and maintainability. The architecture balances simplicity (SQLite, APScheduler) with proven robustness (FastAPI, HTTPX, structured logging). All components verified as of January 2026 via PyPI and official documentation.

**Core technologies:**
- **Python 3.12 + FastAPI 0.115+** — Industry standard for typed, async-first APIs with auto-validation and excellent DX; required for modern ASGI deployment
- **HTTPX 1.0+ + lxml 5.3+** — Modern async HTTP client (HTTP/2, connection pooling) paired with high-performance HTML parser (7x faster than BeautifulSoup)
- **Azure OpenAI SDK 2.16+ + Tenacity 9.0+** — Official SDK with Azure support, combined with exponential backoff retry logic (reduces failure rate by 97%)
- **Microsoft Graph API (msgraph-sdk 1.0+)** — Modern M365 email delivery with application permissions for daemon scenarios (replaces deprecated SMTP AUTH)
- **SQLite 3.45+ + Litestream 0.3+** — Zero-config serverless database with continuous backup to Azure Blob; handles 897 insurers easily (<1M rows)
- **APScheduler 3.10+** — Production-ready in-app scheduling with cron triggers, persistence, and async support; no external dependencies required
- **structlog 24.4+** — Production-standard structured logging with JSON output for CloudWatch/ELK integration and context injection
- **Jinja2 3.1+ + premailer 3.10+** — Industry standard HTML templating with CSS inlining for email client compatibility
- **Docker + Gunicorn + Uvicorn** — Container-first deployment on Windows with multi-worker ASGI server (2 workers per CPU core recommended)

**Critical version notes:**
- Pydantic v2 (2.11+) offers 5-10x performance improvement over v1
- Python 3.12 required for FastAPI and offers significant performance gains
- Use Batch API for all non-time-critical LLM calls (50% cost savings)

### Expected Features

Competitive intelligence systems have converged around three core capabilities: automated data collection with intelligent filtering, real-time alerting with sophisticated prioritization to combat alert fatigue, and executive-friendly dashboards with drill-down analytics. The market has matured beyond basic keyword tracking toward AI-powered relevance scoring and actionable intelligence distribution.

**Must have (table stakes):**
- **Automated news collection for 897 insurers** — Core value proposition; failure = no product
- **Status classification system (Critical/Watch/Monitor/Stable)** — Essential for executive decision-making and actionable prioritization
- **Daily scheduled reports with multi-recipient distribution** — Standard delivery mechanism; 5-10 executives expect consistent timing
- **Real-time alerts for Critical status** — Monitoring systems must notify immediately for high-priority events; delays = missed opportunities
- **Insurer database management + Excel import/export** — Foundation for monitoring scope; practical necessity for bulk operations
- **Basic admin UI** — Configuration management, insurer CRUD, report history, search/filter
- **Mobile-friendly reports** — Executives access reports on phones/tablets; responsive email templates required

**Should have (competitive):**
- **AI relevance scoring** — Industry leaders use GPT-4/Claude for importance ranking; eliminates low-value alerts and reduces noise by >90%
- **Insurance domain intelligence** — Context-aware analysis specific to Brazilian market; understands regulatory changes, market dynamics, competitive moves
- **Sentiment analysis** — Positive/negative/neutral scoring helps executives assess reputational impact
- **Executive summary generation** — One-paragraph daily distillation saves C-suite time; key differentiator
- **Trend detection across insurers** — Identify emerging market patterns before they become obvious; "3 health insurers expanded to São Paulo" = actionable trend

**Defer (v2+):**
- **Social media monitoring** — Scope creep; Brazilian insurance news primarily from traditional media and press releases
- **Real-time live dashboards** — Executive audience checks once daily, not hourly; creates unnecessary complexity
- **Full-text article storage** — Copyright issues and storage costs; store headlines, summaries, source links only
- **Collaborative annotation tools** — 5-10 recipients don't need Slack-like features; email replies sufficient
- **Deep historical trend analysis** — Greenfield system has no history; build basic archive first, add analytics after 6+ months data

### Architecture Approach

Multi-stage ETL pipeline architecture with distinct separation between collection, processing, classification, and delivery layers. The architecture emphasizes continuous monitoring over periodic checks, AI-driven classification for intelligence extraction, and queue-based delivery for reliability. Key principle: decouple collection from processing from delivery to enable independent scaling, failure recovery, and maintainability.

**Major components:**
1. **Orchestration Layer (Windows Scheduled Task)** — Triggers 3 daily pipeline runs per category (Health, Dental, Life); coordinates execution and error handling
2. **Data Collection Layer (Apify + HTTPX)** — Fetches raw content from 897 insurer websites; handles JS rendering, CAPTCHAs, IP rotation via Apify; stages to SQLite
3. **Processing & Classification Layer (Azure OpenAI)** — Multi-stage pipeline: Stage 1 (fast relevance filter 95% throughput) → Stage 2 (category classification 5% remaining) → Stage 3 (entity extraction); reduces LLM costs by 60-80%
4. **Persistence Layer (SQLite + WAL mode)** — Stores articles, insurers, classifications, audit logs; 99.9% of use cases don't need Postgres for <1M rows
5. **Delivery & Notification Layer (Microsoft Graph API)** — Queue-based email delivery with retry logic, exponential backoff, delivery confirmation polling
6. **Admin & Monitoring Layer (FastAPI)** — Web UI for configuration management, manual review, pipeline health monitoring, historical analytics

**Critical patterns to follow:**
- **Multi-stage LLM classification** — Use cheap models for relevance filtering, expensive models only for complex categorization (60-80% cost reduction)
- **Queue-based notification delivery** — Decouple report generation from email delivery using database-backed queue with retry logic
- **Session-per-request database** — FastAPI dependency injection for proper transaction boundaries and thread safety with SQLite
- **Configuration-driven pipeline** — Separate business logic (insurers, categories, rules) from code; enables non-technical management via admin UI

**Anti-patterns to avoid:**
- Synchronous processing without queues (email failures block pipeline, no retry capability)
- Using expensive LLMs for all classification (GPT-4 for simple filtering = $1000+ monthly waste)
- No idempotency in scheduled tasks (duplicate notifications, cannot retry safely)
- Hardcoded business logic (897 insurer configs in code = engineer bottleneck for changes)

### Critical Pitfalls

Research identified 13 domain-specific pitfalls with varying severity. Top 5 account for majority of CI system failures in production.

1. **Scraping without change detection → Silent failures** — News sites change HTML structure weekly; scrapers return 200 OK but extract zero articles; stakeholders don't notice for days/weeks. **Prevention:** Implement health checks validating article count baseline (±30%), content validation for expected patterns, alerting on empty responses. **Detection:** 30%+ article count drop over 7 days, increasing empty response ratio.

2. **LLM classification drift → Accuracy degradation without detection** — Classification accuracy degrades from 90%+ to 60-70% due to language evolution, domain changes, prompt assumptions; generates false positives (alert fatigue) and false negatives (missed intelligence). **Prevention:** Establish baseline metrics (F1, precision, recall) with 200-500 labeled validation set, weekly statistical tests, sample 50 articles weekly for manual review. **Detection:** Sudden classification volume spike (>2σ), user reports of irrelevant articles, confidence score distribution shift.

3. **Alert fatigue → Signal buried in noise** — 897 insurers generate 500-2000+ alerts daily; stakeholders ignore emails, miss critical moves, system becomes "shelfware" within 6 months. 47% of analysts cite alerting issues as #1 inefficiency. **Prevention:** Implement 0-100 relevance scoring beyond binary classification, deduplicate via embedding similarity (>0.85), use digest mode (daily/weekly) instead of real-time flood, priority tiers (Critical immediate, High daily, Medium weekly). **Detection:** Email open rates <30% after first month, user unsubscribe requests.

4. **Azure OpenAI cost explosion → Token usage spirals** — Initial $500-1000/month estimates explode to $5K-10K+ due to verbose prompts, no caching, using GPT-4 for simple tasks (15x cost vs GPT-3.5-mini). **Prevention:** Model tiering (use GPT-4o-mini $0.15/1M for classification), Batch API for non-time-critical (50% discount), prompt compression (<200 tokens), implement caching. **Detection:** Monthly token usage growing >50% without article increase, per-article cost >$0.10.

5. **Brazilian Portuguese NLP → Classification accuracy 15-25% lower** — Portuguese is resource-scarce (179/16,676 HuggingFace datasets); insurance jargon, regional slang, irony cause misclassification; pre-trained models optimized for European Portuguese struggle with Brazilian variants. **Prevention:** Use Portuguese-specific models (BERTimbau), provide 5-10 Portuguese examples in few-shot prompts, include insurance terminology glossary, maintain 500+ labeled Brazilian Portuguese validation set. **Detection:** Consistently lower confidence scores, user feedback on specific term/phrase misclassifications.

**Additional high-impact pitfalls:**
- **Windows Task Scheduler silent failures** — Minimal diagnostic context (error 0x1), no unified monitoring; 2026-01 KB5073723 caused credential prompt failures
- **Microsoft Graph API email asynchronous delivery failures** — Returns 202 Accepted but emails never delivered; trial tenant reputation issues; rate limits (150MB/5min, ~2000 messages/24h)
- **Apify rate limiting cascading failures** — 2026 anti-bot defenses (TLS fingerprinting, behavioral analysis) detect simple scrapers; 65.8% report increased proxy costs

## Implications for Roadmap

Based on research, recommended 6-phase structure emphasizing vertical slice first, then horizontal expansion:

### Phase 1: Foundation & Vertical Slice (Weeks 1-3)
**Rationale:** Validate architecture end-to-end before expanding horizontally; identifies integration issues early; provides working demo quickly; establishes critical monitoring baseline

**Delivers:** Minimal working pipeline: single insurer → Apify scraping → Azure OpenAI classification → SQLite storage → Microsoft Graph email → manual trigger (no scheduling yet)

**Addresses (from FEATURES.md):**
- Basic insurer database structure
- Simple LLM classification (single-stage initially)
- Email delivery foundation
- SQLite schema and persistence patterns

**Avoids (from PITFALLS.md):**
- Scraping without change detection (Pitfall #1) — implement health checks and baseline monitoring from day one
- No LLM accuracy baseline (Pitfall #2) — create 200-500 article validation dataset during this phase
- Corporate firewall blocks (Pitfall #10) — test connectivity from production environment early
- Legal/compliance violations (Pitfall #11) — legal review before any scraping implementation

**Critical success criteria:** Single end-to-end flow working, health checks reporting, baseline metrics established

**Research flags:** None — standard patterns well-documented

---

### Phase 2: Scale to 897 Insurers + Classification Pipeline (Weeks 4-6)
**Rationale:** Expand horizontal coverage after vertical slice proven; implement multi-stage classification to manage costs; add production resilience patterns; this phase transforms prototype into production-capable system

**Delivers:** Full insurer coverage (897 entities), multi-stage LLM pipeline (cheap filter → expensive categorization), Excel import/export, basic admin UI for insurer management, structured logging with JSON output

**Uses (from STACK.md):**
- APScheduler for daily scheduled runs (3x per category)
- Tenacity exponential backoff for API resilience
- structlog for production observability
- Batch API for cost optimization (50% savings)

**Implements (from ARCHITECTURE.md):**
- Multi-stage classification pipeline (60-80% cost reduction)
- Configuration-driven pipeline (database-managed insurer list)
- Session-per-request database pattern for admin UI
- Normalization and deduplication engine

**Avoids (from PITFALLS.md):**
- Cost explosion (Pitfall #4) — implement model tiering and Batch API from start
- Portuguese NLP issues (Pitfall #7) — use Portuguese-specific prompting with insurance glossary
- Inadequate deduplication (Pitfall #12) — implement embedding similarity clustering (>0.85 threshold)

**Critical success criteria:** 897 insurers monitored daily, costs <$1000/month, classification accuracy >80% for Portuguese content

**Research flags:**
- **Phase 2 needs research:** Portuguese-specific prompt engineering and validation (resource-scarce domain)
- **Phase 2 needs research:** Apify configuration for 897 concurrent sources with rate limiting

---

### Phase 3: Alert Prioritization & Delivery Reliability (Weeks 7-9)
**Rationale:** Address alert fatigue before launch (top cause of CI system abandonment); implement queue-based delivery for reliability; add real-time Critical alerts; this phase ensures stakeholder adoption and trust

**Delivers:** AI relevance scoring (0-100), status classification (Critical/Watch/Monitor/Stable), notification queue with retry logic, real-time Critical alerts, delivery confirmation polling, mobile-friendly email templates

**Uses (from STACK.md):**
- Jinja2 + premailer for responsive HTML emails
- Microsoft Graph API with application permissions
- SQLite notification queue table with retry tracking

**Implements (from ARCHITECTURE.md):**
- Queue-based notification delivery pattern (decouples processing from delivery)
- Report aggregation and formatting layer
- Priority-based routing (Critical = immediate, others = digest)

**Avoids (from PITFALLS.md):**
- Alert fatigue (Pitfall #3) — implement relevance scoring, deduplication, digest mode
- Email delivery failures (Pitfall #6) — add delivery confirmation polling, test sends, rate limiting
- No single source of truth (Pitfall #9) — centralized dashboard with role-based access

**Critical success criteria:** <10 Critical alerts per day per recipient, email open rates >50%, delivery confirmation >99%

**Research flags:** None — notification patterns well-established

---

### Phase 4: Production Hardening & Monitoring (Weeks 10-11)
**Rationale:** Add operational reliability before production launch; implement drift detection and monitoring; harden failure modes; this phase ensures long-term maintainability

**Delivers:** LLM drift detection with weekly validation, Litestream continuous SQLite backup to Azure Blob, external Task Scheduler monitoring (New Relic/equivalent), circuit breakers for rate limiting, comprehensive health dashboard

**Uses (from STACK.md):**
- Litestream for SQLite production backup
- structlog with Azure Log Analytics integration
- Windows Task Scheduler with external monitoring

**Implements (from ARCHITECTURE.md):**
- Monitoring and observability architecture (pipeline health, classification accuracy, delivery status)
- Error and retry flow with exponential backoff
- Idempotency for scheduled tasks (safe retries)

**Avoids (from PITFALLS.md):**
- LLM accuracy drift (Pitfall #2) — continuous monitoring, weekly statistical tests, alert thresholds
- Task Scheduler silent failures (Pitfall #5) — external monitoring, structured logging, heartbeat signals
- Rate limiting cascades (Pitfall #8) — circuit breakers, proxy reputation tracking, CAPTCHA solving

**Critical success criteria:** Monitoring alerts configured, backup validated, drift detection operational, no silent failures

**Research flags:** None — standard production hardening patterns

---

### Phase 5: Executive Intelligence Features (Weeks 12-14)
**Rationale:** Add competitive differentiators after core reliability proven; enhance intelligence value; focus on executive audience needs; these features drive adoption and demonstrate ROI

**Delivers:** Executive summary generation (one-paragraph daily distillation), sentiment analysis (positive/negative/neutral), competitive benchmarking ("Company X had 5 news items vs avg 2"), visual dashboard with insurer activity charts, two-way feedback mechanism

**Uses (from STACK.md):**
- Azure OpenAI for summary generation and sentiment
- FastAPI for interactive dashboard
- Embedding similarity for trend detection

**Implements (from ARCHITECTURE.md):**
- Report aggregation with AI-generated summaries
- Analytics queries for competitive context
- Feedback loop for continuous improvement

**Avoids (from PITFALLS.md):**
- Wrong stakeholder strategy (Pitfall #13) — tiered monitoring based on strategic insurer importance
- Generic BI dashboard (anti-feature) — domain-specific views emphasizing insurance context

**Critical success criteria:** Executive summaries rated useful >80%, sentiment accuracy >75%, dashboard engagement weekly

**Research flags:**
- **Phase 5 needs research:** Portuguese sentiment analysis models and accuracy expectations
- **Phase 5 needs research:** Executive summary prompt engineering for insurance domain

---

### Phase 6: Advanced Analytics & Integrations (Weeks 15+)
**Rationale:** Scale intelligence capabilities after adoption proven; add strategic insights; integrate with Marsh systems; these features maximize long-term value and system stickiness

**Delivers:** Trend detection across insurers (identify patterns before obvious), regulatory change detection (flag compliance shifts), cross-insurer pattern recognition, automated battlecards (competitive intelligence summaries), Marsh CRM/sales tool integrations, historical trend analysis (6+ months data)

**Uses (from STACK.md):**
- Azure OpenAI for trend and pattern detection
- Time-series analysis for historical insights
- REST APIs for Marsh system integration

**Implements (from ARCHITECTURE.md):**
- Advanced intelligence layer (domain-specific, regulatory, cross-insurer)
- Integration points with external systems
- Historical analytics requiring 6+ months baseline

**Avoids (from PITFALLS.md):**
- Premature historical analysis (anti-pattern) — wait for 6+ months data before deep trend analysis
- Social media monitoring (anti-feature) — stay focused on traditional media for Brazilian insurance

**Critical success criteria:** 3+ actionable trends identified monthly, regulatory changes detected within 24h, Marsh integration adoption >70%

**Research flags:**
- **Phase 6 needs research:** Marsh system integration APIs and authentication patterns
- **Phase 6 needs research:** Brazilian insurance regulatory data sources and classification

---

### Phase Ordering Rationale

**Why this order:**
1. **Vertical slice first (Phase 1)** prevents late-stage architectural failures; validates all integration points before scale
2. **Scale before features (Phase 2)** ensures infrastructure handles 897 insurers before adding complexity
3. **Alert quality before volume (Phase 3)** addresses top cause of CI system abandonment; stakeholder trust is fragile
4. **Reliability before intelligence (Phase 4)** ensures system stays operational; drift detection prevents gradual degradation
5. **Value features after stability (Phase 5-6)** maximizes ROI; advanced features useless if core unreliable

**Dependency-driven grouping:**
- Phase 1-2 establish data foundation (collection, storage, classification)
- Phase 3 builds delivery foundation (notifications, emails, prioritization)
- Phase 4 adds operational foundation (monitoring, reliability, drift detection)
- Phase 5-6 layer intelligence on stable foundation (summaries, trends, insights)

**Pitfall avoidance strategy:**
- Critical pitfalls (#1-3) addressed in Phases 1-3 before launch
- Production pitfalls (#4-8) hardened in Phase 4
- Strategic pitfalls (#9, #13) prevented via Phase 5-6 stakeholder focus

**Research-informed decisions:**
- Multi-stage classification (Phase 2) prevents cost explosion — research shows 60-80% savings
- Queue-based delivery (Phase 3) prevents silent failures — standard pattern for reliability
- Drift detection (Phase 4) catches accuracy degradation — research shows gradual trust erosion without monitoring
- Portuguese-specific validation (all phases) accounts for resource scarcity — research shows 15-25% accuracy penalty

### Research Flags

**Phases needing deeper research during planning:**

- **Phase 2 (Insurer Scale):**
  - **Portuguese prompt engineering:** Resource-scarce domain with limited examples; need validation of few-shot prompts and insurance terminology effectiveness
  - **Apify 897-source configuration:** Rate limiting strategy for concurrent scraping; proxy rotation patterns; CAPTCHA solving integration; need cost/performance benchmarking

- **Phase 5 (Executive Intelligence):**
  - **Portuguese sentiment analysis:** Accuracy expectations for Brazilian Portuguese insurance content; model selection (BERTimbau vs multilingual); need baseline establishment
  - **Executive summary prompts:** Distillation of technical insurance content for C-suite audience; prompt engineering for one-paragraph summaries; need stakeholder validation

- **Phase 6 (Advanced Analytics):**
  - **Marsh integration APIs:** Authentication patterns, data formats, rate limits for CRM/sales tools; need technical documentation and access
  - **Brazilian regulatory sources:** Identification of SUSEP and ANS data feeds; classification patterns for regulatory changes; need domain expert consultation

**Phases with standard patterns (skip research-phase):**

- **Phase 1 (Foundation):** FastAPI + SQLite + Azure OpenAI + Graph API are well-documented; vertical slice pattern standard
- **Phase 3 (Alert Delivery):** Queue-based notification and email reliability patterns established; no novel integration challenges
- **Phase 4 (Production Hardening):** Monitoring, logging, backup patterns mature; drift detection frameworks documented

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | All versions verified via PyPI as of January 2026; FastAPI/Pydantic/HTTPX proven for production async Python; Azure OpenAI SDK official with Azure support |
| Features | **HIGH** | Competitive intelligence patterns validated across 30+ industry sources; table stakes vs differentiators clear from market analysis; anti-features verified via failure case studies |
| Architecture | **MEDIUM** | Multi-stage pipeline patterns well-documented; notification delivery proven; specific Apify integration less documented; SQLite limits need validation for 897 insurers × 3 categories |
| Pitfalls | **HIGH** | Top 5 pitfalls validated with current (2026) industry sources; scraping challenges documented in state-of-web-scraping report; LLM drift patterns confirmed in multiple production case studies |

**Overall confidence:** **HIGH**

Research synthesis supported by 100+ sources including official documentation (Microsoft, OpenAI, FastAPI), industry reports (Apify 2026 web scraping state, competitive intelligence analyses), and production case studies. Architecture patterns validated across multiple authoritative references. Technology stack verified against current (January 2026) versions via PyPI.

### Gaps to Address

Areas where research was inconclusive or needs validation during implementation:

- **Portuguese classification accuracy baseline:** Limited production examples for Brazilian Portuguese insurance content; need to establish realistic accuracy targets (research suggests 70-75% baseline vs 85-90% for English) and validate with domain-specific validation dataset. **Handle:** Create 500+ labeled article validation set during Phase 1; run accuracy experiments with multiple prompt strategies.

- **SQLite performance at scale:** Research confirms SQLite handles <1M rows easily, but specific performance for 897 insurers × 3 categories × daily runs (potential write contention during pipeline runs) needs validation. **Handle:** Benchmark write performance with WAL mode during Phase 2; monitor for "database locked" errors; document PostgreSQL migration path if needed.

- **Microsoft Graph API rate limits for use case:** Documentation shows 150MB/5min per mailbox and ~2000 messages/24h for shared mailboxes, but specific impact of 3 daily emails × 5-10 recipients needs testing. **Handle:** Test under realistic load during Phase 3; implement client-side throttling at 80% of limits; consider Azure Communication Services for high-volume scenarios.

- **Apify cost/performance for 897 sources:** Apify handles parallel execution well, but specific cost (per-insurer scraping cost) and performance (success rate, execution time) for Brazilian news sites needs measurement. **Handle:** Run cost analysis during Phase 2 with representative sample; validate against budget; document Scrapy migration path for cost optimization if needed.

- **LLM multi-stage classification thresholds:** Research validates pattern but optimal stage 1 filter threshold (what % of articles pass to stage 2?) requires experimentation with actual data. **Handle:** A/B test multiple threshold configurations during Phase 2; measure precision/recall and cost impact; iterate based on production metrics.

- **Brazilian insurance domain terminology coverage:** Insurance jargon and regulatory terms may not be well-represented in Azure OpenAI training data; need to validate classification accuracy for domain-specific content. **Handle:** Collaborate with Marsh insurance experts to build terminology glossary during Phase 1; include in system prompts; measure accuracy improvement on validation set.

## Sources

### Stack Research (HIGH confidence)
**Primary sources — Official documentation and verified 2026 versions:**
- PyPI package pages (fastapi 0.115, pydantic 2.11, httpx 1.0, openai 2.16) — January 2026 verification
- [FastAPI SQL Databases Tutorial](https://fastapi.tiangolo.com/tutorial/sql-databases/) — Official patterns
- [Azure OpenAI Python SDK](https://learn.microsoft.com/en-us/graph/tutorials/python-email) — Microsoft official
- [Microsoft Graph Email Tutorial](https://learn.microsoft.com/en-us/graph/tutorials/python-email) — M365 integration
- [Python Job Scheduling 2026](https://research.aimultiple.com/python-job-scheduling/) — APScheduler comparison
- [Tenacity Retries 2026](https://johal.in/tenacity-retries-exponential-backoff-decorators-2026/) — Resilience patterns

**Secondary sources — Industry best practices:**
- [FastAPI Production Deployment](https://render.com/articles/fastapi-production-deployment-best-practices) — Production patterns
- [Docker Best Practices 2026](https://thinksys.com/devops/docker-best-practices/) — Container optimization

### Features Research (HIGH confidence)
**Primary sources — Competitive intelligence tool reviews:**
- [11 Best Competitive Intelligence Tools 2026](https://www.contify.com/resources/blog/best-competitive-intelligence-tools/)
- [10 Best AI Tools for Competitor Analysis 2026](https://visualping.io/blog/best-ai-tools-competitor-analysis)
- [19 Best Competitive Intelligence Software 2026](https://thecmo.com/tools/best-competitive-intelligence-software/)
- [14 Best Media Monitoring Tools 2026](https://www.stateofdigitalpublishing.com/digital-platform-tools/best-media-monitoring-tools/)

**Secondary sources — Insurance industry intelligence:**
- [Competitive Intelligence for Insurance Industry](https://risk.lexisnexis.com/insights-resources/blog-post/mastering-insurance-market-dynamics-with-competitive-intelligence)
- [Alert Fatigue SOC 2026](https://torq.io/blog/cybersecurity-alert-management-2026/) — Applicable to CI systems

### Architecture Research (MEDIUM confidence)
**Primary sources — Pipeline architecture patterns:**
- [Data Pipeline Architecture Explained](https://www.montecarlodata.com/blog-data-pipeline-architecture-explained/)
- [LLM Orchestration 2026](https://research.aimultiple.com/llm-orchestration/)
- [Multi-Stage LLM Classification](https://www.emergentmind.com/topics/multi-stage-llm-based-classification-pipeline)
- [Scalable Notification Service Design](https://blog.algomaster.io/p/design-a-scalable-notification-service)

**Secondary sources — FastAPI + SQLite patterns:**
- [Modern FastAPI Architecture Patterns](https://medium.com/algomart/modern-fastapi-architecture-patterns-for-scalable-production-systems-41a87b165a8b)
- [Building Scalable FastAPI with SQLModel](https://medium.com/@faizulkhan56/building-a-scalable-fastapi-application-with-sqlmodel-a-complete-guide-to-three-layer-architecture-3c33ec981922)

### Pitfalls Research (HIGH confidence)
**Primary sources — Production failure modes:**
- [State of Web Scraping Report 2026](https://blog.apify.com/web-scraping-report-2026/) — Industry survey
- [LLM Monitoring: Drift and Failures](https://medium.com/@kuldeep.paul08/llm-monitoring-detecting-drift-hallucinations-and-failures-1028055c1d34)
- [Data Drift in LLMs 2026](https://nexla.com/ai-infrastructure/data-drift/)
- [Azure OpenAI Pricing 2026](https://inference.net/content/azure-openai-pricing-explained/)
- [OpenAI Cost Optimization Guide](https://www.finout.io/blog/openai-cost-optimization-a-practical-guide)
- [Alert Fatigue Killing SOC 2026](https://torq.io/blog/cybersecurity-alert-management-2026/)

**Secondary sources — Domain-specific challenges:**
- [Portuguese NLP Resources](https://github.com/ajdavidl/Portuguese-NLP)
- [Windows Task Scheduler Diagnostics](https://www.jamsscheduler.com/blog/windows-task-scheduler-error-diagnostics/)
- [Graph API Email Delivery Issues](https://learn.microsoft.com/en-us/graph/outlook-things-to-know-about-send-mail)
- [7 Common CI Mistakes](https://klue.com/blog/competitive-intelligence-framework-problems)

---

*Research completed: 2026-02-04*
*Ready for roadmap: yes*
