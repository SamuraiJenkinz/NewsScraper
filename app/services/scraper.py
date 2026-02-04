# app/services/scraper.py
"""
Apify-based web scraper service for Google News.

Uses the lhotanova/google-news-scraper actor to fetch news
about Brazilian insurers with proper rate limiting.
"""
import logging
from typing import Any
from datetime import datetime

from apify_client import ApifyClient

from app.config import get_settings

logger = logging.getLogger(__name__)


class ScrapedNewsItem:
    """Represents a scraped news item from Google News."""

    def __init__(
        self,
        title: str,
        description: str | None = None,
        url: str | None = None,
        source: str | None = None,
        published_at: datetime | None = None,
        raw_data: dict | None = None,
    ):
        self.title = title
        self.description = description
        self.url = url
        self.source = source
        self.published_at = published_at
        self.raw_data = raw_data or {}

    def __repr__(self) -> str:
        return f"ScrapedNewsItem(title={self.title[:50]}..., source={self.source})"


class ApifyScraperService:
    """
    Service for scraping Google News using Apify actors.

    Wraps the Apify client and provides methods for searching
    news about specific insurers using their name and ANS code.
    """

    # Google News scraper actor from Apify Store
    GOOGLE_NEWS_ACTOR = "lhotanova/google-news-scraper"

    def __init__(self):
        settings = get_settings()
        if not settings.is_apify_configured():
            logger.warning("Apify token not configured - scraping will fail")
            self.client = None
        else:
            self.client = ApifyClient(settings.apify_token)

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
        """
        if not self.client:
            logger.error("Apify client not initialized - check APIFY_TOKEN")
            return []

        run_input = {
            "queries": query,
            "language": language,
            "country": country,
            "maxItems": max_results,
            "timeRange": time_filter,
        }

        logger.info(f"Starting Google News search: {query[:100]}...")

        try:
            # Run actor and wait for completion
            run = self.client.actor(self.GOOGLE_NEWS_ACTOR).call(
                run_input=run_input,
                timeout_secs=timeout_secs,
            )

            # Retrieve results from default dataset
            items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            logger.info(f"Found {len(items)} news items for query")

            return self._parse_results(items)

        except Exception as e:
            logger.error(f"Apify scraping failed: {e}")
            return []

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
        # Build query with name and ANS code for better matching
        # Use quotes for exact phrase matching on name
        query = f'"{insurer_name}" OR "ANS {ans_code}"'

        return self.search_google_news(
            query=query,
            max_results=max_results,
        )

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

    def health_check(self) -> dict[str, Any]:
        """
        Check Apify service connectivity.

        Returns dict with status and any error message.
        """
        if not self.client:
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
