# Roadmap: BrasilIntel

## Milestones

- ✅ **v1.0 MVP** - Phases 1-8 (shipped 2026-02-05)
- 🚧 **v1.1 Enterprise API Integration** - Phases 9-14 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-8) - SHIPPED 2026-02-05</summary>

Full archive: `.planning/milestones/v1.0-ROADMAP.md`

Phases 1-8 delivered: data foundation, vertical slice validation, 6-source news collection at scale, AI classification pipeline, professional branded reports, email delivery with PDF and alerts, APScheduler automation, and complete admin dashboard.

41 plans total. 63 requirements validated.

</details>

---

### 🚧 v1.1 Enterprise API Integration (In Progress)

**Milestone Goal:** Replace Apify web scraping with Factiva/Dow Jones as the sole news source, add inline equity price data for tracked Brazilian insurance companies, extend admin dashboard with enterprise API visibility, and clean up legacy Apify infrastructure — porting the proven enterprise integration patterns from MDInsights into BrasilIntel.

---

#### Phase 9: Enterprise API Foundation

**Goal**: The system can authenticate with the MMC Core API platform and all API activity is observable through a persistent event log
**Depends on**: Phase 8 (v1.0 complete)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04
**Success Criteria** (what must be TRUE):
  1. Pipeline acquires a valid JWT token from MMC Access Management API before making any enterprise API call
  2. A token acquired near expiry is automatically refreshed with 5-minute margin — pipeline never fails mid-request due to an expired token
  3. Every enterprise API call (token request, news fetch, equity lookup, email send) writes a record to the api_events table visible in the database
  4. When token acquisition fails, the pipeline continues without crashing — enterprise features are skipped and the failure is logged
**Plans**: 3 plans

Plans:
- [x] 09-01-PLAN.md — Config expansion: MMC Core API credential fields, helper methods, tenacity dependency, .env.example
- [x] 09-02-PLAN.md — ORM models + migration: ApiEvent, FactivaConfig, EquityTicker models, migration 007, main.py registration
- [x] 09-03-PLAN.md — TokenManager + test_auth.py: OAuth2 client credentials auth, proactive refresh, event logging, validation script

#### Phase 10: Factiva News Collection

**Goal**: The pipeline collects a batch of Brazilian insurance news from Factiva via MMC Core API, fetches full article bodies, deduplicates, and normalizes articles into BrasilIntel's NewsItem schema
**Depends on**: Phase 9
**Requirements**: FACT-01, FACT-02, FACT-03, FACT-05, FACT-07
**Success Criteria** (what must be TRUE):
  1. Running the pipeline fetches a batch of news articles from the Factiva Recent News endpoint using Brazilian insurance industry codes and Portuguese keywords
  2. Full article body text is retrieved for each article (not just headlines)
  3. Articles that appear more than once within the batch are removed before processing (URL dedup + semantic similarity threshold)
  4. Each surviving Factiva article is stored with all required fields: title, description, source_url, source_name, published_at, and source badge indicating "Factiva"
**Plans**: 3 plans

Plans:
- [x] 10-01-PLAN.md — FactivaCollector: complete API client with search, article body fetch, normalization, ApiEvent recording, and FactivaConfig seed script
- [x] 10-02-PLAN.md — ArticleDeduplicator: sentence-transformers semantic dedup with UnionFind grouping, add sentence-transformers dependency
- [x] 10-03-PLAN.md — Integration test: test_factiva.py end-to-end validation (collect, URL dedup, semantic dedup, field validation)

#### Phase 11: Insurer Matching Pipeline

**Goal**: Every Factiva article is matched to one or more of the 897 tracked insurers and Factiva is the sole active news collection path in the pipeline
**Depends on**: Phase 10
**Requirements**: FACT-04, FACT-06
**Success Criteria** (what must be TRUE):
  1. After a pipeline run, each article stored in the database has at least one insurer_id assignment drawn from the 897 tracked insurers
  2. Articles clearly mentioning a specific insurer by name or known search term are matched without AI involvement (deterministic path)
  3. Ambiguous articles are sent to Azure OpenAI for insurer identification — the model receives insurer name/search_term context and returns a structured match result
  4. The pipeline collection step invokes Factiva — there is no Apify code path remaining in the active collection flow
**Plans**: 3 plans

Plans:
- [x] 11-01-PLAN.md — Deterministic insurer matcher: MatchResult schema + InsurerMatcher with name/search_term word-boundary matching, Portuguese accent normalization
- [x] 11-02-PLAN.md — AI-assisted insurer matcher: AIInsurerMatcher with Azure OpenAI structured output for ambiguous articles, ApiEvent logging
- [x] 11-03-PLAN.md — Pipeline integration: rewrite runs.py to use FactivaCollector + dedup + insurer matching, remove Apify from active flow, sentinel insurer for unmatched

#### Phase 12: Equity Price Enrichment

**Goal**: Tracked Brazilian insurance companies display inline equity data (ticker, price, change%) in both browser and email reports
**Depends on**: Phase 9
**Requirements**: EQTY-01, EQTY-02, EQTY-03, EQTY-04
**Success Criteria** (what must be TRUE):
  1. After a pipeline run, equity price data for configured B3 tickers is fetched from the MMC Core API Equity Price endpoint and stored
  2. Admin can add, edit, and delete insurer-to-ticker mappings (e.g., "SulAmerica" → "SULA11") through the admin dashboard
  3. Browser report pages show equity chips (ticker symbol, current price, percentage change) next to insurer sections that have a configured ticker
  4. Email reports show the same equity data in a table-compatible layout that renders correctly in Outlook and Gmail
**Plans**: 3 plans

Plans:
- [x] 12-01-PLAN.md — EquityPriceClient service port + pipeline equity enrichment integration
- [x] 12-02-PLAN.md — Admin ticker CRUD routes, equity.html template, sidebar nav, seed defaults
- [x] 12-03-PLAN.md — Report equity chip display (email-compatible inline styles in report_professional.html)

#### Phase 13: Admin Dashboard Extensions

**Goal**: The admin dashboard surfaces enterprise API health, exposes credential and query configuration, and labels Factiva-sourced articles
**Depends on**: Phase 9, Phase 12
**Requirements**: ADMN-17, ADMN-18, ADMN-19, ADMN-20, ADMN-22
**Success Criteria** (what must be TRUE):
  1. Dashboard home page shows an enterprise API health panel with current auth status, API connectivity indicator, and timestamps of last successful and failed requests
  2. Admin can enter and save MMC Core API credentials (API key, client ID, client secret) through a settings page without editing environment variables
  3. Admin can configure Factiva query parameters (industry codes, Portuguese keywords, date range) through a dedicated page that immediately affects the next pipeline run
  4. Admin can add, edit, and delete equity ticker mappings through the dedicated tickers page (CRUD operations persist to database) -- ALREADY COMPLETE (Phase 12-02)
  5. Article listings in the admin show a "Factiva" source badge on articles collected from Factiva
**Plans**: 3 plans

Plans:
- [ ] 13-01-PLAN.md — Enterprise API health panel + fallback event log on dashboard (ADMN-17)
- [ ] 13-02-PLAN.md — Enterprise Config credentials page + Factiva query config page with date range (ADMN-18, ADMN-19)
- [ ] 13-03-PLAN.md — Factiva source badges in report templates (ADMN-22)

#### Phase 14: Apify Cleanup

**Goal**: All Apify scraping infrastructure is removed from the codebase and the project reflects Factiva as the only news collection mechanism
**Depends on**: Phase 11 (Factiva pipeline confirmed working)
**Requirements**: CLNP-01, CLNP-02, CLNP-03, CLNP-04
**Success Criteria** (what must be TRUE):
  1. No Apify source class files exist in the codebase (base.py, google_news.py, valor.py, infomoney.py, cqcs.py, estadao.py, rss_source.py, ans.py under app/services/sources/ are removed)
  2. requirements.txt contains no apify-client or feedparser entries
  3. The pipeline collection step has no conditional branch for Apify — only the Factiva path exists
  4. .env.example contains MMC Core API variables and APIFY_TOKEN is absent
**Plans**: TBD

Plans:
- [ ] 14-01: Remove Apify source classes, base class, and __init__ registrations; remove apify-client and feedparser from requirements.txt
- [ ] 14-02: Scrub pipeline of Apify branching; update .env.example and documentation

---

## Progress

**Execution Order:** 9 → 10 → 11 → 12 → 13 → 14
Note: Phase 12 depends only on Phase 9 (not Phase 10/11) and may parallelize with Phase 10/11 if desired, but sequential execution is the default.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation & Data Layer | v1.0 | 4/4 | Complete | 2026-02-05 |
| 2. Vertical Slice Validation | v1.0 | 9/9 | Complete | 2026-02-05 |
| 3. News Collection Scale | v1.0 | 6/6 | Complete | 2026-02-05 |
| 4. AI Classification Pipeline | v1.0 | 4/4 | Complete | 2026-02-05 |
| 5. Professional Reporting | v1.0 | 5/5 | Complete | 2026-02-05 |
| 6. Email Delivery & Alerts | v1.0 | 4/4 | Complete | 2026-02-05 |
| 7. Scheduling & Automation | v1.0 | 4/4 | Complete | 2026-02-05 |
| 8. Admin Interface | v1.0 | 6/6 | Complete | 2026-02-05 |
| 9. Enterprise API Foundation | v1.1 | 3/3 | Complete | 2026-02-19 |
| 10. Factiva News Collection | v1.1 | 3/3 | Complete | 2026-02-19 |
| 11. Insurer Matching Pipeline | v1.1 | 3/3 | Complete | 2026-02-19 |
| 12. Equity Price Enrichment | v1.1 | 3/3 | Complete | 2026-02-19 |
| 13. Admin Dashboard Extensions | v1.1 | 0/3 | Not started | - |
| 14. Apify Cleanup | v1.1 | 0/2 | Not started | - |
