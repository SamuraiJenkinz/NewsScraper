# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Senior management at Marsh Brasil receives actionable intelligence reports on their monitored insurers daily, with zero manual effort.
**Current focus:** v1.1 Enterprise API Integration — Phase 9: COMPLETE, Phase 10 next

## Current Position

Phase: 11 of 15 (Insurer Matching Pipeline) — IN PROGRESS
Plan: 1 of 3 in current phase
Status: In progress
Last activity: 2026-02-19 — Completed 11-01-PLAN.md (Deterministic insurer matching)

Progress: v1.0 [##########] 100% | v1.1 [#####.....] 53%

## Performance Metrics

**v1.0 Velocity (reference):**
- Total plans completed: 41
- Average duration: ~10 min
- Total execution time: ~7.0 hours

**v1.1 Velocity:**
- Total plans completed: 8
- Average duration: 7.1 min
- Total execution time: 57 min

**By Phase (v1.1):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 9. Enterprise API Foundation | 3/3 COMPLETE | 7 min | 2.3 min |
| 10. Factiva News Collection | 3/3 COMPLETE | 48 min | 16 min |
| 11. Insurer Matching Pipeline | 1/3 | 2 min | 2 min |

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

### Pending Todos

None.

### Blockers/Concerns

- **ACTION REQUIRED before Phase 11 testing:** Staging MMC credentials must be added to .env and validated with `python scripts/test_auth.py` (Phase 9) and `python scripts/test_factiva.py` (Phase 10)
- Phase 11 insurer matching complexity: 897 insurers, batch articles, AI disambiguation cost needs monitoring
- First semantic dedup run downloads all-MiniLM-L6-v2 model (~80MB, ~30s) — may trigger during Phase 11 pipeline dev
- Cleanup (Phase 15) must NOT run until Phase 11 is confirmed working in pipeline
- Windows Long Path error with msgraph-sdk on `pip install -r requirements.txt` — pre-existing, not caused by Phase 9

## Session Continuity

Last session: 2026-02-20T01:16:05Z
Stopped at: Completed 11-01-PLAN.md — Deterministic insurer matching with Portuguese accent normalization
Resume file: .planning/phases/11-insurer-matching-pipeline/11-01-SUMMARY.md

---
*Initialized: 2026-02-04*
*Last updated: 2026-02-19 after 11-01 completion*
