# app/services/scraper.py
"""
Unified scraper service for BrasilIntel.

Integrates multiple news sources with batch processing and relevance scoring.
Maintains backward compatibility with Phase 2 ApifyScraperService.
"""
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.services.sources import (
    SourceRegistry,
    ScrapedNewsItem,
    GoogleNewsSource,
)
from app.services.batch_processor import BatchProcessor, BatchProgress
from app.services.relevance_scorer import RelevanceScorer
from app.models.insurer import Insurer
from app.models.run import Run

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = ["ScrapedNewsItem", "ApifyScraperService", "ScraperService"]


class ApifyScraperService:
    """
    Legacy scraper service for backward compatibility.

    Maintained for Phase 2 code that imports ApifyScraperService.
    New code should use ScraperService instead.

    Note: This class now delegates to GoogleNewsSource internally
    while maintaining the same public interface.
    """

    # Google News scraper actor from Apify Store
    GOOGLE_NEWS_ACTOR = "lhotanova/google-news-scraper"

    def __init__(self):
        """Initialize the service with GoogleNewsSource."""
        self._google_source = GoogleNewsSource()

    def search_google_news(
        self,
        query: str,
        language: str = "pt",
        country: str = "BR",
        max_results: int = 10,
        time_filter: str = "7d",
        timeout_secs: int = 300,
    ) -> list[ScrapedNewsItem]:
        """
        Search Google News for a query string.

        Args:
            query: Search query (supports quoted phrases and OR)
            language: Language code (pt for Portuguese)
            country: Country code (BR for Brazil)
            max_results: Maximum number of results to return
            time_filter: Time range (7d, 1m, 1y, etc.)
            timeout_secs: Actor execution timeout

        Returns:
            List of ScrapedNewsItem objects

        Note: language, country, time_filter, and timeout_secs are
        currently using default values in the underlying source.
        """
        # Run the async method synchronously for backward compatibility
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, use thread pool
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._google_source.search(query, max_results)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self._google_source.search(query, max_results)
                )
        except RuntimeError:
            # No event loop exists
            return asyncio.run(self._google_source.search(query, max_results))

    def search_insurer(
        self,
        insurer_name: str,
        ans_code: str,
        max_results: int = 10,
    ) -> list[ScrapedNewsItem]:
        """
        Search for news about a specific insurer.

        Combines insurer name and ANS code in search query
        for better accuracy and relevance.

        Args:
            insurer_name: Full insurer name
            ans_code: ANS registration code
            max_results: Maximum results to return

        Returns:
            List of ScrapedNewsItem objects
        """
        return self._google_source.search_insurer(
            insurer_name=insurer_name,
            ans_code=ans_code,
            max_results=max_results,
        )

    def health_check(self) -> dict[str, Any]:
        """
        Check Apify service connectivity.

        Returns dict with status and any error message.
        """
        # Run the async method synchronously
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._google_source.health_check()
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self._google_source.health_check()
                )
        except RuntimeError:
            return asyncio.run(self._google_source.health_check())


class ScraperService:
    """
    Unified scraper service with multi-source support.

    Integrates:
    - 6 news sources (Google News, InfoMoney, Estadao, ANS, Valor, CQCS)
    - Batch processing for 897 insurers
    - Relevance scoring pre-filter

    This is the recommended service for Phase 3+ code.
    """

    def __init__(
        self,
        sources: list[str] | None = None,
        use_relevance_scoring: bool = True,
    ):
        """
        Initialize scraper service.

        Args:
            sources: List of source names to use (default: all registered)
            use_relevance_scoring: Whether to filter by relevance (default: True)
        """
        settings = get_settings()

        # Get sources from registry
        if sources:
            self.sources = [
                SourceRegistry.get(name)
                for name in sources
                if SourceRegistry.get(name)
            ]
        else:
            self.sources = SourceRegistry.get_all()

        # Initialize batch processor with selected sources
        self.batch_processor = BatchProcessor(sources=self.sources)

        # Initialize relevance scorer
        self.use_relevance_scoring = use_relevance_scoring
        self.relevance_scorer = RelevanceScorer() if use_relevance_scoring else None

        logger.info(
            f"ScraperService initialized: {len(self.sources)} sources, "
            f"relevance_scoring={use_relevance_scoring}"
        )

    async def scrape_insurer(
        self,
        insurer: Insurer,
        max_results_per_source: int = 10,
    ) -> list[ScrapedNewsItem]:
        """
        Scrape all sources for a single insurer.

        Args:
            insurer: Insurer object to scrape for
            max_results_per_source: Max results per source

        Returns:
            List of scraped and relevance-filtered items
        """
        all_items: list[ScrapedNewsItem] = []

        # Build search query - use custom search terms if available
        if hasattr(insurer, 'search_terms') and insurer.search_terms:
            query = insurer.search_terms
        else:
            query = f'"{insurer.name}" OR "ANS {insurer.ans_code}"'

        # Scrape each source
        for source in self.sources:
            try:
                items = await source.search(query, max_results_per_source)
                all_items.extend(items)
                logger.debug(f"Source {source.SOURCE_NAME}: {len(items)} items")
            except Exception as e:
                logger.warning(f"Source {source.SOURCE_NAME} failed: {e}")

        # Apply relevance scoring if enabled
        if self.relevance_scorer and all_items:
            all_items = self.relevance_scorer.score_batch(
                items=all_items,
                insurer_name=insurer.name,
                max_results=max_results_per_source * len(self.sources),
            )
            logger.debug(f"After relevance filter: {len(all_items)} items")

        return all_items

    async def process_category(
        self,
        category: str,
        db: Session,
        run: Run | None = None,
        enabled_only: bool = True,
    ) -> BatchProgress:
        """
        Process all insurers in a category.

        Args:
            category: Category name (Health, Dental, Group Life)
            db: Database session
            run: Optional run record for tracking
            enabled_only: Only process enabled insurers

        Returns:
            BatchProgress with statistics
        """
        return await self.batch_processor.process_category(
            category=category,
            db=db,
            run=run,
            enabled_only=enabled_only,
        )

    async def process_insurers(
        self,
        insurers: list[Insurer],
        run: Run | None = None,
        db: Session | None = None,
    ) -> BatchProgress:
        """
        Process a specific list of insurers.

        Args:
            insurers: List of insurers to process
            run: Optional run record
            db: Database session

        Returns:
            BatchProgress with statistics
        """
        return await self.batch_processor.process_insurers(
            insurers=insurers,
            run=run,
            db=db,
        )

    def health_check(self) -> dict[str, Any]:
        """Check all sources and components."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def check_all():
            results = {
                "status": "ok",
                "sources": {},
                "sources_count": len(self.sources),
                "relevance_scoring": self.use_relevance_scoring,
                "batch_processor": {
                    "batch_size": self.batch_processor.batch_size,
                    "max_concurrent": self.batch_processor.max_concurrent,
                    "delay_seconds": self.batch_processor.delay_seconds,
                },
            }

            # Check each source
            errors = 0
            for source in self.sources:
                try:
                    hc = await source.health_check()
                    results["sources"][source.SOURCE_NAME] = hc
                    if hc.get("status") != "ok":
                        errors += 1
                except Exception as e:
                    results["sources"][source.SOURCE_NAME] = {
                        "status": "error",
                        "message": str(e)
                    }
                    errors += 1

            if errors > 0:
                results["status"] = "degraded" if errors < len(self.sources) else "error"
                results["errors"] = errors

            # Check relevance scorer
            if self.relevance_scorer:
                results["relevance_scorer"] = self.relevance_scorer.health_check()

            return results

        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, check_all())
                return future.result()
        else:
            return loop.run_until_complete(check_all())

    @property
    def source_names(self) -> list[str]:
        """Get list of configured source names."""
        return [s.SOURCE_NAME for s in self.sources]
