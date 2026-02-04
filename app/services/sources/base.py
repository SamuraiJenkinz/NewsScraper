# app/services/sources/base.py
"""
News source abstraction layer.

Provides abstract base class for news sources and a registry
for discovering and managing registered sources.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar


@dataclass
class ScrapedNewsItem:
    """
    Represents a scraped news item from any news source.

    This is the common data structure returned by all news source
    implementations, providing a unified interface for downstream
    processing regardless of the source.
    """
    title: str
    description: str | None = None
    url: str | None = None
    source: str | None = None
    published_at: datetime | None = None
    raw_data: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        title_preview = self.title[:50] if self.title else "No title"
        return f"ScrapedNewsItem(title={title_preview}..., source={self.source})"


class NewsSource(ABC):
    """
    Abstract base class for news sources.

    All news sources must implement this interface to be used
    interchangeably in the news collection pipeline.

    Subclasses must:
    - Define SOURCE_NAME class variable
    - Implement search() method for querying news
    - Implement health_check() method for connectivity verification
    """

    SOURCE_NAME: ClassVar[str]

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> list[ScrapedNewsItem]:
        """
        Search for news items matching the query.

        Args:
            query: Search query string (may include boolean operators)
            max_results: Maximum number of results to return

        Returns:
            List of ScrapedNewsItem objects matching the query
        """
        pass

    @abstractmethod
    async def health_check(self) -> dict:
        """
        Check source connectivity and availability.

        Returns:
            Dict with "status" key ("ok" or "error") and optional
            "message" key for error details.
        """
        pass


class SourceRegistry:
    """
    Registry for managing news source instances.

    Provides source discovery and lookup by name. Sources auto-register
    themselves on module import.

    Usage:
        # Get a specific source
        google = SourceRegistry.get("google_news")

        # Iterate all sources
        for source in SourceRegistry.get_all():
            results = await source.search("query")
    """

    _sources: ClassVar[dict[str, NewsSource]] = {}

    @classmethod
    def register(cls, source: NewsSource) -> None:
        """
        Register a news source instance.

        Args:
            source: NewsSource instance to register
        """
        cls._sources[source.SOURCE_NAME] = source

    @classmethod
    def get(cls, name: str) -> NewsSource | None:
        """
        Get a registered source by name.

        Args:
            name: Source name (e.g., "google_news")

        Returns:
            NewsSource instance or None if not found
        """
        return cls._sources.get(name)

    @classmethod
    def get_all(cls) -> list[NewsSource]:
        """
        Get all registered sources.

        Returns:
            List of all registered NewsSource instances
        """
        return list(cls._sources.values())

    @classmethod
    def names(cls) -> list[str]:
        """
        Get all registered source names.

        Returns:
            List of source names
        """
        return list(cls._sources.keys())

    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered sources.

        Mainly useful for testing.
        """
        cls._sources.clear()
