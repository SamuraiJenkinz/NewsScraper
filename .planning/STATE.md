# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Senior management at Marsh Brasil receives actionable intelligence reports on their monitored insurers daily, with zero manual effort.
**Current focus:** v1.1 Enterprise API Integration — Phase 9: COMPLETE, Phase 10 next

## Current Position

Phase: 9 of 15 (Enterprise API Foundation) — COMPLETE
Plan: 3 of 3 in current phase (all plans done)
Status: Phase complete — ready for Phase 10
Last activity: 2026-02-19 — Completed 09-03-PLAN.md (OAuth2 TokenManager + test_auth.py)

Progress: v1.0 [##########] 100% | v1.1 [###.......] 30%

## Performance Metrics

**v1.0 Velocity (reference):**
- Total plans completed: 41
- Average duration: ~10 min
- Total execution time: ~7.0 hours

**v1.1 Velocity:**
- Total plans completed: 3
- Average duration: 2.3 min
- Total execution time: 7 min

**By Phase (v1.1):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 9. Enterprise API Foundation | 3/3 COMPLETE | 7 min | 2.3 min |

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

### Pending Todos

None.

### Blockers/Concerns

- **ACTION REQUIRED before Phase 10:** Staging MMC credentials must be added to .env and validated with `python scripts/test_auth.py` — run passes exit code 0 confirms auth works
- Phase 11 insurer matching complexity: 897 insurers, batch articles, AI disambiguation cost needs monitoring
- Cleanup (Phase 15) must NOT run until Phase 11 is confirmed working in pipeline
- Windows Long Path error with msgraph-sdk on `pip install -r requirements.txt` — pre-existing, not caused by Phase 9

## Session Continuity

Last session: 2026-02-19T18:53:46Z
Stopped at: Completed 09-03-PLAN.md — OAuth2 TokenManager (app/auth/token_manager.py) + test_auth.py
Resume file: .planning/phases/09-enterprise-api-foundation/09-03-SUMMARY.md

---
*Initialized: 2026-02-04*
*Last updated: 2026-02-19 after 09-03 completion (Phase 9 COMPLETE)*
