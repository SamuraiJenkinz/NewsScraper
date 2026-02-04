"""
Batch processor for scraping news across all sources for multiple insurers.

Implements semaphore-based rate limiting and progress tracking
to handle 897 insurers without overwhelming news sources.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Awaitable

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.insurer import Insurer
from app.models.run import Run
from app.models.news_item import NewsItem
from app.services.sources import SourceRegistry, ScrapedNewsItem, NewsSource

logger = logging.getLogger(__name__)


@dataclass
class BatchProgress:
    """Tracks progress of a batch processing run."""
    total_insurers: int = 0
    processed_insurers: int = 0
    total_items_found: int = 0
    errors: list[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)

    @property
    def percent_complete(self) -> float:
        """Calculate percentage of insurers processed."""
        if self.total_insurers == 0:
            return 0.0
        return (self.processed_insurers / self.total_insurers) * 100

    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time since start."""
        return (datetime.utcnow() - self.start_time).total_seconds()


@dataclass
class InsurerResult:
    """Result of scraping a single insurer."""
    insurer_id: int
    insurer_name: str
    items: list[ScrapedNewsItem] = field(default_factory=list)
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if scraping was successful (no error)."""
        return self.error is None


class BatchProcessor:
    """
    Orchestrates batch scraping across all sources for multiple insurers.

    Features:
    - Configurable batch size (default 30, NEWS-07 requires 30-50)
    - Semaphore-based concurrency limiting
    - Delay between batches to prevent rate limiting
    - Progress tracking with callback support
    - Graceful error handling (one failure doesn't stop batch)
    """

    def __init__(
        self,
        batch_size: int | None = None,
        max_concurrent: int | None = None,
        delay_seconds: float | None = None,
        sources: list[NewsSource] | None = None,
    ):
        """
        Initialize batch processor with configuration.

        Args:
            batch_size: Number of insurers to process per batch (default from settings)
            max_concurrent: Maximum concurrent scraping operations (default from settings)
            delay_seconds: Delay between batches in seconds (default from settings)
            sources: List of news sources to use (default: all registered sources)
        """
        settings = get_settings()

        self.batch_size = batch_size or settings.batch_size
        self.max_concurrent = max_concurrent or settings.max_concurrent_sources
        self.delay_seconds = delay_seconds or settings.batch_delay_seconds
        self.max_results_per_source = settings.scrape_max_results

        # Use provided sources or all registered sources
        self.sources = sources if sources is not None else SourceRegistry.get_all()

        logger.info(
            f"BatchProcessor initialized: batch_size={self.batch_size}, "
            f"max_concurrent={self.max_concurrent}, sources={len(self.sources)}"
        )

    async def process_insurers(
        self,
        insurers: list[Insurer],
        run: Run | None = None,
        db: Session | None = None,
        progress_callback: Callable[[BatchProgress], Awaitable[None]] | None = None,
    ) -> BatchProgress:
        """
        Process a list of insurers, scraping all sources for each.

        Args:
            insurers: List of Insurer objects to process
            run: Optional Run record to update progress
            db: Database session (required if run provided)
            progress_callback: Optional async callback for progress updates

        Returns:
            BatchProgress with final statistics
        """
        progress = BatchProgress(total_insurers=len(insurers))

        if not insurers:
            logger.warning("No insurers to process")
            return progress

        if not self.sources:
            logger.error("No sources configured")
            progress.errors.append("No news sources configured")
            return progress

        logger.info(
            f"Starting batch processing: {len(insurers)} insurers, "
            f"{len(self.sources)} sources"
        )

        # Process in batches
        for batch_start in range(0, len(insurers), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(insurers))
            batch = insurers[batch_start:batch_end]

            batch_num = (batch_start // self.batch_size) + 1
            total_batches = (len(insurers) + self.batch_size - 1) // self.batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} insurers)")

            # Process batch with concurrency limiting
            results = await self._process_batch(batch)

            # Update progress
            for result in results:
                progress.processed_insurers += 1
                progress.total_items_found += len(result.items)

                if result.error:
                    progress.errors.append(f"{result.insurer_name}: {result.error}")
                    logger.warning(f"Error for {result.insurer_name}: {result.error}")

                # Store items if db provided
                if db and run:
                    await self._store_items(result, run, db)

            # Update run record if provided
            if run and db:
                run.insurers_processed = progress.processed_insurers
                run.items_found = progress.total_items_found
                db.commit()

            # Call progress callback if provided
            if progress_callback:
                await progress_callback(progress)

            # Delay between batches (except for last batch)
            if batch_end < len(insurers):
                logger.debug(f"Waiting {self.delay_seconds}s before next batch")
                await asyncio.sleep(self.delay_seconds)

        logger.info(
            f"Batch processing complete: {progress.processed_insurers} insurers, "
            f"{progress.total_items_found} items, {len(progress.errors)} errors"
        )

        return progress

    async def _process_batch(self, insurers: list[Insurer]) -> list[InsurerResult]:
        """Process a single batch of insurers with concurrency limiting."""
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def process_with_limit(insurer: Insurer) -> InsurerResult:
            async with semaphore:
                return await self._scrape_insurer(insurer)

        results = await asyncio.gather(
            *[process_with_limit(ins) for ins in insurers],
            return_exceptions=True,
        )

        # Convert exceptions to InsurerResult
        final_results = []
        for insurer, result in zip(insurers, results):
            if isinstance(result, Exception):
                final_results.append(InsurerResult(
                    insurer_id=insurer.id,
                    insurer_name=insurer.name,
                    error=str(result),
                ))
            else:
                final_results.append(result)

        return final_results

    async def _scrape_insurer(self, insurer: Insurer) -> InsurerResult:
        """Scrape all sources for a single insurer."""
        result = InsurerResult(
            insurer_id=insurer.id,
            insurer_name=insurer.name,
        )

        # Build search query - use custom search terms if available
        if insurer.search_terms:
            query = insurer.search_terms
        else:
            query = f'"{insurer.name}" OR "ANS {insurer.ans_code}"'

        # Scrape each source
        for source in self.sources:
            try:
                items = await source.search(
                    query=query,
                    max_results=self.max_results_per_source,
                )
                result.items.extend(items)

            except Exception as e:
                logger.warning(
                    f"Source {source.SOURCE_NAME} failed for {insurer.name}: {e}"
                )
                # Continue with other sources

        logger.debug(f"Scraped {len(result.items)} items for {insurer.name}")
        return result

    async def _store_items(
        self,
        result: InsurerResult,
        run: Run,
        db: Session,
    ) -> None:
        """Store scraped items in database."""
        for item in result.items:
            news_item = NewsItem(
                run_id=run.id,
                insurer_id=result.insurer_id,
                title=item.title,
                description=item.description,
                source_url=item.url,
                source_name=item.source,
                published_at=item.published_at,
                # Classification fields left null - to be filled by classifier
            )
            db.add(news_item)

        # Flush in batches to avoid lock contention
        if result.items:
            db.flush()

    async def process_category(
        self,
        category: str,
        db: Session,
        run: Run | None = None,
        enabled_only: bool = True,
        progress_callback: Callable[[BatchProgress], Awaitable[None]] | None = None,
    ) -> BatchProgress:
        """
        Convenience method to process all insurers in a category.

        Args:
            category: Category name (Health, Dental, Group Life)
            db: Database session
            run: Optional run record
            enabled_only: Only process enabled insurers (default True)
            progress_callback: Optional async callback for progress updates

        Returns:
            BatchProgress with final statistics
        """
        query = db.query(Insurer).filter(Insurer.category == category)

        if enabled_only:
            query = query.filter(Insurer.enabled == True)

        insurers = query.all()

        logger.info(f"Processing category {category}: {len(insurers)} insurers")

        return await self.process_insurers(
            insurers=insurers,
            run=run,
            db=db,
            progress_callback=progress_callback,
        )
