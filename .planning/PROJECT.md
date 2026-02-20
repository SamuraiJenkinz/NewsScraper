# BrasilIntel

## What This Is

Automated competitive intelligence system for Marsh Brasil that monitors 897 Brazilian insurers across Health, Dental, and Group Life categories. The system collects news from Factiva/Dow Jones via MMC Core API, uses Azure OpenAI to summarize and classify insurer status, enriches reports with inline B3 equity price data, and generates polished daily HTML reports with PDF attachments for senior management — replacing manual web searches and report compilation.

## Core Value

Senior management at Marsh Brasil receives actionable, professionally-formatted intelligence reports on their monitored insurers daily, with zero manual effort.

## Current State

**Version:** v1.1 Enterprise API Integration (shipped 2026-02-20)
**Codebase:** 10,286 lines of Python across app/, 20+ HTML templates
**Tech Stack:** Python 3.11, FastAPI, SQLite, MMC Core API (Factiva + Equity), Azure OpenAI, Microsoft Graph, WeasyPrint, APScheduler, HTMX, sentence-transformers

## Requirements

### Validated

- DATA-01 through DATA-08 — v1.0 (insurer database with Excel import/export)
- NEWS-01 through NEWS-10 — v1.0 (news collection with batch processing)
- CLASS-01 through CLASS-06 — v1.0 (Azure OpenAI classification with sentiment)
- REPT-01 through REPT-13 — v1.0 (professional Marsh-branded reports with archival)
- DELV-01 through DELV-08 — v1.0 (email delivery with PDF and critical alerts)
- SCHD-01 through SCHD-07 — v1.0 (APScheduler automation)
- ADMN-01 through ADMN-16 — v1.0 (complete admin dashboard; ADMN-10/11 read-only by design)
- DEPL-01 through DEPL-09 — v1.0 (Docker and Windows deployment)
- AUTH-01 through AUTH-04 — v1.1 (OAuth2 JWT token management with proactive refresh)
- FACT-01 through FACT-07 — v1.1 (Factiva news collection, insurer matching, deduplication)
- EQTY-01 through EQTY-04 — v1.1 (equity price enrichment with admin ticker management)
- ADMN-17 through ADMN-22 — v1.1 (API health, enterprise config, Factiva config, source badges)
- CLNP-01 through CLNP-04 — v1.1 (complete Apify removal, Factiva as sole source)

### Active

(None — planning next milestone)

### Out of Scope

- Real-time notifications — daily batch reports sufficient for use case
- Mobile app — web dashboard accessible from any device
- Multi-tenant / SaaS — single deployment for Marsh Brasil
- Custom report designer — templates are fixed to Marsh branding
- Historical trend analysis — focus on current news, not analytics (v2 candidate)
- Portuguese language UI — English admin interface acceptable
- Editable recipients via UI — environment variable configuration acceptable
- Enterprise email via MMC Core API — Graph API sufficient (EEML-01-05 deferred)
- Direct Factiva API access — must use corporate Apigee gateway
- Per-insurer Factiva queries — batch query with post-hoc matching more efficient

## Context

**Business Context:**
- Previous state: Manual web searches and report compilation by DDH team
- Current state: Automated daily intelligence with enterprise-grade Factiva news and equity data
- Users: Senior management at Marsh Brasil (5-10 recipients per category)
- Data source: DDH partner database of 897 insurers
- News source: Factiva/Dow Jones via MMC Core API (replaced Apify scraping in v1.1)

**Technical Environment:**
- Corporate M365 Exchange Online (Graph API for email)
- Azure AD for authentication
- Azure OpenAI (corporate LLM deployment)
- MMC Core API platform (Apigee) — staging credentials available (shared with MDInsights)
- Windows Server on AWS (production)
- Windows 11 (development)

**Sister Project:**
- MDInsights (v1.0 shipped) provided the enterprise API integration patterns ported to BrasilIntel. Same tech stack, same MMC Core API credentials.

**Key Identifiers:**
- ANS Code: Brazilian regulatory registration number
- Market Master: Marsh global system code (216 of 897 insurers have this)

## Constraints

- **Tech Stack**: Python 3.11+, FastAPI, SQLite, MMC Core API, Azure OpenAI SDK, Microsoft Graph SDK, sentence-transformers
- **Corporate Auth**: Azure AD app registration for Graph API and Azure OpenAI access; OAuth2 client credentials for MMC Core API
- **Deployment**: Docker (local dev) and Windows Scheduled Task (production)
- **Branding**: Reports must match Marsh visual identity
- **Data Volume**: 897 insurers, batch Factiva collection per category
- **Timezone**: All schedules in America/Sao_Paulo

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python over Node.js | Better Azure SDK support, stronger data processing | Good |
| FastAPI over Flask | Modern async support, automatic OpenAPI docs | Good |
| SQLite over PostgreSQL | Zero config, portable, sufficient for single deployment | Good |
| Windows Scheduled Task over Service | Simpler deployment, matches existing patterns | Good |
| 3 separate scheduled jobs | Staggered runs, independent failures | Good |
| HTMX over React/Vue | SPA-like UX without frontend build complexity | Good |
| HTTP Basic auth | Simple, sufficient for internal tool | Good |
| Read-only recipients | Env var config acceptable for MVP scope | Acceptable |
| WeasyPrint for PDF | Native Python, good CSS support | Good |
| Factiva over Apify for news | Enterprise Dow Jones feed more reliable than web scraping; proven in MDInsights | Good |
| Port from MDInsights | Adapt enterprise modules directly (TokenManager, FactivaCollector, EquityPriceClient) | Good |
| Industry codes + keywords for Factiva | Batch query by Brazilian insurance codes, AI matches insurers post-hoc | Good |
| Stay with Graph API email | Enterprise email via MMC Core API deferred — Graph API sufficient | Good |
| Inline styles only for email | All report UI elements (equity chips, Factiva badges) use inline styles for Outlook/Gmail | Good |
| R$ Brazilian Real format | Equity chips show R$ not $ — matches local currency for B3 insurers | Good |
| Sentinel insurer for unmatched | "Noticias Gerais" (ANS 000000) prevents data loss from unmatched articles | Good |
| 4-char threshold for deterministic matching | Short insurer names (Sul, Amil) route to AI to avoid false positives | Good |
| Semantic dedup at 0.85 threshold | UnionFind grouping removes duplicate wire-service articles | Good |

---
*Last updated: 2026-02-20 after v1.1 milestone completion*
