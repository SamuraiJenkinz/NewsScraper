"""
Migration 008: Add date_range_hours column to factiva_config table.

Adds a configurable date range column for Factiva lookback window (24h, 48h, 7d).
Default is 48 hours to match the existing hardcoded behavior.

Run with: python scripts/migrate_008_factiva_date_range.py
"""
import sqlite3
import sys
from pathlib import Path


# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "brasilintel.db"


def get_columns(cursor, table_name: str) -> set:
    """Get set of column names for a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def migrate():
    """Run the migration — idempotent, safe to re-run."""
    if not DB_PATH.exists():
        print(f"[INFO] Database not found at {DB_PATH}")
        print("[INFO] Database will be created automatically when the application first runs.")
        print("[INFO] Migration skipped — column will be created by SQLAlchemy on startup.")
        sys.exit(0)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if factiva_config table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='factiva_config'")
        if not cursor.fetchone():
            print("[INFO] Table 'factiva_config' does not exist yet")
            print("[INFO] Migration skipped — table will be created by SQLAlchemy on startup.")
            sys.exit(0)

        # Get existing columns
        existing_columns = get_columns(cursor, "factiva_config")
        print(f"[INFO] Existing columns: {sorted(existing_columns)}")

        # Add date_range_hours column if it doesn't exist
        if "date_range_hours" in existing_columns:
            print("[SKIP] Column 'date_range_hours' already exists")
        else:
            print("[ALTER] Adding column 'date_range_hours' to factiva_config...")
            cursor.execute("""
                ALTER TABLE factiva_config
                ADD COLUMN date_range_hours INTEGER NOT NULL DEFAULT 48
            """)
            print("[OK]   Column 'date_range_hours' added")

        conn.commit()

        # Verification
        final_columns = get_columns(cursor, "factiva_config")
        if "date_range_hours" not in final_columns:
            print("[ERROR] Column 'date_range_hours' not found after migration")
            sys.exit(1)

        print()
        print("[DONE] Migration 008 complete — date_range_hours column present")
        print(f"       Columns: {sorted(final_columns)}")

        # Verify current config row
        cursor.execute("SELECT id, date_range_hours, enabled FROM factiva_config WHERE id=1")
        row = cursor.fetchone()
        if row:
            print(f"[VERIFY] factiva_config id=1: date_range_hours={row[1]}, enabled={row[2]}")
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
    print("Migration 008: Factiva Date Range Column")
    print("=" * 60)
    migrate()
