# app/services/sources/__init__.py
"""
News sources package.

Provides abstract interfaces and implementations for various
news sources (Google News, RSS feeds, web crawlers, etc.).
"""
from app.services.sources.base import NewsSource, ScrapedNewsItem, SourceRegistry
from app.services.sources.google_news import GoogleNewsSource

__all__ = [
    "NewsSource",
    "ScrapedNewsItem",
    "SourceRegistry",
    "GoogleNewsSource",
]
