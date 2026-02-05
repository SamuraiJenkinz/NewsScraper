# app/services/sources/valor.py
"""
Valor Economico news source using Apify Website Content Crawler.

Valor Economico is a major Brazilian financial news outlet. Since they
don't provide RSS feeds, we use Apify's website content crawler to
scrape their insurance news section.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from apify_client import ApifyClient

from app.config import get_settings
from app.services.sources.base import NewsSource, ScrapedNewsItem, SourceRegistry, filter_by_recency

logger = logging.getLogger(__name__)


class ValorSource(NewsSource):
    """
    Valor Economico news source using Apify Website Content Crawler.

    Uses the cheerio crawler type for faster HTML parsing without
    full browser rendering. Filters to insurance-related content.
    """

    SOURCE_NAME = "valor"
    CRAWLER_ACTOR_ID = "apify/website-content-crawler"
    BASE_URL = "https://valor.globo.com"
    SEARCH_URL = "https://valor.globo.com/busca/?q="

    # Patterns to exclude non-article pages
    EXCLUDE_PATTERNS = [
        r"/video/",
        r"/podcast/",
        r"/autor/",
        r"/colunistas/",
        r"/especial/",
        r"#",  # Fragment links
    ]

    def __init__(self):
        """Initialize the Valor source with Apify client."""
        settings = get_settings()
        if not settings.is_apify_configured():
            logger.warning("Apify token not configured - Valor source will not work")
            self.client = None
            self.timeout = 120
        else:
            self.client = ApifyClient(settings.apify_token)
            self.timeout = settings.get_source_timeout("valor")

    async def search(self, query: str, max_results: int = 10) -> list[ScrapedNewsItem]:
        """
        Search Valor Economico for news matching the query.

        Uses website content crawler to search and extract articles.
        Over-fetches then filters to max_results.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of ScrapedNewsItem objects
        """
        if self.client is None:
            logger.error("Apify client not initialized - check APIFY_TOKEN")
            return []

        # Build search URL with query
        search_url = f"{self.SEARCH_URL}{query.replace(' ', '+')}"

        # Over-fetch to account for filtering
        crawl_limit = max_results * 3

        run_input = {
            "startUrls": [{"url": search_url}],
            "crawlerType": "cheerio",  # Fast HTML-only crawler
            "maxCrawlDepth": 1,  # Only crawl search results page + linked articles
            "maxCrawlPages": crawl_limit,
            "maxRequestsPerCrawl": crawl_limit,
            "includeUrlGlobs": [
                f"{self.BASE_URL}/financas/**",
                f"{self.BASE_URL}/empresas/**",
                f"{self.BASE_URL}/brasil/**",
            ],
            "excludeUrlGlobs": [
                "**/video/**",
                "**/podcast/**",
                "**/autor/**",
            ],
            "saveHtml": False,
            "saveMarkdown": True,
            "saveScreenshots": False,
        }

        logger.info(f"Starting Valor search: {query[:50]}...")

        try:
            run = self.client.actor(self.CRAWLER_ACTOR_ID).call(
                run_input=run_input,
                timeout_secs=self.timeout,
            )

            items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            logger.info(f"Crawled {len(items)} pages from Valor")

            parsed = self._parse_results(items, query)

            # Filter to valid articles and last 24 hours only
            filtered = [item for item in parsed if self._is_valid_article(item)]
            filtered = filter_by_recency(filtered)
            return filtered[:max_results]

        except Exception as e:
            logger.error(f"Valor scraping failed: {e}")
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
            user = self.client.user().get()
            return {
                "status": "ok",
                "username": user.get("username"),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _is_valid_article(self, item: ScrapedNewsItem) -> bool:
        """
        Check if the item is a valid news article.

        Filters out non-article pages like videos, podcasts, author pages.
        """
        if not item.url:
            return False

        for pattern in self.EXCLUDE_PATTERNS:
            if re.search(pattern, item.url, re.IGNORECASE):
                return False

        # Must have a title
        if not item.title or item.title == "No title":
            return False

        return True

    def _parse_results(self, items: list[dict[str, Any]], query: str) -> list[ScrapedNewsItem]:
        """
        Parse raw crawler results into ScrapedNewsItem objects.

        Extracts publication dates from URL patterns and metadata.
        """
        results = []

        for item in items:
            try:
                url = item.get("url", "")

                # Skip search results page itself
                if "busca" in url:
                    continue

                # Extract title from metadata or content
                title = (
                    item.get("metadata", {}).get("title")
                    or item.get("title")
                    or "No title"
                )

                # Clean title - remove site name suffix
                if " - Valor Econ" in title:
                    title = title.split(" - Valor Econ")[0]
                if " | Valor" in title:
                    title = title.split(" | Valor")[0]

                # Extract description
                description = (
                    item.get("metadata", {}).get("description")
                    or item.get("text", "")[:500]
                )

                # Try to extract date from URL pattern (valor uses /DD/MM/YYYY/)
                published_at = self._extract_date_from_url(url)

                # Try metadata date if URL date not found
                if not published_at:
                    date_str = item.get("metadata", {}).get("datePublished")
                    if date_str:
                        try:
                            published_at = datetime.fromisoformat(
                                date_str.replace("Z", "+00:00")
                            )
                        except ValueError:
                            pass

                news_item = ScrapedNewsItem(
                    title=title,
                    description=description,
                    url=url,
                    source="Valor Economico",
                    published_at=published_at,
                    raw_data=item,
                )
                results.append(news_item)

            except Exception as e:
                logger.warning(f"Failed to parse Valor item: {e}")
                continue

        return results

    def _extract_date_from_url(self, url: str) -> datetime | None:
        """
        Extract publication date from Valor URL patterns.

        Valor uses URL patterns like:
        /noticia/2024/01/15/article-slug
        """
        # Pattern: /YYYY/MM/DD/
        match = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
        if match:
            try:
                year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                return datetime(year, month, day)
            except ValueError:
                pass
        return None


# Auto-register on import
SourceRegistry.register(ValorSource())
