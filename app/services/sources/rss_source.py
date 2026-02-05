# app/services/sources/rss_source.py
"""
Generic RSS feed news source using feedparser and aiohttp.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import ClassVar

import aiohttp
import feedparser

from app.services.sources.base import NewsSource, ScrapedNewsItem, filter_by_recency

logger = logging.getLogger(__name__)


class RSSNewsSource(NewsSource):
    """
    Base class for RSS feed news sources.

    Subclasses should set FEED_URLS and SOURCE_NAME.
    """

    SOURCE_NAME: ClassVar[str] = "rss_generic"
    FEED_URLS: ClassVar[list[str]] = []
    TIMEOUT_SECONDS: ClassVar[int] = 30

    async def search(self, query: str, max_results: int = 10) -> list[ScrapedNewsItem]:
        """
        Search RSS feeds for items matching query.

        Fetches all configured feeds, filters by query keywords,
        returns up to max_results items.
        """
        if not self.FEED_URLS:
            logger.warning(f"{self.SOURCE_NAME}: No feed URLs configured")
            return []

        all_items: list[ScrapedNewsItem] = []

        # Fetch all feeds concurrently
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_feed(session, url) for url in self.FEED_URLS]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect items from successful fetches
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"{self.SOURCE_NAME}: Feed fetch error: {result}")
                continue
            all_items.extend(result)

        # Filter by query
        filtered = self._filter_by_query(all_items, query)

        # Filter to last 24 hours only
        filtered = filter_by_recency(filtered)

        # Sort by date (newest first) and limit
        filtered.sort(key=lambda x: x.published_at or datetime.min, reverse=True)

        return filtered[:max_results]

    async def _fetch_feed(
        self, session: aiohttp.ClientSession, url: str
    ) -> list[ScrapedNewsItem]:
        """Fetch and parse a single RSS feed."""
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
            ) as response:
                if response.status != 200:
                    logger.warning(f"{self.SOURCE_NAME}: HTTP {response.status} for {url}")
                    return []

                content = await response.text()

            # feedparser.parse is sync but fast
            feed = feedparser.parse(content)

            if feed.bozo and not feed.entries:
                logger.warning(f"{self.SOURCE_NAME}: Malformed feed at {url}")
                return []

            items = []
            for entry in feed.entries:
                item = self._parse_entry(entry)
                if item:
                    items.append(item)

            return items

        except asyncio.TimeoutError:
            logger.error(f"{self.SOURCE_NAME}: Timeout fetching {url}")
            return []
        except Exception as e:
            logger.error(f"{self.SOURCE_NAME}: Error fetching {url}: {e}")
            return []

    def _parse_entry(self, entry: feedparser.FeedParserDict) -> ScrapedNewsItem | None:
        """Parse a feed entry into ScrapedNewsItem."""
        title = entry.get("title", "").strip()
        if not title:
            return None

        description = entry.get("summary", "") or entry.get("description", "")

        # Parse publication date
        published_at = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published_at = datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                published_at = datetime(*entry.updated_parsed[:6])
            except (TypeError, ValueError):
                pass

        return ScrapedNewsItem(
            title=title,
            description=description[:500] if description else None,
            url=entry.get("link"),
            source=self.SOURCE_NAME,
            published_at=published_at,
            raw_data=dict(entry),
        )

    def _filter_by_query(
        self, items: list[ScrapedNewsItem], query: str
    ) -> list[ScrapedNewsItem]:
        """Filter items by query keywords."""
        if not query:
            return items

        # Extract keywords from query (handle quotes and OR)
        # e.g., '"Bradesco Saude" OR "ANS 123456"' -> ['bradesco', 'saude', 'ans', '123456']
        query_lower = query.lower()
        # Remove quotes and OR, split into words
        cleaned = query_lower.replace('"', " ").replace(" or ", " ")
        keywords = [w.strip() for w in cleaned.split() if len(w.strip()) > 2]

        if not keywords:
            return items

        filtered = []
        for item in items:
            text = f"{item.title} {item.description or ''}".lower()
            if any(kw in text for kw in keywords):
                filtered.append(item)

        return filtered

    async def health_check(self) -> dict:
        """Check if feeds are accessible."""
        if not self.FEED_URLS:
            return {"status": "error", "message": "No feed URLs configured"}

        try:
            async with aiohttp.ClientSession() as session:
                # Use GET instead of HEAD - some servers block HEAD requests
                async with session.get(
                    self.FEED_URLS[0], timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status < 400:
                        return {"status": "ok", "feeds": len(self.FEED_URLS)}
                    return {"status": "error", "message": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
