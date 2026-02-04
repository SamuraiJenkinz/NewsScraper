"""
Standalone migration script to add category_indicators column.

Run with: python scripts/migrate_004_category_indicators.py

This migration adds the category_indicators column to the news_items table
to store comma-separated list of classification categories like financial_crisis,
regulatory_action, m_and_a, etc.
"""
import sqlite3
import os
import sys


def migrate():
    """Add category_indicators column to news_items table."""
    # Get database path relative to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    db_path = os.path.join(project_root, 'data', 'brasilintel.db')

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("Database will be created automatically when the application first runs.")
        return 0

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(news_items)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'category_indicators' in columns:
            print("✓ category_indicators column already exists in news_items table")
            conn.close()
            return 0

        # Add column
        print("Adding category_indicators column to news_items table...")
        cursor.execute("ALTER TABLE news_items ADD COLUMN category_indicators VARCHAR(500)")
        conn.commit()
        print("✓ Successfully added category_indicators column to news_items table")

        conn.close()
        return 0

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(migrate())
