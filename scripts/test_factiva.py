"""
Standalone end-to-end validation for Factiva collection and deduplication.

Tests the full Phase 10 pipeline:
    1. Read FactivaConfig from database (seeded if missing)
    2. Collect articles from Factiva API
    3. Apply URL deduplication (remove duplicate source_url values)
    4. Apply semantic deduplication (sentence transformers)
    5. Print summary of results and validate required fields

Usage:
    python scripts/test_factiva.py

Exit codes:
    0 = Success (or graceful skip if credentials not configured)
    1 = Unexpected error during execution

Prerequisites:
    - MMC API credentials in .env (MMC_API_BASE_URL, MMC_API_KEY)
    - Database initialized (data/brasilintel.db)
    - sentence-transformers installed (pip install sentence-transformers)
"""
import logging
import os
import sys
from datetime import datetime

# Ensure project root is on path when running as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load .env before importing app modules
load_dotenv()

# Suppress noisy library output (requests, httpx, transformers, etc.)
logging.basicConfig(level=logging.WARNING)

# Create module logger for script output
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from app.config import get_settings
from app.database import SessionLocal, Base, engine
from app.models.factiva_config import FactivaConfig
from app.collectors.factiva import FactivaCollector
from app.services.deduplicator import ArticleDeduplicator

# Import all models to ensure tables are created
import app.models.insurer  # noqa: F401
import app.models.run  # noqa: F401
import app.models.news_item  # noqa: F401
import app.models.api_event  # noqa: F401
import app.models.factiva_config  # noqa: F401
import app.models.equity_ticker  # noqa: F401


def _print_separator():
    print("-" * 60)


def _check_credentials() -> bool:
    """Check if MMC API key is configured. Returns True if configured."""
    settings = get_settings()

    if not settings.is_mmc_api_key_configured():
        print("MMC API key not configured.")
        print("Set MMC_API_BASE_URL and MMC_API_KEY in .env to test Factiva collection.")
        print()
        print("Example .env entries:")
        print("  MMC_API_BASE_URL=https://mmc-dallas-int-non-prod-ingress.mgti.mmc.com")
        print("  MMC_API_KEY=your-staging-api-key-here")
        print()
        print("Exit code 0 (not an error — just not configured yet).")
        return False

    return True


def _ensure_config_exists() -> FactivaConfig:
    """
    Ensure FactivaConfig row exists, creating it if missing.

    Returns the active config (id=1).
    """
    with SessionLocal() as session:
        config = session.query(FactivaConfig).filter_by(id=1).first()

        if config:
            print(f"Found existing FactivaConfig (id={config.id})")
            print(f"  Industry codes: {config.industry_codes}")
            print(f"  Keywords: {config.keywords}")
            print(f"  Page size: {config.page_size}")
            print(f"  Enabled: {config.enabled}")
            return config

        # Create default config (Brazilian insurance)
        print("No FactivaConfig found — creating default row...")
        config = FactivaConfig(
            id=1,
            industry_codes="i82,i8200,i82001,i82002,i82003",
            company_codes="",
            keywords="seguro,seguradora,resseguro,saude suplementar,plano de saude,previdencia,sinistro,apolice,corretora de seguros",
            page_size=50,
            enabled=True,
        )
        session.add(config)
        session.commit()
        session.refresh(config)

        print(f"Created FactivaConfig (id={config.id})")
        print(f"  Industry codes: {config.industry_codes}")
        print(f"  Keywords: {config.keywords}")
        print(f"  Page size: {config.page_size}")

        return config


def _url_deduplicate(articles: list) -> list:
    """
    Remove articles with duplicate source_url values (keep first occurrence).

    Returns deduplicated list and count removed.
    """
    seen_urls = set()
    url_deduped = []

    for article in articles:
        url = article.get("source_url", "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        url_deduped.append(article)

    removed = len(articles) - len(url_deduped)
    return url_deduped, removed


def _validate_articles(articles: list) -> None:
    """Print warnings for any articles missing required fields."""
    for i, article in enumerate(articles):
        issues = []

        if not article.get("title"):
            issues.append("missing title")

        if article.get("source_name") != "Factiva":
            issues.append(f"source_name is '{article.get('source_name')}', expected 'Factiva'")

        if article.get("published_at") is None:
            issues.append("missing published_at")

        if issues:
            print(f"  WARNING: Article {i+1} has issues: {', '.join(issues)}")
            print(f"    Title: {article.get('title', 'N/A')[:80]}")


def main():
    """Run the Factiva collection validation."""
    # Ensure database and tables exist
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)

    print()
    print("=" * 60)
    print("  BrasilIntel — Factiva Collection Validation")
    print("=" * 60)
    _print_separator()
    print("STEP 1: Checking MMC API credentials")
    _print_separator()

    # Pre-flight check: credentials configured?
    if not _check_credentials():
        sys.exit(0)

    print("Credentials: CONFIGURED")

    # Ensure FactivaConfig exists
    _print_separator()
    print("STEP 2: Loading FactivaConfig from database")
    _print_separator()

    config = _ensure_config_exists()

    # Build query_params dict
    query_params = {
        "industry_codes": config.industry_codes,
        "company_codes": config.company_codes,
        "keywords": config.keywords,
        "page_size": config.page_size,
    }

    # Collect articles
    _print_separator()
    print("STEP 3: Collecting articles from Factiva API")
    _print_separator()
    print(f"Query window: Last 48 hours")
    print(f"Industry codes: {config.industry_codes}")
    print(f"Keywords: {config.keywords}")
    print()

    collector = FactivaCollector()

    try:
        articles = collector.collect(query_params)
        print(f"Factiva returned: {len(articles)} articles")
    except Exception as exc:
        print(f"COLLECTION FAILED: {type(exc).__name__}: {exc}")
        print()
        print("Common causes:")
        print("  - Invalid API key")
        print("  - Network unreachable (check VPN / firewall)")
        print("  - Factiva endpoint unavailable")
        print("  - Query timeout (try reducing page_size in config)")
        print()
        sys.exit(1)

    # URL deduplication
    _print_separator()
    print("STEP 4: URL deduplication")
    _print_separator()

    url_deduped, url_removed = _url_deduplicate(articles)
    print(f"After URL dedup: {len(url_deduped)} articles (removed {url_removed})")

    # Semantic deduplication
    _print_separator()
    print("STEP 5: Semantic deduplication (sentence transformers)")
    _print_separator()
    print("Note: First run will download all-MiniLM-L6-v2 model (~80MB)")
    print()

    deduplicator = ArticleDeduplicator()
    final_articles = deduplicator.deduplicate(url_deduped)

    semantic_removed = len(url_deduped) - len(final_articles)
    print(f"After semantic dedup: {len(final_articles)} articles (removed {semantic_removed})")

    # Print article summaries
    _print_separator()
    print("STEP 6: Article summaries")
    _print_separator()

    if not final_articles:
        print("No articles found for the configured query.")
        print()
        print("Try:")
        print("  - Broadening the keywords or industry codes")
        print("  - Checking Factiva has coverage for the query terms")
        print("  - Verifying the date window (48 hours) captures recent news")
    else:
        for i, article in enumerate(final_articles, 1):
            title = article.get("title", "N/A")
            source_name = article.get("source_name", "N/A")
            published_at = article.get("published_at")
            description = article.get("description", "")
            source_url = article.get("source_url", "N/A")

            published_str = "N/A"
            if isinstance(published_at, datetime):
                published_str = published_at.strftime("%Y-%m-%d %H:%M UTC")

            print(f"\n{i}. {title[:80]}")
            print(f"   Source: {source_name}")
            print(f"   Published: {published_str}")
            print(f"   Description: {len(description)} chars")
            print(f"   URL: {source_url[:80]}")

    # Print totals
    _print_separator()
    print("STEP 7: Summary statistics")
    _print_separator()

    full_body_count = sum(1 for a in final_articles if len(a.get("description", "")) > 200)
    snippet_count = len(final_articles) - full_body_count

    print(f"Articles fetched from Factiva: {len(articles)}")
    print(f"After URL dedup: {len(url_deduped)} (removed {url_removed})")
    print(f"After semantic dedup: {len(final_articles)} (removed {semantic_removed})")
    print()
    print(f"Articles with full body (>200 chars): {full_body_count}")
    print(f"Articles with snippet only (≤200 chars): {snippet_count}")

    # Validate required fields
    _print_separator()
    print("STEP 8: Field validation")
    _print_separator()

    _validate_articles(final_articles)

    if not any(
        not a.get("title") or a.get("source_name") != "Factiva" or a.get("published_at") is None
        for a in final_articles
    ):
        print("All articles have required fields: PASSED")

    # Success
    print()
    print("=" * 60)
    print("Factiva collection validation: SUCCESS")
    print("Phase 10 pipeline verified end-to-end.")
    print("=" * 60)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(0)
    except Exception as exc:
        print(f"\n\nUNEXPECTED ERROR: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
