# Project Milestones: BrasilIntel

## v1.1 Enterprise API Integration (Shipped: 2026-02-20)

**Delivered:** Replaced all 6 Apify web scrapers with Factiva/Dow Jones enterprise news via MMC Core API, added inline B3 equity price data for tracked Brazilian insurers, and extended the admin dashboard with enterprise API health monitoring, credential management, and Factiva configuration.

**Phases completed:** 9-14 (17 plans total)

**Key accomplishments:**
- OAuth2 client credentials TokenManager with proactive 5-min token refresh and ApiEvent observability
- FactivaCollector API client for Brazilian insurance news via Dow Jones/Factiva with semantic deduplication
- Deterministic insurer matching for 897 tracked insurers with Portuguese accent normalization + AI disambiguation via Azure OpenAI
- Inline B3 equity price data (R$ format) in browser and email reports with admin ticker CRUD
- Admin dashboard: enterprise API health panel, credential management UI, Factiva query config, Factiva source badges
- Complete Apify removal: 2,900 lines of legacy scraping infrastructure deleted, Factiva as sole news path

**Stats:**
- 107 files created/modified (16,611 insertions, 3,224 deletions)
- 10,286 lines of Python (app/)
- 6 phases, 17 plans
- 2 days from start to ship (2026-02-19 → 2026-02-20)

**Git range:** `83a3487` → `799c694`

**Requirements:** 22/22 shipped (5 EEML requirements intentionally removed — Graph API retained)

**What's next:** Production deployment with MMC staging credentials, email visual QA

---

## v1.0 MVP (Shipped: 2026-02-05)

**Delivered:** Complete automated competitive intelligence system for Marsh Brasil that monitors 897 insurers, scrapes 6 news sources, classifies with Azure OpenAI, and delivers professional branded reports via email.

**Phases completed:** 1-8 (41 plans total)

**Key accomplishments:**
- SQLite database with 897 insurers, full Excel import/export with validation
- End-to-end pipeline: Google News + 5 Brazilian sources → Azure OpenAI classification → Microsoft Graph email
- Professional Marsh-branded HTML reports with mobile responsiveness and PDF generation
- APScheduler automation with configurable cron (6/7/8 AM São Paulo time)
- Critical alert system for immediate notification of high-priority status changes
- Complete admin dashboard with HTMX-powered real-time updates

**Stats:**
- 57 Python files, 16 HTML templates
- 11,057 lines of Python
- 8 phases, 41 plans
- 1 day from start to ship (2026-02-04)

**Git range:** `bd9f94b` → `cd76e14`

**Known gap:** Recipients page is read-only (ADMN-10/11) — design decision, configured via environment variables

**What's next:** Production deployment and user feedback collection

---
