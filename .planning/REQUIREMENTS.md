# Requirements: BrasilIntel v1.1 Enterprise API Integration

## Milestone Requirements

### Authentication (AUTH)

- [ ] **AUTH-01**: System acquires JWT tokens via OAuth2 client credentials grant from MMC Access Management API
- [ ] **AUTH-02**: Token refresh happens proactively (5-min margin before expiry) so pipeline never hits mid-request expiry
- [ ] **AUTH-03**: All API interactions (token requests, news fetches, equity lookups, email sends) are logged to an api_events table for observability
- [ ] **AUTH-04**: When authentication fails, pipeline logs the failure and skips enterprise features gracefully (no silent crashes)

### Factiva News Collection (FACT)

- [x] **FACT-01**: Pipeline collects news via MMC Core API Recent News (Factiva/Dow Jones) endpoint using X-Api-Key authentication
- [x] **FACT-02**: Factiva queries use Brazilian insurance industry codes and Portuguese keywords to fetch relevant articles in batch
- [x] **FACT-03**: Individual article bodies are fetched from Factiva for full-text content (not just headlines)
- [x] **FACT-04**: AI-assisted matching assigns each Factiva article to one or more of the 897 tracked insurers using insurer names, search_terms, and Azure OpenAI for ambiguous cases
- [x] **FACT-05**: Factiva articles are normalized to BrasilIntel's NewsItem schema (title, description, source_url, source_name, published_at, insurer_id)
- [x] **FACT-06**: Factiva replaces all 6 Apify/RSS sources as the sole news collection mechanism — no fallback path
- [x] **FACT-07**: Duplicate articles are detected and filtered (URL dedup + semantic dedup within batch)

### Equity Price Enrichment (EQTY)

- [x] **EQTY-01**: Equity price data is retrieved via MMC Core API Equity Price endpoint for tracked Brazilian insurance companies
- [x] **EQTY-02**: Admin can configure entity-to-ticker mappings (insurer name → B3 stock ticker) via the admin dashboard
- [x] **EQTY-03**: Browser reports display inline equity chips (ticker, price, change%) alongside relevant insurer news
- [x] **EQTY-04**: Email reports display inline equity data in table-based layout compatible with Outlook and Gmail

### Enterprise Email Delivery (EEML)

- [ ] **EEML-01**: Reports are delivered via MMC Core API Email endpoint as the primary delivery method
- [ ] **EEML-02**: Enterprise email uses JWT Bearer + X-Api-Key authentication (tokens from AUTH-01)
- [ ] **EEML-03**: When enterprise email fails for a category, delivery falls back to existing Graph API email automatically
- [ ] **EEML-04**: PDF attachments are included in enterprise email delivery (matching current Graph API behavior)
- [ ] **EEML-05**: Run record tracks which delivery method succeeded (enterprise, Graph fallback, or failed)

### Admin Dashboard Extensions (ADMN)

- [ ] **ADMN-17**: Dashboard shows enterprise API health panel (auth status, API connectivity, last success/failure times)
- [ ] **ADMN-18**: Admin can configure MMC Core API credentials (API key, client ID, client secret) via settings UI
- [ ] **ADMN-19**: Admin can configure Factiva query parameters (industry codes, keywords, date range) via dedicated page
- [ ] **ADMN-20**: Admin can manage equity ticker mappings (insurer → B3 ticker CRUD) via dedicated page
- [ ] **ADMN-21**: Dashboard shows fallback event log (enterprise → Graph fallback history with timestamps and reasons)
- [ ] **ADMN-22**: Article listings show source badge indicating Factiva attribution

### Cleanup (CLNP)

- [ ] **CLNP-01**: All 6 Apify scraper source classes and base class are removed from codebase
- [ ] **CLNP-02**: apify-client and feedparser dependencies are removed from requirements.txt
- [ ] **CLNP-03**: Pipeline collection step uses Factiva-only path (no fallback branching)
- [ ] **CLNP-04**: .env.example is updated with MMC Core API configuration variables (replacing APIFY_TOKEN)

## Future Requirements

- Historical equity price trends (charts over time) — deferred to v2
- Multi-language Factiva queries (English + Portuguese) — evaluate after v1.1 usage data
- Real-time Factiva streaming — daily batch sufficient for current audience

## Out of Scope

- Apify/RSS fallback for news collection — Factiva is strict/sole source per user decision
- Direct Factiva API access (bypassing MMC Core API) — must use corporate Apigee gateway
- Per-insurer Factiva queries — batch query with post-hoc insurer matching is more efficient
- Editable recipients via UI — remains env var config (unchanged from v1.0)

## Traceability

| Requirement | Phase | Plan | Status |
|-------------|-------|------|--------|
| AUTH-01 | Phase 9 | 09-03 | Complete |
| AUTH-02 | Phase 9 | 09-03 | Complete |
| AUTH-03 | Phase 9 | 09-01, 09-02, 09-03 | Complete |
| AUTH-04 | Phase 9 | 09-03 | Complete |
| FACT-01 | Phase 10 | 10-01 | Complete |
| FACT-02 | Phase 10 | 10-01 | Complete |
| FACT-03 | Phase 10 | 10-01 | Complete |
| FACT-04 | Phase 11 | 11-01, 11-02 | Complete |
| FACT-05 | Phase 10 | 10-01 | Complete |
| FACT-06 | Phase 11 | 11-03 | Complete |
| FACT-07 | Phase 10 | 10-02, 10-03 | Complete |
| EQTY-01 | Phase 12 | 12-01 | Complete |
| EQTY-02 | Phase 12 | 12-02 | Complete |
| EQTY-03 | Phase 12 | 12-03 | Complete |
| EQTY-04 | Phase 12 | 12-03 | Complete |
| EEML-01 | Phase 13 | 13-01 | Pending |
| EEML-02 | Phase 13 | 13-01 | Pending |
| EEML-03 | Phase 13 | 13-02 | Pending |
| EEML-04 | Phase 13 | 13-01 | Pending |
| EEML-05 | Phase 13 | 13-02 | Pending |
| ADMN-17 | Phase 14 | 14-01 | Pending |
| ADMN-18 | Phase 14 | 14-02 | Pending |
| ADMN-19 | Phase 14 | 14-03 | Pending |
| ADMN-20 | Phase 12 | 12-02 | Complete |
| ADMN-21 | Phase 14 | 14-04 | Pending |
| ADMN-22 | Phase 14 | 14-05 | Pending |
| CLNP-01 | Phase 15 | 15-01 | Pending |
| CLNP-02 | Phase 15 | 15-01 | Pending |
| CLNP-03 | Phase 15 | 15-02 | Pending |
| CLNP-04 | Phase 15 | 15-02 | Pending |

---
*Created: 2026-02-19 for milestone v1.1*
*Traceability updated: 2026-02-19 after roadmap creation*
