# Roadmap: BrasilIntel

## Overview

BrasilIntel delivers daily competitive intelligence to Marsh Brasil executives through an 8-phase journey: establish data foundation and validate architecture with a vertical slice, scale to 897 insurers across all news sources, build the AI classification pipeline, create professional branded reports, implement reliable delivery with critical alerts, automate scheduling, and complete the admin interface. Each phase delivers verifiable user value, building from core persistence through production-ready automation.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation & Data Layer** - Core persistence, insurer database, Excel import/export
- [x] **Phase 2: Vertical Slice Validation** - Single-source end-to-end pipeline proof
- [x] **Phase 3: News Collection Scale** - All sources, 897 insurers, production scraping
- [ ] **Phase 4: AI Classification Pipeline** - Full Azure OpenAI classification system
- [ ] **Phase 5: Professional Reporting** - Marsh-branded HTML reports with all sections
- [ ] **Phase 6: Delivery & Critical Alerts** - Email delivery, PDF generation, alert routing
- [ ] **Phase 7: Scheduling & Automation** - APScheduler jobs, cron config, run tracking
- [ ] **Phase 8: Admin Interface** - Complete web dashboard with all management pages

## Phase Details

### Phase 1: Foundation & Data Layer
**Goal**: Establish SQLite database schema and insurer management capabilities with Excel integration
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, DATA-08
**Success Criteria** (what must be TRUE):
  1. Admin can upload Excel file and see 897 insurers imported into SQLite database
  2. Admin can search for any insurer by name or ANS code and edit details
  3. Admin can export current insurer list as Excel file matching original format
  4. System rejects duplicate ANS codes and shows clear validation errors
  5. System validates all required fields (ANS Code, Name, Category) before import commit
**Plans**: 4 plans in 3 waves

Plans:
- [x] 01-01-PLAN.md — Project scaffolding, database setup, Insurer model and schemas
- [x] 01-02-PLAN.md — Insurer CRUD endpoints with search and filter
- [x] 01-03-PLAN.md — Excel import with preview-before-commit workflow
- [x] 01-04-PLAN.md — Excel export and complete data management cycle

### Phase 2: Vertical Slice Validation
**Goal**: Prove end-to-end architecture with minimal single-source pipeline (Google News → Azure OpenAI → Email)
**Depends on**: Phase 1
**Requirements**: NEWS-01, CLASS-01, CLASS-03, REPT-01, DELV-01, DEPL-01, DEPL-02, DEPL-03, DEPL-04, DEPL-05, DEPL-06, DEPL-07, DEPL-08, DEPL-09
**Success Criteria** (what must be TRUE):
  1. System scrapes Google News for one insurer and stores news items in database
  2. Azure OpenAI classifies insurer status (Critical/Watch/Monitor/Stable) based on news content
  3. Azure OpenAI generates bullet-point summary for each news item
  4. System generates basic HTML report for one category with classified insurer
  5. System sends report via Microsoft Graph API email to configured recipient
  6. Application runs in Docker container on Windows 11 and deploys via Windows Scheduled Task on Windows Server
  7. Health check endpoint returns system status at /api/health
**Plans**: 9 plans in 4 waves

Plans:
- [x] 02-01-PLAN.md — Database models for NewsItem and Run tracking
- [x] 02-02-PLAN.md — Configuration module with pydantic-settings
- [x] 02-03-PLAN.md — Apify scraper service for Google News
- [x] 02-04-PLAN.md — Azure OpenAI classification service with structured outputs
- [x] 02-05-PLAN.md — Microsoft Graph email service
- [x] 02-06-PLAN.md — HTML report generator with Jinja2 templates
- [x] 02-07-PLAN.md — Run orchestration endpoint (/api/runs/execute)
- [x] 02-08-PLAN.md — Docker deployment (Dockerfile, docker-compose.yml)
- [x] 02-09-PLAN.md — Windows Scheduled Task deployment and enhanced health check

### Phase 3: News Collection Scale
**Goal**: Scale scraping to all 6 news sources with batch processing for 897 insurers
**Depends on**: Phase 2
**Requirements**: NEWS-02, NEWS-03, NEWS-04, NEWS-05, NEWS-06, NEWS-07, NEWS-08, NEWS-09, NEWS-10
**Success Criteria** (what must be TRUE):
  1. System scrapes all 6 sources (Google News, Valor Econômico, InfoMoney, CQCS, ANS, Broadcast/Estadão)
  2. System processes 897 insurers in configurable batches (30-50 at a time) with rate limiting
  3. System stores news items with complete metadata (title, summary, URL, source, date)
  4. System links each news item to specific insurer and run record for traceability
  5. AI relevance scoring filters out low-value content before classification
**Plans**: 6 plans in 4 waves

Plans:
- [x] 03-01-PLAN.md — Source abstraction base and Google News refactor
- [x] 03-02-PLAN.md — RSS sources (InfoMoney, Estadao/G1, ANS)
- [x] 03-03-PLAN.md — Website crawler sources (Valor, CQCS) and batch config
- [x] 03-04-PLAN.md — Batch processor with semaphore-based rate limiting
- [x] 03-05-PLAN.md — AI relevance scoring pre-filter
- [x] 03-06-PLAN.md — Scraper integration and run endpoint update

### Phase 4: AI Classification Pipeline
**Goal**: Complete Azure OpenAI classification with sentiment analysis and configurable toggle
**Depends on**: Phase 3
**Requirements**: CLASS-02, CLASS-04, CLASS-05, CLASS-06
**Success Criteria** (what must be TRUE):
  1. Azure OpenAI classifies insurer status based on financial crisis, regulatory action, M&A, leadership changes
  2. Azure OpenAI assigns sentiment (positive/negative/neutral) to each news item
  3. Classification results stored with insurer records and accessible in reports
  4. LLM summarization can be toggled on/off via USE_LLM_SUMMARY configuration flag
**Plans**: TBD

Plans:
- [ ] 04-01: TBD during planning
- [ ] 04-02: TBD during planning

### Phase 5: Professional Reporting
**Goal**: Generate complete Marsh-branded HTML reports with all sections and mobile responsiveness
**Depends on**: Phase 4
**Requirements**: REPT-02, REPT-03, REPT-04, REPT-05, REPT-06, REPT-07, REPT-08, REPT-09, REPT-10, REPT-11, REPT-12, REPT-13
**Success Criteria** (what must be TRUE):
  1. Reports match Marsh branding (colors, layout) from reference HTML designs
  2. Reports include confidential banner, executive summary cards (Critical/Warning/Positive), coverage table
  3. Reports group insurers by status priority (Critical first, then Watch, Monitor, Stable)
  4. Each insurer section shows news items with icons, titles, impact tags, source attribution
  5. Reports include market context section and strategic recommendations section
  6. Azure OpenAI generates executive summary paragraph for each report
  7. Reports render correctly on mobile devices (responsive HTML)
  8. Admin can browse and view historical reports by date and category in archive
**Plans**: TBD

Plans:
- [ ] 05-01: TBD during planning
- [ ] 05-02: TBD during planning

### Phase 6: Delivery & Critical Alerts
**Goal**: Reliable email delivery with PDF attachment, recipient management, and immediate critical alerts
**Depends on**: Phase 5
**Requirements**: DELV-02, DELV-03, DELV-04, DELV-05, DELV-06, DELV-07, DELV-08
**Success Criteria** (what must be TRUE):
  1. Email supports TO, CC, BCC recipient lists configurable per product category
  2. Recipients are configurable per product category (Health, Dental, Group Life)
  3. System sends immediate separate alert email when Critical status detected
  4. Critical alerts sent separately from daily digest reports
  5. System generates PDF version of each report and attaches to email
  6. System tracks email delivery status per run and reports success/failure
**Plans**: TBD

Plans:
- [ ] 06-01: TBD during planning
- [ ] 06-02: TBD during planning

### Phase 7: Scheduling & Automation
**Goal**: Automated daily runs with APScheduler, configurable cron, manual triggers, and run tracking
**Depends on**: Phase 6
**Requirements**: SCHD-01, SCHD-02, SCHD-03, SCHD-04, SCHD-05, SCHD-06, SCHD-07
**Success Criteria** (what must be TRUE):
  1. System runs 3 scheduled jobs (Health 6 AM, Dental 7 AM, Group Life 8 AM São Paulo time)
  2. Admin can modify cron expression for each category via configuration
  3. Admin can enable/disable each scheduled job independently
  4. Admin can trigger manual run for any category via admin UI button
  5. System tracks run history (started, completed, status, items found, errors)
  6. System displays next scheduled run time for each category on dashboard
**Plans**: TBD

Plans:
- [ ] 07-01: TBD during planning
- [ ] 07-02: TBD during planning

### Phase 8: Admin Interface
**Goal**: Complete web dashboard with all management pages, authentication, and settings
**Depends on**: Phase 7
**Requirements**: ADMN-01, ADMN-02, ADMN-03, ADMN-04, ADMN-05, ADMN-06, ADMN-07, ADMN-08, ADMN-09, ADMN-10, ADMN-11, ADMN-12, ADMN-13, ADMN-14, ADMN-15, ADMN-16
**Success Criteria** (what must be TRUE):
  1. Web dashboard accessible at configured port (default 3000) with basic authentication
  2. Dashboard shows summary cards per category (insurer count, last run, next run, system status)
  3. Dashboard shows recent reports list with quick view links
  4. Insurers page has category tabs, search, status filters, and bulk enable/disable operations
  5. Import page has drag-and-drop file upload with preview and validation errors before commit
  6. Recipients page supports add/edit/remove recipient with category subscription checkboxes
  7. Schedules page shows each category with cron expression, next run time, enable/disable toggle, and manual trigger button
  8. Settings page configures company branding (name, classification level) and scraping config (batch size, timeout, lookback days)
  9. API keys displayed masked with reveal toggle for security
**Plans**: TBD

Plans:
- [ ] 08-01: TBD during planning
- [ ] 08-02: TBD during planning

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Data Layer | 4/4 | Complete | 2026-02-04 |
| 2. Vertical Slice Validation | 9/9 | Complete | 2026-02-04 |
| 3. News Collection Scale | 6/6 | Complete | 2026-02-04 |
| 4. AI Classification Pipeline | 0/TBD | Not started | - |
| 5. Professional Reporting | 0/TBD | Not started | - |
| 6. Delivery & Critical Alerts | 0/TBD | Not started | - |
| 7. Scheduling & Automation | 0/TBD | Not started | - |
| 8. Admin Interface | 0/TBD | Not started | - |

---
*Roadmap created: 2026-02-04*
*Last updated: 2026-02-04*
