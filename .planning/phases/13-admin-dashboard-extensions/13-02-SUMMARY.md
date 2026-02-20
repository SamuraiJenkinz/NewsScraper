---
phase: 13-admin-dashboard-extensions
plan: 02
type: summary
completed: 2026-02-20
duration: 8 min
subsystem: admin-dashboard
tags: [admin-ui, configuration, credentials, factiva, enterprise-api]

requires:
  - 13-01 (enterprise API health panel)
  - 10-01 (Factiva collector foundation)
  - 09-01 (MMC Core API auth foundation)

provides:
  - Enterprise Config credential management UI
  - Factiva query parameter configuration UI
  - Date range configuration (24h/48h/7d)
  - .env file write capability with secret masking
  - Settings cache invalidation

affects:
  - Future phases requiring credential configuration via UI
  - Phase 14 (Apify cleanup) — can reference Factiva config patterns

tech-stack:
  added:
    - None (uses existing Bootstrap 5 + HTMX + Jinja2)
  patterns:
    - _update_env_var() helper for .env file updates
    - Hidden field pattern for checkbox handling (enabled)
    - Secret field masking with password input (never show actual values)
    - Settings cache clear via get_settings.cache_clear()
    - FactivaConfig database row CRUD with audit trail

key-files:
  created:
    - app/templates/admin/enterprise_config.html (credential management form)
    - app/templates/admin/factiva.html (Factiva query config form)
    - scripts/migrate_008_factiva_date_range.py (adds date_range_hours column)
  modified:
    - app/routers/admin.py (added enterprise-config and factiva routes, _update_env_var helper)
    - app/templates/admin/base.html (sidebar nav entries for both pages)
    - app/models/factiva_config.py (added date_range_hours column)
    - app/collectors/factiva.py (reads date_range_hours from query_params)

decisions:
  - env-file-pattern: Credentials stored in .env file (not database) for consistency with existing config pattern
  - secret-masking: Secret fields never rendered in HTML source; password input with boolean placeholder
  - blank-preserves: Blank secret field submissions preserve existing values (not overwritten)
  - cache-clear: get_settings.cache_clear() called after .env write so pipeline reads fresh values
  - date-range-default: 48 hours matches existing hardcoded behavior (backward compatible)
  - factiva-row-id: FactivaConfig id=1 is the active configuration (single-row pattern)
  - sidebar-placement: New nav entries placed after Equity Tickers, before end of nav
---

# Phase 13 Plan 02: Enterprise Config & Factiva Config Pages Summary

**One-liner:** Enterprise Config credential management and Factiva query parameter forms with date range dropdown (24h/48h/7d) for admin-configurable pipeline behavior.

## Objective

Add two admin pages for configuring MMC Core API credentials and Factiva query parameters without editing .env files or database rows directly. Satisfies ADMN-18 (credential config) and ADMN-19 (Factiva query config with date range).

## Tasks Completed

### Task 1: Enterprise Config Credential Management Page

**Duration:** 4 min | **Commit:** 6d76b49

**Implementation:**
- Added `_update_env_var()` helper function to admin.py for regex-based .env file updates
- Created GET route `/admin/enterprise-config` to render form with current settings
  - Non-secret fields show actual values (base_url, client_id, sender_email)
  - Secret fields show boolean flags only (client_secret_set, api_key_set)
- Created POST route to save credentials to .env file
  - Non-secret fields always updated
  - Secret fields only updated if submitted value is non-blank (preserves existing)
  - Calls `get_settings.cache_clear()` after write so pipeline reads fresh .env
- Created `enterprise_config.html` template with MMC Core API card
  - 5 credential fields with Bootstrap 5 form styling
  - Secret fields use type="password" with bullet placeholders
  - Field hints explain each credential's purpose
  - Help card documents credential requirements per API
- Updated `base.html` sidebar navigation
  - Added "Enterprise Config" with bi-shield-lock icon
  - Added "Factiva Config" with bi-newspaper icon
  - Placed after Equity Tickers nav entry

**Verification:**
- `python -c "from app.routers.admin import router"` — imports without errors
- Grep confirms GET/POST routes for `/admin/enterprise-config`
- `enterprise_config.html` exists with "MMC Core API" card
- Sidebar nav entries confirmed in `base.html`
- `_update_env_var` helper and `cache_clear()` call confirmed

**Artifacts:**
- `app/templates/admin/enterprise_config.html` (186 lines)
- Updated `app/routers/admin.py` (+97 lines for helper + routes)
- Updated `app/templates/admin/base.html` (sidebar nav entries)

### Task 2: Factiva Query Config Page with Date Range

**Duration:** 4 min | **Commit:** 43b5ebc

**Implementation:**
- Added `date_range_hours` column to FactivaConfig model (Integer, default 48, NOT NULL)
  - Comment: "Lookback window in hours (24, 48, or 168 for 7 days)"
- Created migration script `migrate_008_factiva_date_range.py`
  - ALTER TABLE factiva_config ADD COLUMN date_range_hours
  - Idempotent with try/except for column already existing
  - Follows migrate_007 pattern exactly
- Updated `FactivaCollector.collect()` to use configurable date range
  - Read `date_range_hours` from query_params (default 48)
  - Replace hardcoded `timedelta(days=2)` with `timedelta(hours=date_range_hours)`
  - Updated docstring from "past 48 hours" to "configured lookback window"
- Added FactivaConfig import to admin.py
- Created GET route `/admin/factiva` to render query config form
  - Queries FactivaConfig row id=1 from database
  - Creates default row if missing (industry codes, keywords, page_size=50, date_range=48)
- Created POST route to save Factiva configuration
  - Cleans comma-separated inputs (strip whitespace)
  - Validates page_size (10, 25, 50, 100 — default 25)
  - Validates date_range_hours (24, 48, 168 — default 48)
  - Hidden field pattern for enabled checkbox
  - Updates audit fields (updated_at, updated_by)
- Created `factiva.html` template with query parameter form
  - Industry codes text input with common code hints
  - Company codes text input (optional)
  - Keywords text input with Portuguese insurance terms hint
  - Results per page dropdown (10/25/50/100)
  - Date range dropdown (24h/48h/7d)
  - Enabled toggle switch with hidden field pattern
  - Last updated timestamp display
  - Reference table card with common Brazilian insurance industry codes (i82, i8200, i82001, i82002, i82003, i832)

**Verification:**
- FactivaConfig model columns include `date_range_hours`
- Admin.py imports without errors
- Grep confirms date_range_hours in model and collector
- GET/POST routes for `/admin/factiva` confirmed
- `factiva.html` exists and contains date range dropdown
- Migration script 008 exists

**Artifacts:**
- `app/templates/admin/factiva.html` (283 lines with reference table)
- Updated `app/models/factiva_config.py` (+6 lines for date_range_hours column)
- Updated `app/collectors/factiva.py` (+4 lines to read date_range_hours)
- Updated `app/routers/admin.py` (+110 lines for Factiva routes)
- `scripts/migrate_008_factiva_date_range.py` (98 lines)

## Deviations from Plan

None — plan executed exactly as written.

## Key Decisions

### Enterprise Config Pattern
- **Decision:** Store credentials in .env file (not database)
- **Rationale:** Consistency with existing config.py pattern; Settings uses pydantic BaseSettings with env_file
- **Impact:** Admin changes require .env write + settings cache clear; no database dependency for credentials

### Secret Masking Strategy
- **Decision:** Never render actual secret values in HTML; use password input with boolean placeholder
- **Rationale:** Security best practice; admin knows if secret is set without seeing actual value
- **Impact:** Blank submissions preserve existing secrets (don't overwrite)

### Date Range Default
- **Decision:** 48 hours default for Factiva date range
- **Rationale:** Matches existing hardcoded `timedelta(days=2)` behavior; backward compatible
- **Impact:** No behavior change for existing deployments; migration sets default=48

### Factiva Config Row Pattern
- **Decision:** Single row (id=1) holds active configuration
- **Rationale:** Simple, no multi-config complexity; matches existing design from Phase 10
- **Impact:** Admin edits single config row; no config versioning or A/B testing

## Requirements Satisfied

✅ **ADMN-18:** Admin can configure MMC Core API credentials via settings UI without editing .env files
- Enterprise Config page at `/admin/enterprise-config`
- Form with 5 credential fields (base_url, client_id, client_secret, api_key, sender_email)
- Secret fields masked with password input
- .env file write with settings cache clear
- Sidebar nav entry with shield-lock icon

✅ **ADMN-19:** Admin can configure Factiva query parameters via dedicated page
- Factiva Config page at `/admin/factiva`
- Form with industry codes, company codes, keywords, page size, date range, enabled toggle
- Date range dropdown with 24h/48h/7d options (48h default)
- Reference table with common Brazilian insurance industry codes
- Sidebar nav entry with newspaper icon

## Next Phase Readiness

**Phase 13-03 (Factiva source badges):** Ready to proceed
- Admin can now configure Factiva query parameters via UI
- Date range configuration will affect badge display (recent vs. older articles)
- Factiva collector uses configurable date range starting next pipeline run

**Phase 14 (Apify cleanup):** Reference patterns established
- Factiva config page demonstrates admin-configurable source parameters
- Can apply similar patterns to legacy Apify source configuration if needed

**Production deployment considerations:**
- Run `python scripts/migrate_008_factiva_date_range.py` before first startup with new code
- Test credential save flow with staging MMC API credentials
- Verify settings cache clear picks up new .env values
- Validate Factiva date range changes affect next pipeline run
- Confirm secret fields never rendered in HTML source (inspect element check)

## Technical Notes

### Settings Cache Pattern
```python
# After .env write
env_path.write_text(env_content, encoding="utf-8")
get_settings.cache_clear()  # ← Critical for fresh .env load
settings_refreshed = get_settings()
```

### Hidden Field Checkbox Pattern
```html
<!-- Ensures form submission includes enabled=false when unchecked -->
<input type="hidden" name="enabled_hidden" value="false">
<input type="checkbox" name="enabled" {% if config.enabled %}checked{% endif %}>
```

### Secret Field Masking
```html
<!-- Never render actual value; show bullets if set -->
<input type="password" value=""
       placeholder="{% if secret_set %}••••••••••••••••{% else %}Not set{% endif %}">
```

Backend only updates if non-blank:
```python
if mmc_api_client_secret.strip():
    env_content = _update_env_var(env_content, "MMC_API_CLIENT_SECRET", mmc_api_client_secret.strip())
```

### Env Var Update Helper
```python
def _update_env_var(env_content: str, var_name: str, value: str) -> str:
    """Replace or append an environment variable in .env file content."""
    import re
    pattern = re.compile(f"^{re.escape(var_name)}=.*$", re.MULTILINE)
    if pattern.search(env_content):
        return pattern.sub(f"{var_name}={value}", env_content)
    else:
        if env_content and not env_content.endswith("\n"):
            env_content += "\n"
        return env_content + f"{var_name}={value}\n"
```

## Files Changed Summary

**Created (5 files):**
- `app/templates/admin/enterprise_config.html` (186 lines)
- `app/templates/admin/factiva.html` (283 lines)
- `scripts/migrate_008_factiva_date_range.py` (98 lines)

**Modified (4 files):**
- `app/routers/admin.py` (+214 lines: helper, 2 route pairs, import)
- `app/templates/admin/base.html` (+6 lines: sidebar nav entries)
- `app/models/factiva_config.py` (+6 lines: date_range_hours column)
- `app/collectors/factiva.py` (+4 lines: read date_range_hours)

**Total:** 797 lines added, 5 lines removed

## Commits

1. **6d76b49** — feat(13-02): add Enterprise Config credential management page
   - Enterprise Config UI with secret masking
   - _update_env_var() helper and settings cache clear
   - Sidebar nav entries for both pages

2. **43b5ebc** — feat(13-02): add Factiva query config page with date range
   - Factiva Config UI with date range dropdown
   - Migration 008 for date_range_hours column
   - Collector reads date_range_hours from query_params
   - Reference table with Brazilian insurance industry codes

---

**Phase 13 Plan 02 Status:** ✅ COMPLETE
**Next:** 13-03 (Factiva source badges in reports)
**Blockers:** None
**Duration:** 8 minutes
**Quality:** All verification steps passed, no deviations from plan
