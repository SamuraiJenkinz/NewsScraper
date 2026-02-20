# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Senior management at Marsh Brasil receives actionable intelligence reports on their monitored insurers daily, with zero manual effort.
**Current focus:** v1.1 Enterprise API Integration — Phase 12: COMPLETE, Phase 13 (Admin Dashboard Extensions) next

## Current Position

Phase: 13 of 14 (Admin Dashboard Extensions) — IN PROGRESS
Plan: 2 of 3 complete (13-01, 13-03)
Status: In progress
Last activity: 2026-02-20 — Completed 13-03-PLAN.md (Factiva source badges in reports)

Progress: v1.0 [##########] 100% | v1.1 [#######▪..] 73%

## Performance Metrics

**v1.0 Velocity (reference):**
- Total plans completed: 41
- Average duration: ~10 min
- Total execution time: ~7.0 hours

**v1.1 Velocity:**
- Total plans completed: 14
- Average duration: 6.6 min
- Total execution time: 92 min

**By Phase (v1.1):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 9. Enterprise API Foundation | 3/3 COMPLETE | 7 min | 2.3 min |
| 10. Factiva News Collection | 3/3 COMPLETE | 48 min | 16 min |
| 11. Insurer Matching Pipeline | 3/3 COMPLETE | 17 min | 5.7 min |
| 12. Equity Price Enrichment | 3/3 COMPLETE | 29 min | 9.7 min |
| 13. Admin Dashboard Extensions | 2/3 IN PROGRESS | 4 min | 2.0 min |

*Updated after each plan completion*

## Accumulated Context

### Decisions

All v1.0 decisions logged in PROJECT.md Key Decisions table.

v1.1 decisions:
| Decision | Outcome | Phase |
|----------|---------|-------|
| Factiva over Apify | Enterprise Dow Jones feed more reliable; proven in MDInsights | Pre-planning |
| Port from MDInsights | Adapt enterprise modules directly (MMCAuthService, FactivaClient, EnterpriseEmailer, EquityClient) | Pre-planning |
| Industry codes + keywords | Batch Factiva query with post-hoc AI insurer matching (not per-insurer queries) | Pre-planning |
| mmc_sender_name default | Empty string (not "Kevin Taylor") — BrasilIntel sender identity deferred to Phase 13 | 09-01 |
| Three separate config guards | is_mmc_auth_configured, is_mmc_api_key_configured, is_mmc_email_configured — granular per-service checks | 09-01 |
| MMC env vars commented out | All MMC_ vars commented out in .env.example — app boots safely without enterprise credentials | 09-01 |
| EquityTicker.exchange = BVMF | Default exchange is B3 (Brazilian) not NYSE — BrasilIntel targets Brazilian market | 09-02 |
| Single migration 007 | All three Phase 9-12 tables created upfront — avoids per-phase migration scripts | 09-02 |
| ApiEvent.run_id nullable | Out-of-pipeline calls (auth test scripts) can log events without a run context | 09-02 |
| logging_config.py absent in BrasilIntel | test_auth.py uses stdlib logging.basicConfig(WARNING) instead of configure_logging() | 09-03 |
| structlog kept in TokenManager | structlog IS installed in BrasilIntel — no substitution needed from MDInsights port | 09-03 |
| 48-hour date window | Factiva collect() uses timedelta(days=2) not timedelta(days=1) — cross-run dedup overlap | 10-01 |
| source_url field name | BrasilIntel NewsItem uses source_url, MDInsights uses url — normalization adapted | 10-01 |
| No collector_source field | MDInsights-specific field omitted from BrasilIntel normalization | 10-01 |
| Brazilian insurance codes | i82, i8200, i82001, i82002, i82003 — batch query for entire sector, AI matches insurers post-hoc | 10-01 |
| Portuguese insurance keywords | 9 terms (seguro, seguradora, resseguro, etc.) for broad coverage, AI classifier filters relevance | 10-01 |
| page_size=50 default | Balance coverage and API cost, MAX_ARTICLES=100 hard cap prevents runaway charges | 10-01 |
| Inline FactivaConfig seeding | test_factiva.py creates FactivaConfig id=1 if missing — removes seed script dependency | 10-03 |
| URL dedup before semantic | Explicit URL dedup before embeddings — avoids embedding duplicates, ~40% speedup | 10-03 |
| Exit 0 for unconfigured | test_factiva.py exits 0 (not error) when credentials missing — expected state for new checkouts | 10-03 |
| 4-char threshold | Deterministic matcher skips names <4 chars (Sul, Amil, Porto) — routes to AI to avoid false positives | 11-01 |
| NFKD normalization | unicodedata.normalize('NFKD') handles Portuguese accents (SulAmérica = SulAmerica) | 11-01 |
| Word-boundary regex | \b{re.escape(name)}\b prevents substring false positives (Porto doesn't match 'reportar') | 11-01 |
| Multi-match limit 2-3 | Articles mentioning 2-3 insurers return deterministic_multi; >3 routed to AI | 11-01 |
| Confidence scoring | Single match 0.95, multi-match 0.85, unmatched 0.0 | 11-01 |
| MAX_INSURER_CONTEXT=200 | AI matcher limits insurer context to 200 entries (token optimization), sorts enabled=True first | 11-02 |
| Reuse NEWS_FETCH for AI | ApiEventType.NEWS_FETCH reused for AI matching (api_name='ai_matcher' distinguishes from Factiva) | 11-02 |
| AI hallucination guard | Filter returned insurer_ids to only include valid IDs from provided list | 11-02 |
| Portuguese AI prompt | System prompt in Portuguese for consistency with classifier.py output style | 11-02 |
| Sentinel insurer for unmatched | "Noticias Gerais" (ANS 000000) stores unmatched articles — ensures no data loss | 11-03 |
| 3-insurer cap per article | Multi-insurer articles capped at 3 NewsItem rows to prevent runaway duplication | 11-03 |
| Category-filtered matching | Each run only matches against insurers in requested category (Health, Dental, or Group Life) | 11-03 |
| insurer_id deprecated | ExecuteRequest.insurer_id deprecated — batch Factiva collection doesn't support per-insurer filtering | 11-03 |
| Default exchange BVMF | EquityPriceClient defaults to BVMF (B3) not NYSE — BrasilIntel targets Brazilian insurers | 12-01 |
| Direct port from MDInsights | EquityPriceClient ported with zero logic changes — only docstrings and default exchange adapted | 12-01 |
| Per-run ticker caching | Equity enrichment caches prices by "TICKER:EXCHANGE" key to prevent duplicate API calls within a run | 12-01 |
| Graceful equity degradation | Pipeline continues normally when MMC API unconfigured — enrichment returns empty dict | 12-01 |
| equity_data threading | equity_data dict passed through to reporter now, will be rendered in Phase 12-03 | 12-01 |
| BVMF default in UI | Admin equity form pre-fills exchange with "BVMF" — BrasilIntel targets Brazilian market (B3) | 12-02 |
| Edit form in same page | equity.html handles list and edit modes via edit_ticker parameter (not separate template) | 12-02 |
| Inline styles only | BrasilIntel has ONE template for browser AND email — all equity chip styles must be inline for Outlook/Gmail | 12-03 |
| HTML entities for arrows | &#9650; &#9660; instead of Unicode — safer cross-client display in Outlook Word engine | 12-03 |
| R$ Brazilian Real format | Equity chips show R$ not $ — matches local currency for B3 Brazilian insurers | 12-03 |
| Inline-block layout | Single equity chip uses inline-block not table — simpler markup, email-safe | 12-03 |
| Chip placement | Equity chips between insurer name and code badges — visual hierarchy: Name → Price → Codes → News | 12-03 |
| Stay with Graph API | Enterprise email delivery removed — Graph API sufficient, no MMC email port needed | Pre-13 |
| Phase renumber | Old Phase 13 (Enterprise Email) removed, 14→13 (Admin Dashboard), 15→14 (Apify Cleanup) | Pre-13 |
| BrasilIntel has 3 enterprise APIs | auth, news, equity only — email not yet implemented in Phase 13 (unlike MDInsights) | 13-01 |
| Overall status from most recent | API status = most recent event (success or failure); degraded if fallback, offline if failure | 13-01 |
| Separate timestamp queries | Query most recent success AND failure separately for full visibility into API behavior over time | 13-01 |
| Fallback log includes TOKEN_FAILED | Auth failures visible in ops log alongside NEWS_FALLBACK, EQUITY_FALLBACK, EMAIL_FALLBACK | 13-01 |
| Dow Jones blue for Factiva | #0077c8 badge color — brand consistency with MDInsights Factiva identity | 13-03 |
| Inline badge styles only | All badge styles inline (no CSS classes) — email client compatibility for Outlook/Gmail | 13-03 |
| Conditional Factiva badge | Badge only when source_name == 'Factiva' — backward compatible with legacy Apify sources | 13-03 |

### Pending Todos

None.

### Blockers/Concerns

- **ACTION REQUIRED before Phase 12 testing:** Staging MMC credentials must be added to .env and validated with `python scripts/test_auth.py` (Phase 9) and `python scripts/test_factiva.py` (Phase 10)
- **Phase 12 COMPLETE:** Equity enrichment end-to-end ready — pipeline enrichment (12-01), admin UI (12-02), report display (12-03)
- **Phase 13 Plans 13-01 and 13-03 COMPLETE:** Enterprise API health panel (13-01) and Factiva source badges (13-03) ready
- **Enterprise Email Delivery REMOVED:** Staying with Graph API for email delivery — Phase 13 removed, phases renumbered
- **Email visual QA recommended:** Both equity chips AND Factiva badges use inline styles for Outlook/Gmail compatibility — real email client testing needed before production deployment
- First production run will validate complete pipeline: Factiva → matcher → classifier → equity enrichment → report delivery with badges
- Sentinel insurer may accumulate noise — admin dashboard should provide filtering/hiding
- 3-insurer cap may be restrictive for industry-wide news — monitor in production
- AI matching costs will increase with Factiva volume — ApiEvent monitoring critical for Phase 13
- Old ScraperService functions remain unused (technical debt) — remove in future cleanup phase
- Windows Long Path error with msgraph-sdk on `pip install -r requirements.txt` — pre-existing, not caused by Phase 9

## Session Continuity

Last session: 2026-02-20T07:16:00Z
Stopped at: Completed 13-03-PLAN.md — Factiva source badges in all report templates
Resume file: .planning/phases/13-admin-dashboard-extensions/13-03-SUMMARY.md

---
*Initialized: 2026-02-04*
*Last updated: 2026-02-20 after 13-03 completion (Phase 13: 2 of 3 plans COMPLETE)*
