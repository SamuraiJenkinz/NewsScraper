# Phase 13: Admin Dashboard Extensions - Research

**Researched:** 2026-02-19
**Domain:** Admin UI extensions for enterprise API monitoring and configuration management
**Confidence:** HIGH

## Summary

Phase 13 extends the existing MDInsights admin dashboard with enterprise API health monitoring, credential management, and Factiva query configuration. The implementation builds on well-established patterns from Phases 9-12: Bootstrap 5 + HTMX for UI, pydantic Settings for configuration, and the existing ApiEvent table for health tracking.

**Key findings:**
- Dashboard health panel already implemented (lines 18-74 of dashboard.html) — displays traffic light status from ApiEvent table
- Enterprise config page exists (enterprise_config.html) — manages MMC Core API and Graph API credentials
- FactivaConfig model exists (factiva_config.py) — admin page exists (factiva.html) with working forms
- Article source badges require only template changes — collector_source column already populated
- No new models or migrations needed — all infrastructure complete from Phases 9-12

**Primary recommendation:** This is a UI-only phase. All backend infrastructure (models, API clients, event tracking) exists. Focus planning on template enhancements and route completion.

## Standard Stack

Phase 13 uses the existing MDInsights stack with no new dependencies.

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | (current) | Admin router and form handling | Python async web framework, already used for all admin routes |
| Bootstrap 5 | 5.3.x | UI components and responsive layout | Standard admin template framework, used throughout app/templates/admin/ |
| HTMX | 1.9.x | Partial page updates without full reload | Used for all interactive admin features (search, filters, inline editing) |
| Jinja2 | (current) | Server-side template rendering | FastAPI's template engine, configured in admin.py lines 44-50 |

### Supporting (Already Installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic-settings | (current) | Settings management with .env file | Already used for all configuration (config.py) |
| SQLAlchemy | (current) | ORM for database models | All models use Base class from app/database.py |
| structlog | (current) | Structured logging | All services use structlog.get_logger(__name__) |

### No New Dependencies Required
All Phase 13 features use existing libraries. The codebase already has:
- Bootstrap 5 for UI components (traffic lights, badges, forms)
- HTMX for partial updates (search filters, dashboard refresh)
- pydantic Settings for configuration (.env file management)
- ApiEvent model for health tracking (created in Phase 9)
- FactivaConfig model for query parameters (created in Phase 10)

## Architecture Patterns

### Recommended Project Structure
```
app/
├── routers/
│   └── admin.py              # Already has 17 routes, add health panel partial
├── templates/admin/
│   ├── dashboard.html        # COMPLETE — health panel exists (lines 18-74)
│   ├── enterprise_config.html # COMPLETE — credentials form exists
│   ├── factiva.html          # COMPLETE — query config form exists
│   ├── equity.html           # COMPLETE from Phase 12
│   └── partials/
│       ├── source_table.html # Reference pattern for article badge partial
│       └── health_panel.html # NEW — extract dashboard lines 18-74 for HTMX refresh
├── models/
│   ├── api_event.py          # COMPLETE — health tracking model from Phase 9
│   ├── factiva_config.py     # COMPLETE — query config model from Phase 10
│   └── equity_ticker.py      # COMPLETE from Phase 12
└── config.py                 # COMPLETE — Settings class with all MMC fields
```

### Pattern 1: Enterprise API Health Panel (Dashboard Widget)

**What:** Display traffic light status (healthy/degraded/offline/unknown) for each enterprise API (Auth, Factiva, Equity, Email) by querying the most recent ApiEvent per API.

**Current state:** COMPLETE implementation exists in dashboard.html lines 18-74 and admin.py lines 53-111 (_get_enterprise_api_status function).

**When to use:** No new code needed. Optionally extract the panel HTML to a partial template (partials/health_panel.html) if implementing a "Check Now" button for live refresh.

**Example (existing implementation):**
```python
# app/routers/admin.py lines 53-111
def _get_enterprise_api_status(db) -> list:
    """
    Query api_events table for the most recent event per enterprise API.

    Returns a list of dicts with keys:
        api_name, display_name, status, last_checked, reason

    Status values:
        healthy   - Most recent event was a success
        degraded  - Most recent event was a fallback
        offline   - Most recent event was a failure (not fallback)
        unknown   - No events recorded
    """
    DISPLAY_NAMES = {
        "auth": "Authentication",
        "news": "News (Factiva)",
        "equity": "Equity Prices",
        "email": "Email Delivery",
    }
    FALLBACK_TYPES = {
        ApiEventType.NEWS_FALLBACK,
        ApiEventType.EQUITY_FALLBACK,
        ApiEventType.EMAIL_FALLBACK,
    }

    result = []
    for api_name in ["auth", "news", "equity", "email"]:
        latest = (
            db.query(ApiEvent)
            .filter(ApiEvent.api_name == api_name)
            .order_by(ApiEvent.timestamp.desc())
            .first()
        )

        if latest is None:
            status = "unknown"
            last_checked = None
            reason = None
        elif latest.success:
            status = "healthy"
            last_checked = latest.timestamp.strftime("%Y-%m-%d %H:%M")
            reason = None
        else:
            if latest.event_type in FALLBACK_TYPES:
                status = "degraded"
            else:
                status = "offline"
            last_checked = latest.timestamp.strftime("%Y-%m-%d %H:%M")
            reason = (latest.detail[:100] if latest.detail else None)

        result.append({
            "api_name": api_name,
            "display_name": DISPLAY_NAMES[api_name],
            "status": status,
            "last_checked": last_checked,
            "reason": reason,
        })

    return result
```

**Template rendering (existing, dashboard.html lines 28-71):**
```html
<div class="row g-3">
    {% for api in enterprise_status %}
    <div class="col-md-3">
        <div class="p-3 border rounded">
            <div class="d-flex align-items-center mb-2">
                {% if api.status == 'healthy' %}
                    <i class="bi bi-check-circle-fill text-success fs-5 me-2"></i>
                {% elif api.status == 'degraded' %}
                    <i class="bi bi-exclamation-triangle-fill text-warning fs-5 me-2"></i>
                {% elif api.status == 'offline' %}
                    <i class="bi bi-x-circle-fill text-danger fs-5 me-2"></i>
                {% else %}
                    <i class="bi bi-question-circle text-secondary fs-5 me-2"></i>
                {% endif %}
                <strong>{{ api.display_name }}</strong>
            </div>
            <div class="mb-1">
                {% if api.status == 'healthy' %}
                    <span class="badge bg-success">Healthy</span>
                {% elif api.status == 'degraded' %}
                    <span class="badge bg-warning text-dark">Degraded</span>
                {% elif api.status == 'offline' %}
                    <span class="badge bg-danger">Offline</span>
                {% else %}
                    <span class="badge bg-secondary">Unknown</span>
                {% endif %}
            </div>
            {% if api.last_checked %}
            <div><small class="text-muted">Last checked: {{ api.last_checked }}</small></div>
            {% else %}
            <div><small class="text-muted">No events recorded</small></div>
            {% endif %}
            {% if api.reason %}
            <div><small class="text-danger">{{ api.reason }}</small></div>
            {% endif %}
        </div>
    </div>
    {% endfor %}
</div>
```

**Optional enhancement:** Add HTMX "Check Now" button that triggers live connectivity checks and updates the panel via partial template replacement.

### Pattern 2: Enterprise API Credential Management (Settings Page)

**What:** Form to configure MMC Core API and Microsoft Graph credentials. Saves to .env file and clears Settings cache.

**Current state:** COMPLETE implementation exists in enterprise_config.html and admin.py lines 1794-1933.

**When to use:** No new code needed. Existing implementation handles:
- Form rendering with non-secret values pre-populated
- Secret fields as password inputs (blank = keep existing value)
- POST handler updates .env file with _update_env_var() helper (lines 150-167)
- Settings cache cleared after save (get_settings.cache_clear())

**Example (existing implementation):**
```python
# app/routers/admin.py lines 1794-1829
@router.get("/enterprise-config", response_class=HTMLResponse)
def get_enterprise_config():
    """
    Serve the Enterprise API credential configuration page.

    Displays current non-secret values and boolean flags for secret fields.
    Secret values are never rendered — only a boolean indicating whether
    they are set is passed to the template.
    """
    settings = get_settings()

    config_display = {
        # Non-secret fields — render actual values
        "mmc_api_base_url": settings.mmc_api_base_url,
        "mmc_api_client_id": settings.mmc_api_client_id,
        "mmc_sender_email": settings.mmc_sender_email,
        "microsoft_tenant_id": settings.microsoft_tenant_id,
        "microsoft_client_id": settings.microsoft_client_id,
        "sender_email": settings.sender_email,
        # Secret fields — boolean flags only
        "mmc_api_client_secret_set": bool(settings.mmc_api_client_secret.strip()),
        "mmc_api_key_set": bool(settings.mmc_api_key.strip()),
        "microsoft_client_secret_set": bool(settings.microsoft_client_secret.strip()),
    }

    template = jinja_env.get_template("admin/enterprise_config.html")
    return HTMLResponse(content=template.render(
        config=config_display,
        active_nav="enterprise_config",
        success=None,
        error=None,
    ))
```

**Template pattern (enterprise_config.html lines 86-96):**
```html
<div class="mb-3">
    <label for="mmc_api_client_secret" class="form-label fw-semibold">Client Secret</label>
    <input
        type="password"
        id="mmc_api_client_secret"
        name="mmc_api_client_secret"
        class="form-control"
        value=""
        placeholder="{{ '••••••••' if config.mmc_api_client_secret_set else '' }}"
    >
    <div class="field-hint">Leave blank to keep existing value.</div>
</div>
```

**Security note:** Secrets are never logged or rendered to templates. Boolean flags (`mmc_api_key_set`) indicate whether a secret is configured without exposing the actual value.

### Pattern 3: Factiva Query Configuration (Settings Page)

**What:** Form to configure Factiva API query parameters (industry codes, keywords, page size, enabled toggle). Saves to factiva_config table (row id=1).

**Current state:** COMPLETE implementation exists in factiva.html and admin.py lines 1261-1383.

**When to use:** No new code needed. Existing implementation handles:
- Form rendering with current FactivaConfig values (GET /admin/factiva)
- POST handler validates and persists to database
- Hidden+checkbox pattern for enabled toggle (factiva.html lines 148-149)

**Example (existing implementation):**
```python
# app/routers/admin.py lines 1300-1383
@router.post("/factiva", response_class=HTMLResponse)
def update_factiva_config(
    industry_codes: str = Form(""),
    company_codes: str = Form(""),
    keywords: str = Form(""),
    page_size: int = Form(25),
    enabled: str = Form("false"),
):
    """
    Update Factiva query configuration.

    Persists changes to factiva_config DB table (row id=1). Changes take
    effect on the next pipeline run.
    """
    db = SessionLocal()
    config = None
    try:
        config = db.query(FactivaConfig).filter(FactivaConfig.id == 1).first()
        if not config:
            config = FactivaConfig(id=1)
            db.add(config)

        # Validate page_size
        if page_size not in (10, 25, 50, 100):
            page_size = 25

        # Clean comma-separated inputs
        config.industry_codes = ",".join(
            c.strip() for c in industry_codes.split(",") if c.strip()
        )
        config.company_codes = ",".join(
            c.strip() for c in company_codes.split(",") if c.strip()
        )
        config.keywords = keywords.strip()
        config.page_size = page_size
        config.enabled = enabled.lower() in ("true", "on", "1", "yes")
        config.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(config)

        logger.info("factiva_config_updated", ...)

        template = jinja_env.get_template("admin/factiva.html")
        return HTMLResponse(template.render(
            config=config,
            active_nav="factiva",
            success="Factiva configuration saved successfully.",
            error=None,
        ))

    except Exception as e:
        logger.error("factiva_config_update_failed", error=str(e))
        # Re-render form with error message
        ...
```

**Template checkbox pattern (factiva.html lines 146-160):**
```html
<div class="mb-4">
    <div class="form-check">
        <!-- Hidden field ensures value is submitted even when checkbox unchecked -->
        <input type="hidden" name="enabled" value="false">
        <input
            type="checkbox"
            id="enabled"
            name="enabled"
            value="true"
            class="form-check-input"
            {{ 'checked' if config.enabled }}
        >
        <label class="form-check-label fw-semibold" for="enabled">
            Enable Factiva Collection
        </label>
    </div>
</div>
```

### Pattern 4: Article Source Badges (Template Enhancement)

**What:** Display "Factiva" badge in article listings to distinguish Factiva-sourced articles from Apify/RSS articles.

**Current state:** Database field exists (NewsArticle.collector_source, line 39 of news_article.py). Dashboard already shows source breakdown per run (dashboard.html lines 258-272). Need to add badge to search results and archive viewer.

**When to use:** Apply to any template that lists articles (search results, run details, archive browser).

**Example (from existing dashboard template, lines 258-272):**
```html
<td>
    {% if run.source_breakdown %}
        {% if run.source_breakdown.get('Factiva') %}
            <span class="badge" style="background-color: #0077c8;">
                {{ run.source_breakdown['Factiva'] }} Factiva
            </span>
        {% endif %}
        {% if run.source_breakdown.get('Apify/RSS') %}
            <span class="badge bg-secondary">
                {{ run.source_breakdown['Apify/RSS'] }} Apify/RSS
            </span>
        {% endif %}
    {% endif %}
</td>
```

**Pattern for individual article badge:**
```html
<!-- In article listing templates (search results, archive, etc.) -->
<div class="article-meta">
    {% if article.collector_source == 'Factiva' %}
        <span class="badge" style="background-color: #0077c8;">
            <i class="bi bi-newspaper me-1"></i>Factiva
        </span>
    {% else %}
        <span class="badge bg-secondary">
            <i class="bi bi-rss me-1"></i>Apify/RSS
        </span>
    {% endif %}
</div>
```

**Color scheme (consistent with dashboard):**
- Factiva: `#0077c8` (Dow Jones brand blue)
- Apify/RSS: `bg-secondary` (Bootstrap gray)

### Anti-Patterns to Avoid

- **Don't create new models:** ApiEvent, FactivaConfig, and all credential fields already exist in Settings
- **Don't create migrations:** All database schema changes complete in Phases 9-12
- **Don't write to .env without cache clear:** Always call `get_settings.cache_clear()` after .env updates (line 1885)
- **Don't render secrets to templates:** Use boolean flags (e.g. `mmc_api_key_set`) instead of actual values
- **Don't hard-code API names:** Use the established ApiEvent.api_name values ("auth", "news", "equity", "email")

## Don't Hand-Roll

All core functionality already exists. Do not rebuild:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Health status aggregation | Custom health check service | Query ApiEvent table with _get_enterprise_api_status() | Already implemented in admin.py lines 53-111, reads from api_events table populated by TokenManager, FactivaCollector, EquityPriceClient |
| Credential storage | Custom secrets manager | pydantic Settings + .env file + _update_env_var() | Settings class (config.py) uses pydantic-settings with .env support, _update_env_var() helper (admin.py lines 150-167) handles updates |
| Configuration management | Custom config API | FactivaConfig model + SQLAlchemy ORM | FactivaConfig table exists (factiva_config.py), admin UI exists (factiva.html), POST handler validates and persists (admin.py lines 1300-1383) |
| Source attribution | Custom collector tracking | NewsArticle.collector_source field | Column exists (news_article.py line 39), FactivaCollector sets it to "Factiva" (factiva.py line 415), default is "Apify/RSS" |

**Key insight:** Phase 13 is UI-only. All backend models, API clients, event tracking, and configuration infrastructure was built in Phases 9-12. Planning should focus on template enhancements (extracting health panel partial, adding article badges) and optional live check button.

## Common Pitfalls

### Pitfall 1: Creating New Database Models or Migrations

**What goes wrong:** Attempting to create new models for credential storage or health tracking when they already exist.

**Why it happens:** Not recognizing that Phases 9-12 created all required infrastructure (ApiEvent model in Phase 9, FactivaConfig in Phase 10, EquityTicker in Phase 11, enterprise email settings in Phase 12).

**How to avoid:**
- Review existing models in app/models/ before planning new ones
- Check Settings class (config.py) for credential fields — all MMC and Graph fields exist
- Verify api_events table usage in TokenManager, FactivaCollector, EquityPriceClient
- Confirm FactivaConfig table seeded and managed via /admin/factiva page

**Warning signs:**
- Plan includes "Create ApiHealthStatus model" → use ApiEvent instead
- Plan includes "Create CredentialStore model" → use Settings + .env instead
- Plan includes "Add collector_source column" → column exists since Phase 10

### Pitfall 2: Forgetting Settings Cache Clear After .env Updates

**What goes wrong:** Admin saves credentials via UI, but pipeline continues using old cached values until process restart.

**Why it happens:** pydantic Settings uses @lru_cache() decorator (config.py line 188), caching the Settings instance for the process lifetime.

**How to avoid:**
- Always call `get_settings.cache_clear()` after writing to .env file
- Reference existing pattern in admin.py line 1885 (enterprise_config POST handler)
- Also used in recipients POST handler (admin.py line 1003)

**Detection:** Test credential updates by triggering a pipeline run immediately after saving — if old credentials are used, cache wasn't cleared.

### Pitfall 3: Rendering Secret Values to Templates

**What goes wrong:** Exposing client_secret, api_key, or other credentials in HTML source (even in password fields with value attribute).

**Why it happens:** Attempting to pre-populate password fields with existing secret values for easier editing.

**How to avoid:**
- Use boolean flags (e.g. `mmc_api_key_set: bool(settings.mmc_api_key.strip())`)
- Render placeholder only: `placeholder="{{ '••••••••' if config.mmc_api_key_set else '' }}"`
- Leave value attribute blank: `value=""`
- Document in field hint: "Leave blank to keep existing value."
- Reference enterprise_config.html lines 86-96 for the pattern

**Warning signs:**
- Template includes `value="{{ config.mmc_api_client_secret }}"` → SECURITY ISSUE
- Plan includes "pre-populate secret fields with masked values" → use boolean flags instead

### Pitfall 4: Inconsistent ApiEvent.api_name Values

**What goes wrong:** Health panel queries fail to find events because api_name doesn't match the canonical values used by services.

**Why it happens:** Using different api_name strings when recording events vs. when querying for health status.

**How to avoid:**
- Use the canonical values established by enterprise services:
  - TokenManager: `api_name="auth"` (token_manager.py line 298)
  - FactivaCollector: `api_name="news"` (factiva.py line 442)
  - EquityPriceClient: `api_name="equity"` (equity.py line 269)
  - EnterpriseEmailer: `api_name="email"` (assumed, verify in implementation)
- Reference _get_enterprise_api_status() loop (admin.py line 79): `["auth", "news", "equity", "email"]`
- Never add new api_name values without updating the health panel query

**Detection:** Dashboard shows "unknown" status for an API despite recent pipeline runs recording events — api_name mismatch.

## Code Examples

Verified patterns from official sources.

### Health Panel with Traffic Light Icons

```html
<!-- Source: app/templates/admin/dashboard.html lines 28-71 -->
<!-- Shows traffic light status for each enterprise API -->
<div class="row g-3">
    {% for api in enterprise_status %}
    <div class="col-md-3">
        <div class="p-3 border rounded">
            <div class="d-flex align-items-center mb-2">
                {% if api.status == 'healthy' %}
                    <i class="bi bi-check-circle-fill text-success fs-5 me-2"></i>
                {% elif api.status == 'degraded' %}
                    <i class="bi bi-exclamation-triangle-fill text-warning fs-5 me-2"></i>
                {% elif api.status == 'offline' %}
                    <i class="bi bi-x-circle-fill text-danger fs-5 me-2"></i>
                {% else %}
                    <i class="bi bi-question-circle text-secondary fs-5 me-2"></i>
                {% endif %}
                <strong>{{ api.display_name }}</strong>
            </div>
            <div class="mb-1">
                {% if api.status == 'healthy' %}
                    <span class="badge bg-success">Healthy</span>
                {% elif api.status == 'degraded' %}
                    <span class="badge bg-warning text-dark">Degraded</span>
                {% elif api.status == 'offline' %}
                    <span class="badge bg-danger">Offline</span>
                {% else %}
                    <span class="badge bg-secondary">Unknown</span>
                {% endif %}
            </div>
            {% if api.last_checked %}
            <div><small class="text-muted">Last checked: {{ api.last_checked }}</small></div>
            {% else %}
            <div><small class="text-muted">No events recorded</small></div>
            {% endif %}
            {% if api.reason %}
            <div><small class="text-danger">{{ api.reason }}</small></div>
            {% endif %}
        </div>
    </div>
    {% endfor %}
</div>
```

### Credential Form with Secret Masking

```html
<!-- Source: app/templates/admin/enterprise_config.html lines 99-109 -->
<!-- Password field for API key — never renders actual value -->
<div class="mb-3">
    <label for="mmc_api_key" class="form-label fw-semibold">API Key (X-Api-Key)</label>
    <input
        type="password"
        id="mmc_api_key"
        name="mmc_api_key"
        class="form-control"
        value=""
        placeholder="{{ '••••••••' if config.mmc_api_key_set else '' }}"
    >
    <div class="field-hint">Leave blank to keep existing value.</div>
</div>
```

```python
# Source: app/routers/admin.py lines 1831-1882
# POST handler updates .env file, only writing secrets when non-blank
@router.post("/enterprise-config", response_class=HTMLResponse)
def post_enterprise_config(
    mmc_api_base_url: str = Form(""),
    mmc_api_client_id: str = Form(""),
    mmc_api_client_secret: str = Form(""),
    mmc_api_key: str = Form(""),
    # ... other fields
):
    try:
        env_path = Path(".env")
        if env_path.exists():
            env_content = env_path.read_text(encoding="utf-8")
        else:
            env_content = ""

        # Non-secret fields: always update
        NON_SECRET_FIELDS = [
            ("MMC_API_BASE_URL", mmc_api_base_url),
            ("MMC_API_CLIENT_ID", mmc_api_client_id),
            # ...
        ]
        for var_name, value in NON_SECRET_FIELDS:
            env_content = _update_env_var(env_content, var_name, value)

        # Secret fields: only update if non-blank value provided
        SECRET_FIELDS = [
            ("MMC_API_CLIENT_SECRET", mmc_api_client_secret),
            ("MMC_API_KEY", mmc_api_key),
            # ...
        ]
        for var_name, value in SECRET_FIELDS:
            if value.strip():
                env_content = _update_env_var(env_content, var_name, value)

        env_path.write_text(env_content, encoding="utf-8")

        # Clear settings cache so pipeline picks up new values
        get_settings.cache_clear()

        logger.info("enterprise_config_updated")
        # ...
```

### Checkbox Toggle with Hidden Field Pattern

```html
<!-- Source: app/templates/admin/factiva.html lines 146-164 -->
<!-- Hidden+checkbox pattern ensures boolean form submission -->
<div class="mb-4">
    <div class="form-check">
        <!-- Hidden field ensures a value is always submitted even when checkbox is unchecked -->
        <input type="hidden" name="enabled" value="false">
        <input
            type="checkbox"
            id="enabled"
            name="enabled"
            value="true"
            class="form-check-input"
            {{ 'checked' if config.enabled }}
        >
        <label class="form-check-label fw-semibold" for="enabled">
            Enable Factiva Collection
        </label>
    </div>
    <div class="field-hint ms-4">
        When disabled, the pipeline automatically falls back to Apify/RSS collection.
    </div>
</div>
```

### Article Source Badge

```html
<!-- Pattern extracted from dashboard.html lines 258-272 -->
<!-- Apply to search results, archive browser, any article listing -->
{% if article.collector_source == 'Factiva' %}
    <span class="badge" style="background-color: #0077c8;">
        <i class="bi bi-newspaper me-1"></i>Factiva
    </span>
{% else %}
    <span class="badge bg-secondary">
        <i class="bi bi-rss me-1"></i>Apify/RSS
    </span>
{% endif %}
```

## State of the Art

No state changes for Phase 13 — all infrastructure was created in earlier phases.

| Feature | Implementation Status | Notes |
|---------|----------------------|-------|
| Enterprise API Health Panel | COMPLETE (Phase 9) | Dashboard lines 18-74, admin.py lines 53-111 |
| Credential Management UI | COMPLETE (Phase 12) | enterprise_config.html, admin.py lines 1794-1933 |
| Factiva Query Configuration | COMPLETE (Phase 10) | factiva.html, admin.py lines 1261-1383 |
| Equity Ticker Mappings | COMPLETE (Phase 12) | equity.html, admin.py lines 1508-1791 |
| Article Source Attribution | COMPLETE (Phase 10) | collector_source column populated by FactivaCollector |
| ApiEvent Tracking | COMPLETE (Phase 9) | TokenManager, FactivaCollector, EquityPriceClient all record events |

**No deprecated features:** All patterns established in Phases 9-12 are current and in active use.

## Open Questions

1. **Live Health Check Button**
   - What we know: Dashboard shows cached status from api_events table (last pipeline run)
   - What's unclear: User story doesn't specify "Check Now" live connectivity check
   - Recommendation: Plan 01 adds optional "Check Now" button that triggers TokenManager.get_token(), FactivaCollector health ping, EquityPriceClient health ping, updates ApiEvent table, and refreshes health panel via HTMX partial. Mark as OPTIONAL — cached status from pipeline runs may be sufficient.

2. **Factiva Article Source Filter**
   - What we know: NewsArticle.collector_source column exists and is populated
   - What's unclear: Whether to add source filter dropdown to search page or just display badges
   - Recommendation: Display badges in all article listings (search, archive). Add filter dropdown to search page only if explicitly required in success criteria. Search service (search.py) would need source_name parameter added to search() method.

3. **Enterprise Config "Test Connection" Button**
   - What we know: Enterprise config page saves credentials to .env
   - What's unclear: User story mentions "Test Connection" in CONTEXT.md but not in success criteria
   - Recommendation: Mark as OPTIONAL. Would require route that calls TokenManager.get_token() with temporary Settings instance (without persisting to .env) and returns success/failure message via HTMX.

## Sources

### Primary (HIGH confidence)

- **Existing Codebase** - All findings verified against current implementation
  - app/routers/admin.py (17 routes including health panel, enterprise config, factiva config)
  - app/templates/admin/dashboard.html (lines 18-74: enterprise API health panel)
  - app/templates/admin/enterprise_config.html (credentials form)
  - app/templates/admin/factiva.html (query configuration form)
  - app/models/api_event.py (ApiEvent model with event types)
  - app/models/factiva_config.py (FactivaConfig model for query params)
  - app/models/news_article.py (collector_source field line 39)
  - app/config.py (Settings class with all MMC and Graph fields)
  - app/auth/token_manager.py (TokenManager with _record_event method)
  - app/collectors/factiva.py (FactivaCollector with _record_event method)
  - app/collectors/equity.py (EquityPriceClient with _record_event method)

- **Bootstrap 5 Documentation** - UI component patterns (badges, forms, traffic lights)
  - https://getbootstrap.com/docs/5.3/components/badge/ (badge styling)
  - https://getbootstrap.com/docs/5.3/forms/form-control/ (form patterns)

- **HTMX Documentation** - Partial page updates
  - https://htmx.org/docs/#ajax (HTMX partial refresh pattern)

### Secondary (MEDIUM confidence)

- **pydantic-settings Documentation** - .env file management
  - https://docs.pydantic.dev/latest/concepts/pydantic_settings/ (Settings class pattern)

### Tertiary (LOW confidence)

None — all findings based on existing codebase inspection.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All dependencies already installed and in use
- Architecture: HIGH - Existing patterns verified in codebase
- Pitfalls: HIGH - Based on actual implementation patterns (cache clear, secret masking, api_name values)

**Research date:** 2026-02-19
**Valid until:** 2026-03-21 (30 days — stable stack, no external dependencies)
