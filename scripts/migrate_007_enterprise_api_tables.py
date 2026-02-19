"""
Migration 007: Create enterprise API tables for Phase 9 integration.

Creates three new tables needed for enterprise API integration (Phases 9-14):
  - api_events      : Enterprise API event log (auth, news, equity, email)
  - factiva_config  : Admin-configurable Factiva query parameters (seeded row id=1)
  - equity_tickers  : Entity-to-ticker mappings for equity price enrichment

Run with: python scripts/migrate_007_enterprise_api_tables.py
"""
import sqlite3
import sys
from pathlib import Path


# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "brasilintel.db"


def get_existing_tables(cursor) -> set:
    """Get set of existing table names in the database."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cursor.fetchall()}


def migrate():
    """Run the migration — idempotent, safe to re-run."""
    if not DB_PATH.exists():
        print(f"[INFO] Database not found at {DB_PATH}")
        print("[INFO] Database will be created automatically when the application first runs.")
        print("[INFO] Migration skipped — tables will be created by SQLAlchemy on startup.")
        sys.exit(0)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        existing_tables = get_existing_tables(cursor)
        print(f"[INFO] Existing tables: {sorted(existing_tables)}")

        # ------------------------------------------------------------------ #
        # 1. api_events — enterprise API event log
        # ------------------------------------------------------------------ #
        if "api_events" in existing_tables:
            print("[SKIP] Table 'api_events' already exists")
        else:
            print("[CREATE] Creating table 'api_events'...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_events (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type  VARCHAR(50) NOT NULL,
                    api_name    VARCHAR(50) NOT NULL,
                    timestamp   DATETIME NOT NULL,
                    success     BOOLEAN NOT NULL,
                    detail      TEXT,
                    run_id      INTEGER REFERENCES runs(id)
                )
            """)
            print("[OK]   Table 'api_events' created")

        # ------------------------------------------------------------------ #
        # 2. factiva_config — admin-configurable Factiva query parameters
        # ------------------------------------------------------------------ #
        if "factiva_config" in existing_tables:
            print("[SKIP] Table 'factiva_config' already exists")
        else:
            print("[CREATE] Creating table 'factiva_config'...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS factiva_config (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    industry_codes  VARCHAR(500) NOT NULL DEFAULT 'i82,i832',
                    company_codes   VARCHAR(500) NOT NULL DEFAULT 'MM',
                    keywords        VARCHAR(500) NOT NULL DEFAULT 'insurance reinsurance',
                    page_size       INTEGER NOT NULL DEFAULT 25,
                    enabled         BOOLEAN NOT NULL DEFAULT 1,
                    updated_at      DATETIME,
                    updated_by      VARCHAR(100)
                )
            """)
            print("[OK]   Table 'factiva_config' created")

        # Seed the default configuration row (idempotent — INSERT OR IGNORE)
        cursor.execute("""
            INSERT OR IGNORE INTO factiva_config
                (id, industry_codes, company_codes, keywords, page_size, enabled)
            VALUES
                (1, 'i82,i832', 'MM', 'insurance reinsurance', 25, 1)
        """)
        if cursor.rowcount > 0:
            print("[SEED] Inserted default factiva_config row (id=1)")
        else:
            print("[SKIP] factiva_config row id=1 already exists")

        # ------------------------------------------------------------------ #
        # 3. equity_tickers — entity-to-ticker mappings (BVMF default)
        # ------------------------------------------------------------------ #
        if "equity_tickers" in existing_tables:
            print("[SKIP] Table 'equity_tickers' already exists")
        else:
            print("[CREATE] Creating table 'equity_tickers'...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS equity_tickers (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_name VARCHAR(200) UNIQUE NOT NULL,
                    ticker      VARCHAR(20) NOT NULL,
                    exchange    VARCHAR(20) NOT NULL DEFAULT 'BVMF',
                    enabled     BOOLEAN NOT NULL DEFAULT 1,
                    updated_at  DATETIME,
                    updated_by  VARCHAR(100)
                )
            """)
            print("[OK]   Table 'equity_tickers' created")

        conn.commit()

        # ------------------------------------------------------------------ #
        # Verification
        # ------------------------------------------------------------------ #
        final_tables = get_existing_tables(cursor)
        required = {"api_events", "factiva_config", "equity_tickers"}
        missing = required - final_tables

        print()
        if missing:
            print(f"[ERROR] Missing tables after migration: {missing}")
            sys.exit(1)
        else:
            print("[DONE] Migration 007 complete — all enterprise API tables present")
            for tbl in sorted(required):
                print(f"       - {tbl}")

        # Verify seed row
        cursor.execute("SELECT id, industry_codes, keywords, enabled FROM factiva_config WHERE id=1")
        row = cursor.fetchone()
        if row:
            print(f"[VERIFY] factiva_config id=1: industry_codes='{row[1]}', keywords='{row[2]}', enabled={row[3]}")
        else:
            print("[WARN] factiva_config seed row id=1 not found")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Migration 007: Enterprise API Tables")
    print("=" * 60)
    migrate()
