# app/services/sources/google_news.py
"""
Google News source implementation using Apify.

Uses the lhotanova/google-news-scraper actor to fetch news
about Brazilian insurers with proper rate limiting.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from apify_client import ApifyClient

from app.config import get_settings
from app.services.sources.base import NewsSource, ScrapedNewsItem, SourceRegistry

logger = logging.getLogger(__name__)


class GoogleNewsSource(NewsSource):
    """
    Google News source using Apify actor.

    Implements the NewsSource interface for Google News searches
    targeting Brazilian Portuguese content.
    """

    SOURCE_NAME = "google_news"
    ACTOR_ID = "lhotanova/google-news-scraper"

    def __init__(self):
        """Initialize the Google News source with Apify client."""
        settings = get_settings()
        if not settings.is_apify_configured():
            logger.warning("Apify token not configured - Google News source will not work")
            self.client = None
        else:
            self.client = ApifyClient(settings.apify_token)

    async def search(self, query: str, max_results: int = 10) -> list[ScrapedNewsItem]:
        """
        Search Google News for a query string.

        Args:
            query: Search query (supports quoted phrases and OR)
            max_results: Maximum number of results to return

        Returns:
            List of ScrapedNewsItem objects

        Note:
            The method is marked async for interface consistency but
            internally uses the sync Apify client.call(). The batch
            processor handles async orchestration.
        """
        if self.client is None:
            logger.error("Apify client not initialized - check APIFY_TOKEN")
            return []

        run_input = {
            "queries": query,
            "language": "BR:pt",  # Combined country:language format
            "maxItems": max_results,
            "timeRange": "7d",
        }

        logger.info(f"Starting Google News search: {query[:100]}...")

        try:
            # Run actor and wait for completion
            run = self.client.actor(self.ACTOR_ID).call(
                run_input=run_input,
                timeout_secs=300,
            )

            # Retrieve results from default dataset
            items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            logger.info(f"Found {len(items)} news items for query")

            return self._parse_results(items)

        except Exception as e:
            logger.error(f"Google News scraping failed: {e}")
            return []

    async def health_check(self) -> dict:
        """
        Check Apify service connectivity.

        Returns:
            Dict with status and any error message.
        """
        if self.client is None:
            return {"status": "error", "message": "APIFY_TOKEN not configured"}

        try:
            # Try to get user info as a connectivity test
            user = self.client.user().get()
            return {
                "status": "ok",
                "username": user.get("username"),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def search_insurer(
        self,
        insurer_name: str,
        ans_code: str,
        max_results: int = 10,
    ) -> list[ScrapedNewsItem]:
        """
        Search for news about a specific insurer.

        Convenience method that builds an appropriate query using
        the insurer name and ANS code for better matching.

        Args:
            insurer_name: Full insurer name
            ans_code: ANS registration code
            max_results: Maximum results to return

        Returns:
            List of ScrapedNewsItem objects
        """
        # Build query with name and ANS code for better matching
        # Use quotes for exact phrase matching on name
        query = f'"{insurer_name}" OR "ANS {ans_code}"'

        # Run the async method synchronously for backward compatibility
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.search(query, max_results))
                    return future.result()
            else:
                return loop.run_until_complete(self.search(query, max_results))
        except RuntimeError:
            # No event loop exists
            return asyncio.run(self.search(query, max_results))

    def _parse_results(self, items: list[dict[str, Any]]) -> list[ScrapedNewsItem]:
        """
        Parse raw Apify results into ScrapedNewsItem objects.

        Handles various field names and missing data gracefully.
        """
        results = []

        for item in items:
            try:
                # Extract publication date if available
                published_at = None
                date_str = item.get("publishedAt") or item.get("date")
                if date_str:
                    try:
                        # Handle various date formats
                        if isinstance(date_str, str):
                            # Try ISO format first
                            published_at = datetime.fromisoformat(
                                date_str.replace("Z", "+00:00")
                            )
                    except ValueError:
                        logger.debug(f"Could not parse date: {date_str}")

                news_item = ScrapedNewsItem(
                    title=item.get("title", "No title"),
                    description=item.get("description") or item.get("snippet"),
                    url=item.get("link") or item.get("url"),
                    source=item.get("source") or item.get("publisher"),
                    published_at=published_at,
                    raw_data=item,
                )
                results.append(news_item)

            except Exception as e:
                logger.warning(f"Failed to parse news item: {e}")
                continue

        return results


# Auto-register on import
SourceRegistry.register(GoogleNewsSource())
