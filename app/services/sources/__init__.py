# app/services/sources/__init__.py
"""
News sources package.

Provides abstract interfaces and implementations for various
news sources (Google News, RSS feeds, web crawlers, etc.).
"""
from app.services.sources.base import NewsSource, ScrapedNewsItem, SourceRegistry
from app.services.sources.google_news import GoogleNewsSource
from app.services.sources.rss_source import RSSNewsSource
from app.services.sources.infomoney import InfoMoneySource
from app.services.sources.estadao import EstadaoSource
from app.services.sources.ans import ANSSource
from app.services.sources.valor import ValorSource
from app.services.sources.cqcs import CQCSSource

__all__ = [
    "NewsSource",
    "ScrapedNewsItem",
    "SourceRegistry",
    "GoogleNewsSource",
    "RSSNewsSource",
    "InfoMoneySource",
    "EstadaoSource",
    "ANSSource",
    "ValorSource",
    "CQCSSource",
]
