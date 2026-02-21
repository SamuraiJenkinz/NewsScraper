"""
Seed the FactivaConfig table with Brazilian insurance industry defaults.

Creates the default configuration row (id=1) with:
    - Brazilian insurance industry code (i82 — covers all insurance sub-categories)
    - Portuguese insurance keywords
    - page_size=50 (balance between coverage and API cost)
    - enabled=True

Idempotent: Safe to run multiple times — only inserts if row doesn't exist.

Usage:
    python scripts/seed_factiva_config.py
"""
import os
import sys

# Ensure project root is on path when running as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load .env before importing app modules
load_dotenv()

from app.database import SessionLocal
from app.models.factiva_config import FactivaConfig


def seed_factiva_config():
    """
    Seed FactivaConfig id=1 with Brazilian insurance industry defaults.

    Idempotent: Updates if row exists, inserts if it doesn't.
    """
    with SessionLocal() as session:
        # Check if config already exists
        existing = session.query(FactivaConfig).filter_by(id=1).first()

        # Brazilian insurance defaults
        industry_codes = "i82"
        keywords = "seguro,seguradora,resseguro,saude suplementar,plano de saude,previdencia,sinistro,apolice,corretora de seguros"
        page_size = 50

        if existing:
            # Update existing config with Brazilian defaults
            existing.industry_codes = industry_codes
            existing.company_codes = ""
            existing.keywords = keywords
            existing.page_size = page_size
            existing.enabled = True
            session.commit()

            print("Updated FactivaConfig id=1 with Brazilian insurance defaults:")
            print(f"  Industry codes: {existing.industry_codes}")
            print(f"  Keywords: {existing.keywords}")
            print(f"  Page size: {existing.page_size}")
            print(f"  Enabled: {existing.enabled}")
            return

        # Create default config
        config = FactivaConfig(
            id=1,
            industry_codes=industry_codes,
            company_codes="",
            keywords=keywords,
            page_size=page_size,
            enabled=True,
        )
        session.add(config)
        session.commit()

        print("Seeded FactivaConfig id=1 with Brazilian insurance defaults:")
        print(f"  Industry codes: {config.industry_codes}")
        print(f"  Keywords: {config.keywords}")
        print(f"  Page size: {config.page_size}")
        print(f"  Enabled: {config.enabled}")


if __name__ == "__main__":
    seed_factiva_config()
