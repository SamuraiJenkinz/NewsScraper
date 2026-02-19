# Requirements: BrasilIntel v1.1 Enterprise API Integration

## Milestone Requirements

### Authentication (AUTH)

- [ ] **AUTH-01**: System acquires JWT tokens via OAuth2 client credentials grant from MMC Access Management API
- [ ] **AUTH-02**: Token refresh happens proactively (5-min margin before expiry) so pipeline never hits mid-request expiry
- [ ] **AUTH-03**: All API interactions (token requests, news fetches, equity lookups, email sends) are logged to an api_events table for observability
- [ ] **AUTH-04**: When authentication fails, pipeline logs the failure and skips enterprise features gracefully (no silent crashes)

### Factiva News Collection (FACT)

- [ ] **FACT-01**: Pipeline collects news via MMC Core API Recent News (Factiva/Dow Jones) endpoint using X-Api-Key authentication
- [ ] **FACT-02**: Factiva queries use Brazilian insurance industry codes and Portuguese keywords to fetch relevant articles in batch
- [ ] **FACT-03**: Individual article bodies are fetched from Factiva for full-text content (not just headlines)
- [ ] **FACT-04**: AI-assisted matching assigns each Factiva article to one or more of the 897 tracked insurers using insurer names, search_terms, and Azure OpenAI for ambiguous cases
- [ ] **FACT-05**: Factiva articles are normalized to BrasilIntel's NewsItem schema (title, description, source_url, source_name, published_at, insurer_id)
- [ ] **FACT-06**: Factiva replaces all 6 Apify/RSS sources as the sole news collection mechanism — no fallback path
- [ ] **FACT-07**: Duplicate articles are detected and filtered (URL dedup + semantic dedup within batch)

### Equity Price Enrichment (EQTY)

- [ ] **EQTY-01**: Equity price data is retrieved via MMC Core API Equity Price endpoint for tracked Brazilian insurance companies
- [ ] **EQTY-02**: Admin can configure entity-to-ticker mappings (insurer name → B3 stock ticker) via the admin dashboard
- [ ] **EQTY-03**: Browser reports display inline equity chips (ticker, price, change%) alongside relevant insurer news
- [ ] **EQTY-04**: Email reports display inline equity data in table-based layout compatible with Outlook and Gmail

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
| AUTH-01 | — | — | Pending |
| AUTH-02 | — | — | Pending |
| AUTH-03 | — | — | Pending |
| AUTH-04 | — | — | Pending |
| FACT-01 | — | — | Pending |
| FACT-02 | — | — | Pending |
| FACT-03 | — | — | Pending |
| FACT-04 | — | — | Pending |
| FACT-05 | — | — | Pending |
| FACT-06 | — | — | Pending |
| FACT-07 | — | — | Pending |
| EQTY-01 | — | — | Pending |
| EQTY-02 | — | — | Pending |
| EQTY-03 | — | — | Pending |
| EQTY-04 | — | — | Pending |
| EEML-01 | — | — | Pending |
| EEML-02 | — | — | Pending |
| EEML-03 | — | — | Pending |
| EEML-04 | — | — | Pending |
| EEML-05 | — | — | Pending |
| ADMN-17 | — | — | Pending |
| ADMN-18 | — | — | Pending |
| ADMN-19 | — | — | Pending |
| ADMN-20 | — | — | Pending |
| ADMN-21 | — | — | Pending |
| ADMN-22 | — | — | Pending |
| CLNP-01 | — | — | Pending |
| CLNP-02 | — | — | Pending |
| CLNP-03 | — | — | Pending |
| CLNP-04 | — | — | Pending |

---
*Created: 2026-02-19 for milestone v1.1*
