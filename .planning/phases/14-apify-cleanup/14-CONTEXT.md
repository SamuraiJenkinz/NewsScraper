# Phase 14: Apify Cleanup - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove all Apify web scraping infrastructure from the codebase. After this phase, Factiva is the sole news collection mechanism. No Apify source files, dependencies, pipeline branches, or environment variables remain. Historical data in the database is preserved.

</domain>

<decisions>
## Implementation Decisions

### Historical data handling
- Keep existing Apify-sourced articles in the database untouched — source_name stays as-is ('Google News', 'Valor Economico', etc.)
- Keep existing Source model records untouched — they just won't be used by the pipeline
- Preserve all historical article data — no bulk deletions

### Claude's Discretion (data)
- SourceType enum values — Claude decides whether to remove Apify-related enum entries or keep them for data integrity with existing rows
- Whether to preserve or delete Apify-sourced articles — likely preserve for safety

### ScraperService removal scope
- Remove everything: ScraperService class AND all Apify source classes (base.py, google_news.py, valor.py, infomoney.py, cqcs.py, estadao.py, rss_source.py, ans.py)
- Delete the entire `app/services/sources/` directory — Factiva lives in its own service file, not under sources/
- Simplify collector to Factiva-only — remove source iteration, Apify branching, and scraper dispatch logic
- Researcher should search the full codebase for all ScraperService/Apify import references — scope is uncertain

### Admin UI & source references
- Remove the admin sources management page entirely — Factiva Config page (Phase 13) covers source configuration
- Remove the Sources link from admin sidebar navigation
- Researcher should check for Apify-specific dashboard widgets/metrics and recommend what to remove

### Claude's Discretion (admin)
- Apify source CRUD route handlers in admin.py — Claude determines which are Apify-specific and removes them
- Dashboard widget cleanup — Claude investigates and recommends what to remove

### Validation after removal
- Boot check required — verify FastAPI app starts without import errors after cleanup
- Add cleanup validation checks to test_factiva.py — grep codebase for Apify remnants as an automated check
- Full documentation sweep — update README, inline comments, docstrings, and .env.example that reference Apify sources or scraping

### Claude's Discretion (validation)
- Overall validation approach — Claude determines the most thorough way to verify nothing is broken (likely: import check + grep + boot verify)

</decisions>

<specifics>
## Specific Ideas

- "Remove everything" approach — user wants a clean break, not a gradual deprecation
- Delete the entire sources/ directory, not just files within it
- Simplify collector.py to Factiva-only rather than leaving the multi-source dispatch structure
- Documentation should be updated everywhere, not just .env.example

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-apify-cleanup*
*Context gathered: 2026-02-20*
