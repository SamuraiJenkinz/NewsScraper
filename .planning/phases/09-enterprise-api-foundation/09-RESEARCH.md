# Phase 9: Enterprise API Foundation — Research

**Researched:** 2026-02-19
**Researcher:** GSD Research Agent
**Mode:** Feasibility + Port Analysis
**Confidence:** HIGH — all source files read directly from disk

---

## 1. MDInsights Source Analysis

### 1.1 TokenManager (`app/auth/token_manager.py`)

**Location in MDInsights:** `C:\BrasilIntel\mdinsights\app\auth\token_manager.py`
**Lines:** 332
**Dependencies:** `httpx`, `tenacity`, `structlog`, `app.database.SessionLocal`, `app.models.api_event`

**Core mechanics:**

```python
class TokenManager:
    REFRESH_MARGIN_SECONDS = 300  # 5-minute proactive refresh

    async def get_token(self) -> Optional[str]:
        # Returns cached token if still valid (not within 5 min of expiry)
        # Otherwise calls _acquire_token()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False,
    )
    async def _acquire_token(self) -> Optional[str]:
        # OAuth2 client_credentials POST
        # 401/403 = no retry, return None immediately
        # 429/5xx = retry up to 3 times
        # network errors = retry up to 3 times

    def _record_event(self, event_type, success, detail=None, run_id=None):
        # Opens its OWN DB session — never interferes with caller's transaction
        # Swallows all exceptions — event recording never crashes token flow
```

**Token lifecycle:**
1. `TokenInfo` dataclass: `access_token`, `expires_at` (Unix timestamp), `token_type`
2. `is_token_valid` property: checks `expires_at > time.time() + REFRESH_MARGIN_SECONDS`
3. `force_refresh()`: clears `_token = None`, calls `_acquire_token()` — used by test_auth.py

**Security contract** (must preserve in port):
- NEVER logs `client_id`, `client_secret`, or raw token values
- `detail` strings in api_events are JSON-safe, secret-free
- Token is only shown redacted in scripts (first 8 + last 4 chars)

**Integration pattern in MDInsights pipeline:**
```python
# TokenManager is injected as Optional — graceful degradation built in
class PipelineOrchestrator:
    def __init__(self, ..., token_manager: Optional[TokenManager] = None):
        self.token_manager = token_manager

# Step 0 of pipeline: try auth, degrade gracefully if fails
if self.token_manager and self.token_manager.is_configured():
    token = await self.token_manager.get_token()
    degraded_auth = token is None
```

**What needs changing for BrasilIntel port:**
- Import path change: `from app.config import get_settings` — same pattern, same function name
- `from app.database import SessionLocal` — same pattern, same name
- `from app.models.api_event import ApiEvent, ApiEventType` — new model to be created
- Settings field names are identical (mmc_api_base_url, etc.) — no change needed
- No domain-specific logic in TokenManager itself — pure auth plumbing

### 1.2 ApiEvent Model (`app/models/api_event.py`)

**Location in MDInsights:** `C:\BrasilIntel\mdinsights\app\models\api_event.py`
**Table name:** `api_events`

**Schema:**
```sql
CREATE TABLE api_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  VARCHAR (enum: 9 values),
    api_name    VARCHAR(50) NOT NULL,     -- "auth", "news", "equity", "email"
    timestamp   DATETIME NOT NULL,
    success     BOOLEAN NOT NULL,
    detail      TEXT,                     -- JSON string, never contains secrets
    run_id      INTEGER REFERENCES runs(id)  -- nullable (test scripts have run_id=NULL)
);
```

**ApiEventType enum (all 9 values):**
```python
TOKEN_ACQUIRED = "token_acquired"
TOKEN_REFRESHED = "token_refreshed"
TOKEN_FAILED = "token_failed"
NEWS_FETCH = "news_fetch"
NEWS_FALLBACK = "news_fallback"
EQUITY_FETCH = "equity_fetch"
EQUITY_FALLBACK = "equity_fallback"
EMAIL_SENT = "email_sent"
EMAIL_FALLBACK = "email_fallback"
```

**FK to `runs` table:** Nullable — `run_id=None` for out-of-pipeline calls (test_auth.py).
BrasilIntel's `runs` table exists and has `id` as primary key — FK will work.

**What needs changing for BrasilIntel port:** Nothing. Copy verbatim. The only change
is the import `from app.database import Base` which is identical in both projects.

### 1.3 FactivaConfig Model (`app/models/factiva_config.py`)

**Location in MDInsights:** `C:\BrasilIntel\mdinsights\app\models\factiva_config.py`
**Table name:** `factiva_config`

**Schema:**
```sql
CREATE TABLE factiva_config (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    industry_codes  VARCHAR(500) DEFAULT "i82,i832",
    company_codes   VARCHAR(500) DEFAULT "MM",
    keywords        VARCHAR(500) DEFAULT "insurance reinsurance",
    page_size       INTEGER DEFAULT 25,
    enabled         BOOLEAN DEFAULT TRUE,
    updated_at      DATETIME,
    updated_by      VARCHAR(100)
);
```

**Usage pattern in MDInsights pipeline:**
```python
factiva_config = db.query(FactivaConfig).filter(FactivaConfig.id == 1).first()
if factiva_config and factiva_config.enabled:
    query_params = {
        "industry_codes": factiva_config.industry_codes or "",
        "company_codes": factiva_config.company_codes or "",
        "keywords": factiva_config.keywords or "",
        "page_size": factiva_config.page_size or 25,
    }
```

**Single-row table:** id=1 is the active config, seeded by migration, managed by admin UI.

**What needs changing for BrasilIntel port:** Nothing. Copy verbatim. Defaults
(`i82,i832`, `insurance reinsurance`) are decided and confirmed in CONTEXT.md.

### 1.4 EquityTicker Model (`app/models/equity_ticker.py`)

**Location in MDInsights:** `C:\BrasilIntel\mdinsights\app\models\equity_ticker.py`
**Table name:** `equity_tickers`

**Schema:**
```sql
CREATE TABLE equity_tickers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name VARCHAR(200) UNIQUE NOT NULL,  -- AI classifier entity name (join key)
    ticker      VARCHAR(20) NOT NULL,           -- e.g. "CXSE3", "WIZC3" (B3 tickers)
    exchange    VARCHAR(20) NOT NULL DEFAULT "NYSE",  -- will change to "BVMF" for Brazil
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at  DATETIME,
    updated_by  VARCHAR(100)
);
```

**Join strategy in MDInsights:** `entity_name` string match — NOT a FK to any other table.
`entity_name` must match exactly what the AI classifier produces.

**Domain adaptation needed:**
- `exchange` default: MDInsights uses `"NYSE"`, BrasilIntel should default to `"BVMF"` (B3)
- `entity_name` values will be Brazilian insurer names from AI classification
- This is the ONLY domain-specific change in the three models

**FK question (discretion noted in CONTEXT.md):**
- MDInsights uses `entity_name` string — simpler admin CRUD, no FK cascade complexity
- BrasilIntel has `insurer_id` FK available on `news_items`
- Recommendation: Use `entity_name` string (same as MDInsights) — insurers can be
  renamed/deduped without orphaning ticker rows; admin CRUD is simpler

### 1.5 MDInsights Config Fields (credentials block)

**Location in MDInsights:** `C:\BrasilIntel\mdinsights\app\config.py` lines 73-85

**Fields to add to BrasilIntel:**
```python
# MMC Core API (Enterprise Integration)
mmc_api_base_url: str = ""
mmc_api_client_id: str = ""
mmc_api_client_secret: str = ""
mmc_api_key: str = ""
mmc_api_token_path: str = "/coreapi/access-management/v1/token"

# Enterprise Email Sender (Phase 12 — port now for completeness)
mmc_sender_email: str = ""
mmc_sender_name: str = "Kevin Taylor"
mmc_email_path: str = "/coreapi/email/v1"
```

**Helper methods to add:**
```python
def is_mmc_auth_configured(self) -> bool:
    return bool(self.mmc_api_base_url and self.mmc_api_client_id and self.mmc_api_client_secret)

def is_mmc_api_key_configured(self) -> bool:
    return bool(self.mmc_api_base_url and self.mmc_api_key)

def is_mmc_email_configured(self) -> bool:
    return bool(self.is_mmc_auth_configured() and self.mmc_api_key and self.mmc_sender_email)
```

**Note on `mmc_sender_name`:** "Kevin Taylor" is the MDInsights default. BrasilIntel
may want a different default or no default — flag for plan to decide.

### 1.6 test_auth.py Script (`scripts/test_auth.py`)

**Location in MDInsights:** `C:\BrasilIntel\mdinsights\scripts\test_auth.py`
**Lines:** 208

**What it does:**
1. Checks MMC_API_BASE_URL, MMC_API_CLIENT_ID, MMC_API_CLIENT_SECRET in env
2. Acquires a JWT token (measures latency)
3. Verifies cache hit (second call < 100ms, no network)
4. Tests `force_refresh()` (invalidates cache, re-acquires)
5. Exit codes: 0=pass, 1=token failure, 2=missing config

**BrasilIntel adaptation needed:**
- Import changes: `app.models.news_article` → `app.models.news_item`, etc.
- Model registration block must import new Phase 9 models
- Branding: "MDInsights" → "BrasilIntel" in print statements
- Staging host hint in error output (same Apigee host — no change)

---

## 2. BrasilIntel Target Analysis

### 2.1 Model Conventions

**Base class:** `from app.database import Base` — declarative_base() instance
**Pattern:** Each model in its own file in `app/models/`
**`__init__.py` pattern:** Explicit imports + `__all__` list

Current models:
- `app/models/insurer.py` → `Insurer`
- `app/models/run.py` → `Run`
- `app/models/news_item.py` → `NewsItem`

**After Phase 9, `app/models/__init__.py` needs updating to include:**
```python
from app.models.api_event import ApiEvent, ApiEventType
from app.models.factiva_config import FactivaConfig
from app.models.equity_ticker import EquityTicker
```

**SQLAlchemy style:** Column-based ORM, `Base = declarative_base()`, no `mapped_column`
— MDInsights uses same style, so models port cleanly.

### 2.2 Database Setup

**Pattern:** `SessionLocal = sessionmaker(...)`, `Base`, `engine` exported from `app.database`
**Same pattern as MDInsights** — no adaptation needed.

**Key difference:** BrasilIntel uses `SessionLocal` as a callable (not as context manager
in most places). MDInsights `_record_event()` uses `with SessionLocal() as session:` —
this works because SQLAlchemy 2.x supports context manager on sessions.
BrasilIntel already uses `with SessionLocal() as session:` in `main.py` health check —
confirmed compatible.

### 2.3 Settings / Config

**Current Settings class:** `app/config.py`
**Pattern:** Pydantic BaseSettings, `lru_cache`, `get_settings()` — identical to MDInsights

**Fields that exist in MDInsights but NOT in BrasilIntel:**
- All `mmc_*` fields — none present yet (expected; this is what Phase 9 adds)
- `is_mmc_auth_configured()`, `is_mmc_api_key_configured()`, `is_mmc_email_configured()` — not present

**Fields present in BrasilIntel but different naming from MDInsights:**

| Purpose | MDInsights | BrasilIntel |
|---------|-----------|-------------|
| MS Graph tenant | `microsoft_tenant_id` | `azure_tenant_id` |
| MS Graph client | `microsoft_client_id` | `azure_client_id` |
| MS Graph secret | `microsoft_client_secret` | `azure_client_secret` |

This naming difference only matters when porting EnterpriseEmailClient (Phase 12), not Phase 9.

### 2.4 App Structure and File Locations

**BrasilIntel app layout:**
```
app/
  main.py              — FastAPI + lifespan, no auth dir imports yet
  config.py            — Settings class
  database.py          — Base, engine, SessionLocal
  models/              — flat, one file per model
  services/            — flat, all services at same level
  routers/             — API routes
```

**MDInsights app layout:**
```
app/
  auth/                — separate package for auth (token_manager.py)
  collectors/          — separate package for enterprise collectors
  services/            — mixed scraping, classification, etc.
  models/              — flat, one file per model
```

**Flat vs. nested:** BrasilIntel is flatter than MDInsights (no `collectors/` or `auth/`
sub-packages). Two options for TokenManager location:
1. `app/auth/token_manager.py` (create new package, match MDInsights)
2. `app/services/token_manager.py` (stay flat, match BrasilIntel convention)

**Recommendation: `app/auth/token_manager.py`** — creates a clean package for auth
concerns that will grow (Phase 12 enterprise emailer uses the token). Having a dedicated
`auth/` package signals to future developers where auth logic lives. The overhead is
one `__init__.py` file.

### 2.5 Main.py Integration

**Current lifespan in BrasilIntel:** Creates DB tables, starts APScheduler.
**Phase 9 addition needed:** Import new models so they register with Base.metadata:

```python
# In app/main.py, add to model registration block:
from app.models import api_event, factiva_config, equity_ticker  # noqa: F401
```

This ensures `Base.metadata.create_all(bind=engine)` creates the new tables on startup.
No TokenManager initialization in main.py — TokenManager is instantiated lazily by the
pipeline when needed (same pattern as MDInsights).

### 2.6 Retry Patterns

**BrasilIntel current:** No tenacity imports found anywhere in `app/`. Uses basic
try/except blocks with manual logging.

**MDInsights TokenManager:** Uses `tenacity` with `@retry` decorator — the most
battle-tested retry approach for async HTTP calls.

**Decision: Add tenacity to BrasilIntel** — TokenManager is the first and only
component that needs structured retry with backoff. Adding tenacity is one dependency
but avoids hand-rolling retry logic. MDInsights's pattern is proven.

---

## 3. Dependencies and Migrations

### 3.1 New Python Dependencies

| Package | MDInsights Version | BrasilIntel Status | Notes |
|---------|-------------------|--------------------|-------|
| `httpx` | unpinned | ALREADY PRESENT (`>=0.27.0`) | No change needed |
| `tenacity` | unpinned | MISSING | Add to requirements.txt |

**Only one new dependency: `tenacity`**

BrasilIntel already has `httpx` (used for service health checks per requirements.txt
comment). Tenacity is the only gap.

**requirements.txt addition:**
```
# Phase 9 - Enterprise API Foundation
tenacity>=8.0.0
```

### 3.2 Database Migration

**Migration number:** `007` (follows `migrate_006_scheduler_tracking.py`)
**File:** `scripts/migrate_007_enterprise_api_tables.py`

**Tables to create:**
1. `api_events` — new table
2. `factiva_config` — new table + seed row (id=1)
3. `equity_tickers` — new table

**Migration pattern from existing scripts:** sqlite3 raw SQL, `ALTER TABLE` for existing
tables, `CREATE TABLE IF NOT EXISTS` for new tables, idempotent (safe to re-run).

**What the migration must do:**
```sql
-- 1. Create api_events table
CREATE TABLE IF NOT EXISTS api_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  VARCHAR(50) NOT NULL,
    api_name    VARCHAR(50) NOT NULL,
    timestamp   DATETIME NOT NULL,
    success     BOOLEAN NOT NULL,
    detail      TEXT,
    run_id      INTEGER REFERENCES runs(id)
);

-- 2. Create factiva_config table
CREATE TABLE IF NOT EXISTS factiva_config (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    industry_codes  VARCHAR(500) NOT NULL DEFAULT 'i82,i832',
    company_codes   VARCHAR(500) NOT NULL DEFAULT 'MM',
    keywords        VARCHAR(500) NOT NULL DEFAULT 'insurance reinsurance',
    page_size       INTEGER NOT NULL DEFAULT 25,
    enabled         BOOLEAN NOT NULL DEFAULT 1,
    updated_at      DATETIME,
    updated_by      VARCHAR(100)
);

-- 3. Seed factiva_config row 1 (if not exists)
INSERT OR IGNORE INTO factiva_config
    (id, industry_codes, company_codes, keywords, page_size, enabled)
VALUES
    (1, 'i82,i832', 'MM', 'insurance reinsurance', 25, 1);

-- 4. Create equity_tickers table
CREATE TABLE IF NOT EXISTS equity_tickers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name VARCHAR(200) UNIQUE NOT NULL,
    ticker      VARCHAR(20) NOT NULL,
    exchange    VARCHAR(20) NOT NULL DEFAULT 'BVMF',
    enabled     BOOLEAN NOT NULL DEFAULT 1,
    updated_at  DATETIME,
    updated_by  VARCHAR(100)
);
```

**Note on SQLAlchemy Enum:** The `event_type` column in MDInsights uses `Enum(ApiEventType)`.
SQLite stores enums as VARCHAR. The migration script uses `VARCHAR(50)` — compatible.
SQLAlchemy ORM will still enforce the enum constraint at the Python layer.

**Note on `Base.metadata.create_all`:** On a fresh database (no prior runs), startup
will create all tables automatically via `main.py`'s lifespan. The migration script
is needed for EXISTING databases that were created before Phase 9. The script is
idempotent — safe to run on both fresh and existing DBs.

---

## 4. Recommended File Layout for Phase 9

```
Changes to existing files:
  app/config.py                    — Add mmc_* fields and helper methods
  app/models/__init__.py           — Add ApiEvent, FactivaConfig, EquityTicker imports
  app/main.py                      — Add model import registrations

New files:
  app/auth/__init__.py             — Empty package init
  app/auth/token_manager.py        — OAuth2 TokenManager (ported from MDInsights)

  app/models/api_event.py          — ApiEvent + ApiEventType (port verbatim)
  app/models/factiva_config.py     — FactivaConfig (port verbatim)
  app/models/equity_ticker.py      — EquityTicker (exchange default BVMF, port otherwise)

  scripts/migrate_007_enterprise_api_tables.py  — Create 3 new tables + seed factiva_config
  scripts/test_auth.py             — Auth validation script (ported from MDInsights)
```

**Total new/changed files: 9**
- 3 existing files edited (config, models __init__, main)
- 2 new auth package files
- 3 new model files
- 1 migration script
- 1 test script

### Plan Structure Recommendation

Given the above, Phase 9 naturally divides into:

| Plan | Work | Deliverable |
|------|------|-------------|
| 09-01 | Add `mmc_*` fields to Settings, add helper methods | `app/config.py` updated |
| 09-02 | Port `api_event.py`, `factiva_config.py`, `equity_ticker.py` | 3 new model files |
| 09-03 | Write `migrate_007_enterprise_api_tables.py`, run it | 3 tables created + seeded |
| 09-04 | Port `TokenManager` to `app/auth/token_manager.py` | TokenManager ready |
| 09-05 | Port `test_auth.py`, integrate TokenManager into pipeline stub | AUTH-01..04 verified |

---

## 5. Risks and Blockers

### 5.1 No Blockers — All Source Files Present and Readable

All MDInsights source files exist and were read successfully. All BrasilIntel target
files were read. No missing dependencies or contradictions found.

### 5.2 Risks

**Risk 1: MMC API credentials not yet in BrasilIntel .env (LOW risk)**
- BrasilIntel shares the same Apigee staging host as MDInsights per CONTEXT.md
- Credentials should work without re-provisioning
- test_auth.py will confirm this; AUTH-04 ensures graceful degradation if they don't

**Risk 2: SQLAlchemy Enum dialect behavior (LOW risk)**
- MDInsights uses `Column(Enum(ApiEventType))` on SQLite
- SQLite stores enums as VARCHAR — this is confirmed working in MDInsights
- BrasilIntel uses same SQLAlchemy + SQLite stack — no issue expected

**Risk 3: tenacity `before_sleep_log` requires `logging.WARNING` from stdlib (LOW risk)**
- MDInsights imports both `structlog` and `import logging` for this
- BrasilIntel uses `structlog` in some services, `logging.getLogger` in others
- TokenManager uses `structlog.get_logger()` — same as MDInsights
- Need to import `import logging` alongside `structlog` for `before_sleep_log` call
- Not a blocker; noted for implementer

**Risk 4: `_record_event()` uses context manager on `SessionLocal` (VERIFY)**
- MDInsights: `with SessionLocal() as session:`
- BrasilIntel: `SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)`
- SQLAlchemy 2.0+ supports `with session_factory() as session:` (creates and closes session)
- BrasilIntel main.py already uses `with SessionLocal() as session:` — confirmed compatible

**Risk 5: mmc_sender_name default "Kevin Taylor" (MINOR — clarify in plan)**
- MDInsights hardcodes `mmc_sender_name: str = "Kevin Taylor"` as default
- BrasilIntel may want a different default (e.g., empty string) or environment-specific value
- No functional impact on Phase 9 (sender name is only used in Phase 12 email delivery)
- Implementer should confirm or change this default

### 5.3 Non-Issues (confirmed safe)

- `httpx` already in requirements.txt — no version conflict with TokenManager usage
- `structlog` already in requirements.txt — used identically in MDInsights
- `from app.database import SessionLocal, Base, engine` — exact same signature in both
- `from app.config import get_settings` — exact same pattern in both
- Pipeline integration: BrasilIntel's pipeline (Phase 10+) will receive TokenManager as
  Optional parameter — same Optional injection pattern as MDInsights

---

## RESEARCH COMPLETE

**Confidence:** HIGH — all assertions based on direct file reads

**Key findings:**
1. TokenManager ports with zero domain-specific changes — pure auth plumbing
2. ApiEvent and FactivaConfig port verbatim — no adaptation needed
3. EquityTicker needs one change: `exchange` default from `"NYSE"` to `"BVMF"` (B3)
4. Only one new dependency: `tenacity` (httpx already present)
5. Migration 007 must create 3 tables and seed factiva_config row 1
6. `app/auth/` package is the right home for TokenManager (creates clean boundary)
7. test_auth.py adaptation: 3 import path changes + branding strings

**Recommended plan count:** 5 plans (config → models → migration → TokenManager → test+verify)

**No blockers identified. Ready for roadmap planning.**
