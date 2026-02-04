# BrasilIntel

## What This Is

Automated competitive intelligence system for Marsh Brasil that monitors 897 Brazilian insurers across Health, Dental, and Group Life categories. The system scrapes news from multiple Brazilian and international sources, uses Azure OpenAI to summarize and classify insurer status, and generates polished daily HTML reports for senior management — replacing manual web searches and report compilation.

## Core Value

Senior management at Marsh Brasil receives actionable, professionally-formatted intelligence reports on their monitored insurers daily, with zero manual effort.

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Data Management**
- [ ] Import insurers from Excel spreadsheet (ANS Code, Name, CNPJ, Product Category, Market Master)
- [ ] Support 897 insurers across 3 categories: Health (515), Dental (237), Group Life (145)
- [ ] Admin UI for viewing/editing/enabling/disabling insurers
- [ ] Bulk spreadsheet upload with preview, merge, and replace modes
- [ ] Export current insurer data as Excel

**News Scraping**
- [ ] Integrate Apify SDK for web scraping
- [ ] Scrape Google News for insurer mentions
- [ ] Scrape Brazilian sources: Valor Econômico, InfoMoney, CQCS, ANS releases, Broadcast/Estadão
- [ ] Build search queries using insurer name + ANS code
- [ ] Batch processing (30-50 insurers at a time) with rate limiting
- [ ] Store news items linked to insurers and runs

**AI Classification**
- [ ] Integrate Azure OpenAI for news summarization
- [ ] Generate concise bullet-point summaries for each news item
- [ ] Classify insurer status: Critical, Watch, Monitor, Stable
- [ ] Generate executive summary for report
- [ ] Configurable LLM toggle (USE_LLM_SUMMARY)

**Report Generation**
- [ ] 3 separate daily reports: Health, Dental, Group Life
- [ ] Match Marsh branding from reference HTML designs
- [ ] Executive summary with key findings cards
- [ ] Insurers grouped by status priority (Critical first)
- [ ] News items with icons, impact tags, source attribution
- [ ] Market context section
- [ ] Strategic recommendations
- [ ] PDF export via headless browser
- [ ] Report archive with viewing history

**Scheduling & Delivery**
- [ ] 3 scheduled jobs (one per product category)
- [ ] Configurable cron expressions (default: 6 AM, 7 AM, 8 AM São Paulo time)
- [ ] Manual trigger via API and admin UI
- [ ] Email delivery via Microsoft Graph API
- [ ] TO/CC/BCC recipient support per product category
- [ ] Track run history and delivery status

**Admin Web UI**
- [ ] Dashboard with category summary cards
- [ ] Insurers management page with category filters
- [ ] Recipients page with subscription management
- [ ] Schedules page with cron configuration
- [ ] Import/export page with drag-drop upload
- [ ] Settings page (company branding, API keys, scrape settings)
- [ ] Basic authentication

**Deployment**
- [ ] Docker container for local Windows 11 development
- [ ] Python venv + Windows Scheduled Task for production (Windows Server)
- [ ] PowerShell management scripts (setup, status, run-now, logs)
- [ ] SQLite database (portable, file-based)

### Out of Scope

- Real-time notifications — daily batch reports sufficient for use case
- Mobile app — web dashboard accessible from any device
- Multi-tenant / SaaS — single deployment for Marsh Brasil
- Custom report designer — templates are fixed to Marsh branding
- Historical trend analysis — focus on current news, not analytics
- Portuguese language UI — English admin interface acceptable

## Context

**Business Context:**
- Current state: Manual web searches and report compilation by DDH team
- Target state: Automated daily intelligence with zero manual effort
- Users: Senior management at Marsh Brasil (5-10 recipients per category)
- Data source: DDH partner database of 897 insurers (provided as ByCat3.xlsx)

**Technical Environment:**
- Corporate M365 Exchange Online (Graph API for email)
- Azure AD for authentication
- Azure OpenAI (corporate LLM deployment)
- Apify account for web scraping
- Windows Server on AWS (production)
- Windows 11 (development)

**Key Identifiers:**
- ANS Code: Brazilian regulatory registration number (Agência Nacional de Saúde Suplementar)
- Market Master: Marsh global system code (indicates Marsh Compliance registration)
- 216 of 897 insurers have Market Master codes

**Reference Materials:**
- Architecture document: `refchyt/ARCHITECTURE.md`
- Insurer data: `refchyt/ByCat3.xlsx`
- Report designs: `refchyt/2026-02-03_health_insurer_intelligence_report.html`, `refchyt/2026-02-03_competitor_intelligence_report.html`
- Environment config: `refchyt/.env.example`
- Deployment scripts: `refchyt/deploy/setup_scheduled_task.ps1`, `refchyt/deploy/manage_service.ps1`

## Constraints

- **Tech Stack**: Python 3.11+, FastAPI, SQLite, Apify SDK, Azure OpenAI SDK, Microsoft Graph SDK — chosen for data processing strength, corporate Azure integration, and Windows deployment compatibility
- **Corporate Auth**: Must use Azure AD app registration for Graph API and Azure OpenAI access
- **Deployment**: Must support both Docker (local dev) and Windows Scheduled Task (production) from same codebase
- **Branding**: Reports must match Marsh visual identity (colors, layout) from reference HTML files
- **Data Volume**: 897 insurers across 3 categories, ~15-30 min scrape time per category
- **Timezone**: All schedules in America/Sao_Paulo

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python over Node.js | Better Azure SDK support, stronger data processing, aligns with existing deployment patterns | — Pending |
| FastAPI over Flask | Modern async support, automatic OpenAPI docs, better for concurrent scraping | — Pending |
| SQLite over PostgreSQL | Zero config, portable, sufficient for single-deployment use case | — Pending |
| Windows Scheduled Task over Windows Service | Simpler deployment, matches existing patterns, easier debugging | — Pending |
| Apify over direct scraping | Proven infrastructure, handles rate limiting, reliable actors | — Pending |
| 3 separate scheduled jobs | Allows staggered runs, independent failures, targeted email distribution | — Pending |

---
*Last updated: 2026-02-04 after initialization*
