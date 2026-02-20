# Phase 12: Equity Price Enrichment - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Tracked Brazilian insurance companies display inline equity data (ticker, price, change%) in both browser and email reports. Admin can manage insurer-to-ticker mappings. Equity prices are fetched from the MMC Core API Equity Price endpoint.

This phase does NOT include: historical price charts, trend analysis, or portfolio tracking. Those are future features.

</domain>

<decisions>
## Implementation Decisions

### Equity chip design
- Claude's discretion on content (ticker + price + change%, or subset) — pick the best balance of information density and readability for the Bootstrap 5 report theme
- Claude's discretion on color coding — pick what fits BrasilIntel's existing admin/report styling (likely subtle badge colors with arrow symbols for accessibility)
- Claude's discretion on placement — determine whether chips go inline next to insurer headings, in a summary table, or both
- Claude's discretion on interactivity — decide if chips should link to Google Finance or remain display-only

### Email layout approach
- Claude's discretion on format — determine best approach for Outlook/Gmail compatibility (per-insurer inline vs summary table)
- Claude's discretion on detail level — match browser or simplify for email context
- Claude's discretion on color usage — pick safest approach that still looks professional (text fallback symbols for stripped colors)
- Claude's discretion on price timestamp — determine if "Prices as of [time]" adds value

### Data freshness & missing tickers
- Claude's discretion on fetch timing — determine whether prices fetch during pipeline run or on separate schedule
- Claude's discretion on missing ticker behavior — show nothing vs placeholder for unmapped insurers
- Claude's discretion on API failure degradation — hide section vs show stale data with warning
- Claude's discretion on initial ticker scope — seed sensible defaults for major publicly-traded Brazilian insurers (SulAmerica, Porto Seguro, BB Seguridade, IRB Brasil, Caixa Seguridade etc. — likely 5-10)

### Admin ticker management UX
- Claude's discretion on CRUD approach — dedicated page vs inline on insurer list, following existing Bootstrap 5 + HTMX admin patterns
- Claude's discretion on bulk import — determine if CSV upload is worth the complexity given ~5-10 expected tickers
- Claude's discretion on validation — pick appropriate validation level (free text, format check, or live validation)
- Claude's discretion on live preview — determine if fetching and showing price on save is worth the API call

### Claude's Discretion
All four areas were delegated to Claude's judgment. The user trusts Claude to make sensible, consistent choices that fit the existing BrasilIntel codebase patterns, Bootstrap 5 admin theme, and enterprise report styling. Key guidance:
- Prioritize Outlook/Gmail email compatibility over visual richness
- Keep it practical for ~5-10 publicly-traded insurers, not 897
- Follow existing HTMX partial-update patterns in admin
- Graceful degradation when equity API is unavailable

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User trusts Claude's judgment across all implementation choices for this phase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-equity-price-enrichment*
*Context gathered: 2026-02-19*
