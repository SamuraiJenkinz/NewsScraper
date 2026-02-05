# app/services/sources/cqcs.py
"""
CQCS news source using Apify Website Content Crawler.

CQCS (Centro de Qualificacao do Corretor de Seguros) is a Brazilian
insurance industry news portal. Since they may have anti-bot protection,
we use the playwright:firefox crawler type for better compatibility.
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


class CQCSSource(NewsSource):
    """
    CQCS news source using Apify Website Content Crawler.

    Uses playwright:firefox crawler for better anti-bot compatibility.
    Lower concurrency to avoid rate limiting.
    """

    SOURCE_NAME = "cqcs"
    CRAWLER_ACTOR_ID = "apify/website-content-crawler"
    BASE_URL = "https://cqcs.com.br"
    NEWS_URL = "https://cqcs.com.br/category/noticias/"

    # Insurance-related keywords for filtering
    INSURANCE_KEYWORDS = [
        "seguro",
        "seguradora",
        "seguros",
        "plano de saude",
        "planos de saude",
        "odontologico",
        "previdencia",
        "resseguro",
        "corretora",
        "corretoras",
        "sinistro",
        "apolice",
        "franquia",
        "ans",
        "susep",
    ]

    def __init__(self):
        """Initialize the CQCS source with Apify client."""
        settings = get_settings()
        if not settings.is_apify_configured():
            logger.warning("Apify token not configured - CQCS source will not work")
            self.client = None
            self.timeout = 120
        else:
            self.client = ApifyClient(settings.apify_token)
            self.timeout = settings.get_source_timeout("cqcs")

    async def search(self, query: str, max_results: int = 10) -> list[ScrapedNewsItem]:
        """
        Search CQCS for news matching the query.

        Crawls the news section and filters by query keywords.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of ScrapedNewsItem objects
        """
        if self.client is None:
            logger.error("Apify client not initialized - check APIFY_TOKEN")
            return []

        # CQCS may not have direct search - crawl news section instead
        # Over-fetch to account for keyword filtering
        crawl_limit = max_results * 5

        run_input = {
            "startUrls": [{"url": self.NEWS_URL}],
            "crawlerType": "playwright:firefox",  # Browser-based for anti-bot
            "maxCrawlDepth": 2,  # News list + articles
            "maxCrawlPages": crawl_limit,
            "maxRequestsPerCrawl": crawl_limit,
            "maxConcurrency": 2,  # Lower concurrency to avoid rate limits
            "requestTimeoutSecs": 60,
            "navigationTimeoutSecs": 45,
            "maxRequestRetries": 3,  # Retry on failures
            "includeUrlGlobs": [
                f"{self.BASE_URL}/noticias/**",
                f"{self.BASE_URL}/category/noticias/**",
            ],
            "saveHtml": False,
            "saveMarkdown": True,
            "saveScreenshots": False,
        }

        logger.info(f"Starting CQCS crawl for: {query[:50]}...")

        try:
            run = self.client.actor(self.CRAWLER_ACTOR_ID).call(
                run_input=run_input,
                timeout_secs=self.timeout,
            )

            items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            logger.info(f"Crawled {len(items)} pages from CQCS")

            parsed = self._parse_results(items)

            # Filter by query keywords
            query_lower = query.lower()
            query_terms = [term.strip().lower() for term in query_lower.replace('"', '').split(' OR ')]
            query_terms = [t for t in query_terms if t and t not in ('or', 'and')]

            filtered = []
            for item in parsed:
                if self._matches_query(item, query_terms):
                    filtered.append(item)

            # Filter to last 24 hours only
            filtered = filter_by_recency(filtered)
            return filtered[:max_results]

        except Exception as e:
            logger.error(f"CQCS scraping failed: {e}")
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

    def _matches_query(self, item: ScrapedNewsItem, query_terms: list[str]) -> bool:
        """
        Check if the item matches any of the query terms.

        Searches in title, description, and URL.
        """
        searchable = " ".join([
            item.title or "",
            item.description or "",
            item.url or "",
        ]).lower()

        for term in query_terms:
            if term in searchable:
                return True
        return False

    def _parse_results(self, items: list[dict[str, Any]]) -> list[ScrapedNewsItem]:
        """
        Parse raw crawler results into ScrapedNewsItem objects.
        """
        results = []

        for item in items:
            try:
                url = item.get("url", "")

                # Skip category/listing pages
                if url.endswith("/noticias/") or "/page/" in url:
                    continue

                # Must be an article URL
                if "/noticias/" not in url and "/category/" in url:
                    continue

                # Extract title
                title = (
                    item.get("metadata", {}).get("title")
                    or item.get("title")
                    or "No title"
                )

                # Clean title - remove site suffix
                if " - CQCS" in title:
                    title = title.split(" - CQCS")[0]
                if " | CQCS" in title:
                    title = title.split(" | CQCS")[0]

                # Skip if no meaningful title
                if not title or title == "No title" or len(title) < 10:
                    continue

                # Extract description
                description = (
                    item.get("metadata", {}).get("description")
                    or item.get("text", "")[:500]
                )

                # Try to extract date from metadata
                published_at = None
                date_str = item.get("metadata", {}).get("datePublished")
                if date_str:
                    try:
                        published_at = datetime.fromisoformat(
                            date_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass

                # Try URL pattern if no metadata date
                if not published_at:
                    published_at = self._extract_date_from_url(url)

                news_item = ScrapedNewsItem(
                    title=title,
                    description=description,
                    url=url,
                    source="CQCS",
                    published_at=published_at,
                    raw_data=item,
                )
                results.append(news_item)

            except Exception as e:
                logger.warning(f"Failed to parse CQCS item: {e}")
                continue

        return results

    def _extract_date_from_url(self, url: str) -> datetime | None:
        """
        Extract publication date from CQCS URL patterns.

        CQCS may use patterns like /2024/01/15/article-slug
        """
        match = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
        if match:
            try:
                year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                return datetime(year, month, day)
            except ValueError:
                pass
        return None


# Auto-register on import
SourceRegistry.register(CQCSSource())
