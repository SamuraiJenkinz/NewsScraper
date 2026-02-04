# Phase 3: News Collection Scale - Research

**Researched:** 2026-02-04
**Domain:** Multi-source web scraping, batch processing, AI relevance filtering
**Confidence:** MEDIUM (mixed findings - some sources verified, others require validation)

## Summary

This research investigated how to scale news collection from 1 source (Google News) to 6 sources while processing 897 insurers efficiently. The key challenge is that **no direct Apify actors exist for the 5 additional Brazilian news sources** (Valor Economico, InfoMoney, CQCS, ANS, Broadcast/Estadao). The solution requires a hybrid approach: RSS feed scraping for sources with feeds, and generic web scraping (Cheerio/Web Scraper) for sources without.

For batch processing 897 insurers, Python's asyncio with semaphore-based concurrency limiting provides the cleanest pattern. Apify's SDK handles rate limiting automatically with exponential backoff, but the application should implement its own batching (30-50 insurers) with configurable delays between batches to avoid overwhelming any single source.

AI relevance scoring before classification is straightforward using Azure OpenAI with a lightweight prompt that returns a binary relevant/not-relevant decision, filtering out low-value content before the more expensive full classification call.

**Primary recommendation:** Use RSS feeds where available (InfoMoney, Estadao, ANS gov.br), Apify's Website Content Crawler for dynamic sites without RSS (Valor Economico, CQCS), and implement batch processing with asyncio semaphores at the application level.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| apify-client | 1.x | Apify SDK for Python | Already in use, handles rate limiting with automatic retry |
| asyncio | stdlib | Async batch processing | Built-in, no dependencies, semaphore support |
| aiohttp | 3.9+ | Async HTTP for RSS fetching | Standard for async HTTP in Python |
| feedparser | 6.x | RSS/Atom feed parsing | Industry standard, handles edge cases |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | 8.x | Retry with backoff | Custom retry logic beyond Apify's built-in |
| httpx | 0.27+ | Alternative async HTTP | If aiohttp causes issues |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| feedparser | Custom XML parsing | feedparser handles malformed feeds, edge cases |
| aiohttp | requests + ThreadPoolExecutor | Less efficient, more complex |
| asyncio.Semaphore | aiometer library | aiometer adds rate-per-second, but semaphore is simpler |

**Installation:**
```bash
pip install apify-client aiohttp feedparser tenacity
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── services/
│   ├── scraper.py           # Existing - extend with source registry
│   ├── sources/             # NEW: One module per news source
│   │   ├── __init__.py
│   │   ├── base.py          # Abstract base class for sources
│   │   ├── google_news.py   # Existing logic refactored
│   │   ├── rss_source.py    # Generic RSS handler
│   │   ├── infomoney.py     # RSS-based
│   │   ├── estadao.py       # RSS-based
│   │   ├── ans.py           # Gov.br RSS-based
│   │   ├── valor.py         # Website crawler based
│   │   └── cqcs.py          # Website crawler based
│   ├── batch_processor.py   # NEW: Orchestrates batch scraping
│   └── relevance_scorer.py  # NEW: AI pre-filter
```

### Pattern 1: Source Abstraction with Registry
**What:** Abstract base class for news sources with automatic registration
**When to use:** When supporting multiple sources with different implementations
**Example:**
```python
# Source: Verified pattern from existing codebase
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

@dataclass
class ScrapedNewsItem:
    title: str
    description: str | None = None
    url: str | None = None
    source: str | None = None
    published_at: datetime | None = None
    raw_data: dict | None = None

class NewsSource(ABC):
    """Abstract base for all news sources."""
    SOURCE_NAME: ClassVar[str]

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> list[ScrapedNewsItem]:
        """Search source for query, return standardized items."""
        pass

    @abstractmethod
    async def health_check(self) -> dict:
        """Check source availability."""
        pass

class SourceRegistry:
    """Registry of available news sources."""
    _sources: dict[str, NewsSource] = {}

    @classmethod
    def register(cls, source: NewsSource):
        cls._sources[source.SOURCE_NAME] = source

    @classmethod
    def get_all_sources(cls) -> list[NewsSource]:
        return list(cls._sources.values())
```

### Pattern 2: Semaphore-Based Batch Processing
**What:** Process insurers in batches with concurrency limiting
**When to use:** Processing 897 insurers without overwhelming sources
**Example:**
```python
# Source: asyncio documentation + verified patterns
import asyncio
from typing import Callable, TypeVar

T = TypeVar('T')

async def process_in_batches(
    items: list[T],
    processor: Callable[[T], Coroutine],
    batch_size: int = 30,
    max_concurrent: int = 5,
    delay_between_batches: float = 2.0,
) -> list:
    """Process items in batches with rate limiting."""
    results = []
    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_process(item: T):
        async with semaphore:
            return await processor(item)

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = await asyncio.gather(
            *[limited_process(item) for item in batch],
            return_exceptions=True
        )
        results.extend(batch_results)

        # Rate limit between batches
        if i + batch_size < len(items):
            await asyncio.sleep(delay_between_batches)

    return results
```

### Pattern 3: RSS Feed Source Implementation
**What:** Generic RSS source with feedparser
**When to use:** For InfoMoney, Estadao, ANS
**Example:**
```python
# Source: feedparser documentation
import feedparser
import aiohttp
from datetime import datetime

class RSSNewsSource(NewsSource):
    """Generic RSS feed source."""

    def __init__(self, feed_url: str, source_name: str):
        self.feed_url = feed_url
        self.SOURCE_NAME = source_name

    async def search(self, query: str, max_results: int = 10) -> list[ScrapedNewsItem]:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.feed_url) as response:
                content = await response.text()

        feed = feedparser.parse(content)
        items = []

        query_lower = query.lower()
        for entry in feed.entries[:max_results * 3]:  # Over-fetch for filtering
            title = entry.get('title', '')
            description = entry.get('description', '') or entry.get('summary', '')

            # Basic keyword matching
            if query_lower in title.lower() or query_lower in description.lower():
                items.append(ScrapedNewsItem(
                    title=title,
                    description=description,
                    url=entry.get('link'),
                    source=self.SOURCE_NAME,
                    published_at=self._parse_date(entry),
                ))

                if len(items) >= max_results:
                    break

        return items

    def _parse_date(self, entry) -> datetime | None:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            return datetime(*entry.published_parsed[:6])
        return None
```

### Pattern 4: Website Crawler Source (Apify)
**What:** Use Apify Website Content Crawler for sites without RSS
**When to use:** Valor Economico, CQCS
**Example:**
```python
# Source: Apify documentation
from apify_client import ApifyClient

class ApifyWebsiteSource(NewsSource):
    """Website scraper using Apify Website Content Crawler."""

    ACTOR_ID = "apify/website-content-crawler"

    def __init__(self, base_url: str, source_name: str, search_path: str = "/busca"):
        self.base_url = base_url
        self.search_path = search_path
        self.SOURCE_NAME = source_name
        self.client = ApifyClient(settings.apify_token)

    async def search(self, query: str, max_results: int = 10) -> list[ScrapedNewsItem]:
        search_url = f"{self.base_url}{self.search_path}?q={quote(query)}"

        run_input = {
            "startUrls": [{"url": search_url}],
            "maxCrawlPages": max_results,
            "crawlerType": "cheerio",  # Faster than browser
            "maxConcurrency": 5,
        }

        try:
            run = self.client.actor(self.ACTOR_ID).call(
                run_input=run_input,
                timeout_secs=120,
            )

            items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            return self._parse_results(items)
        except Exception as e:
            logger.error(f"Website scrape failed for {self.SOURCE_NAME}: {e}")
            return []
```

### Anti-Patterns to Avoid
- **Sequential Processing:** Processing 897 insurers one at a time takes hours. Use batching with async.
- **Unbounded Concurrency:** Using `asyncio.gather(*all_tasks)` without semaphore overwhelms sources.
- **Hardcoded Source Logic:** Each source in scraper.py becomes unmaintainable. Use source abstraction.
- **Ignoring Rate Limits:** Apify has 60 req/sec per resource default. Implement delays.
- **Retry Without Backoff:** Immediate retries compound failures. Use exponential backoff.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RSS parsing | Custom XML parser | feedparser | Handles encoding, malformed XML, date formats |
| Rate limiting | Sleep + counter | asyncio.Semaphore | Thread-safe, proven pattern |
| HTTP retries | Try/except loops | tenacity or Apify SDK | Exponential backoff, jitter |
| Date parsing | strptime chains | feedparser + dateutil | International formats, timezones |
| Concurrent batching | ThreadPoolExecutor | asyncio + Semaphore | GIL-free, memory efficient |

**Key insight:** Web scraping has many edge cases (encoding, malformed HTML, varying date formats, rate limits). Libraries like feedparser and Apify SDK encode years of fixes.

## Common Pitfalls

### Pitfall 1: Memory Exhaustion with Large Batches
**What goes wrong:** Creating 897 tasks upfront with `asyncio.gather()` consumes excessive memory
**Why it happens:** All coroutines are instantiated before any complete
**How to avoid:** Process in explicit batches (30-50 items), yielding between batches
**Warning signs:** Memory usage grows linearly with insurer count

### Pitfall 2: Source-Specific Rate Limiting
**What goes wrong:** One source (e.g., CQCS) blocks IP while others work fine
**Why it happens:** Different sites have different rate limit thresholds
**How to avoid:** Implement per-source rate limiting configuration
**Warning signs:** 403/429 errors from specific sources only

### Pitfall 3: Stale RSS Feed Data
**What goes wrong:** RSS feeds show same old articles repeatedly
**Why it happens:** Many RSS feeds only update every 2-6 hours, cache aggressively
**How to avoid:** Track last-seen URLs per source, deduplicate by URL
**Warning signs:** Duplicate news items in database

### Pitfall 4: Timeout Cascades
**What goes wrong:** One slow source blocks entire batch
**Why it happens:** Default timeouts too long, no per-task timeout
**How to avoid:** Set aggressive per-source timeouts (30-60s), use `asyncio.wait_for()`
**Warning signs:** Runs take hours instead of minutes

### Pitfall 5: AI Relevance Scoring Token Costs
**What goes wrong:** Sending all 10,000+ scraped items to Azure OpenAI for relevance scoring
**Why it happens:** Treating AI scoring as free/instant
**How to avoid:** First filter by keyword matching, then AI score only marginal cases
**Warning signs:** Azure OpenAI costs spike unexpectedly

### Pitfall 6: Missing Source Attribution
**What goes wrong:** News items stored without knowing which source they came from
**Why it happens:** Generic scraper loses source context
**How to avoid:** Always attach source_name at scraping time, not later
**Warning signs:** Cannot debug which source produces bad data

## Code Examples

Verified patterns from official sources:

### Relevance Scoring with Azure OpenAI
```python
# Source: Existing ClassificationService pattern
RELEVANCE_PROMPT = """Você é um filtro de relevância para notícias de seguradoras.
Avalie se a notícia é relevante para monitoramento de risco da seguradora.

Notícia irrelevante:
- Propaganda/marketing genérico
- Notícias de outras empresas/setores
- Conteúdo repetido/duplicado
- Artigos muito antigos (>7 dias)

Responda apenas: RELEVANT ou IRRELEVANT"""

class RelevanceScorer:
    """Pre-filter news before expensive classification."""

    async def score_batch(
        self,
        insurer_name: str,
        items: list[ScrapedNewsItem],
    ) -> list[ScrapedNewsItem]:
        """Filter items by AI relevance scoring."""
        if not items:
            return []

        # First pass: keyword filtering (free)
        keyword_filtered = [
            item for item in items
            if self._keyword_match(insurer_name, item)
        ]

        # Second pass: AI scoring (only if needed, max 20 items)
        if len(keyword_filtered) > 20:
            # Use AI to rank and filter
            return await self._ai_filter(insurer_name, keyword_filtered[:50])

        return keyword_filtered

    def _keyword_match(self, insurer_name: str, item: ScrapedNewsItem) -> bool:
        """Fast keyword-based relevance check."""
        text = f"{item.title} {item.description or ''}".lower()
        name_parts = insurer_name.lower().split()
        return any(part in text for part in name_parts if len(part) > 3)
```

### Batch Processor with Progress Tracking
```python
# Source: asyncio patterns + existing Run model
class BatchProcessor:
    """Orchestrates batch scraping across all sources."""

    def __init__(
        self,
        sources: list[NewsSource],
        batch_size: int = 30,
        max_concurrent: int = 5,
        delay_seconds: float = 2.0,
    ):
        self.sources = sources
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.delay = delay_seconds

    async def process_insurers(
        self,
        insurers: list[Insurer],
        run: Run,
        db: Session,
    ) -> int:
        """Process all insurers, updating run progress."""
        total_items = 0
        semaphore = asyncio.Semaphore(self.max_concurrent)

        for i in range(0, len(insurers), self.batch_size):
            batch = insurers[i:i + self.batch_size]

            async def process_one(insurer: Insurer):
                async with semaphore:
                    return await self._scrape_insurer(insurer)

            results = await asyncio.gather(
                *[process_one(ins) for ins in batch],
                return_exceptions=True,
            )

            # Store results, count items
            for insurer, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(f"Failed for {insurer.name}: {result}")
                    continue
                total_items += len(result)
                await self._store_items(result, insurer, run, db)

            # Update progress
            run.insurers_processed = min(i + self.batch_size, len(insurers))
            db.commit()

            # Rate limit between batches
            if i + self.batch_size < len(insurers):
                await asyncio.sleep(self.delay)

        return total_items
```

## News Source Configuration

### Source-Specific Details (Research Findings)

| Source | Type | URL/Feed | Search Method | Confidence |
|--------|------|----------|---------------|------------|
| Google News | Apify Actor | lhotanova/google-news-scraper | Query string | HIGH - already working |
| InfoMoney | RSS Feed | infomoney.com.br/mercados/feed | RSS + keyword filter | MEDIUM - feed URLs verified |
| Estadao | RSS Feed | estadao.com.br/economia + other sections | RSS + keyword filter | MEDIUM - feed structure verified |
| ANS | Gov.br RSS | gov.br/ans/pt-br/assuntos/noticias/RSS | RSS scrape | MEDIUM - pattern verified |
| Valor Economico | Website Scraper | valor.globo.com | Apify Website Crawler | LOW - no RSS, needs testing |
| CQCS | Website Scraper | cqcs.com.br/noticias | Apify Website Crawler | LOW - 403 on direct access |

### RSS Feed URLs (Verified)
```python
RSS_SOURCES = {
    "InfoMoney Markets": "https://www.infomoney.com.br/mercados/feed",
    "InfoMoney Economy": "https://www.infomoney.com.br/economia/feed",
    "InfoMoney Business": "https://www.infomoney.com.br/business/feed",
    "Estadao Economy": "https://estadao.com.br/economia/rss",  # Needs verification
    "ANS News": "https://www.gov.br/ans/pt-br/assuntos/noticias/RSS",  # Pattern-based
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ThreadPoolExecutor | asyncio + Semaphore | Python 3.11+ | Better memory, simpler code |
| requests | aiohttp/httpx | 2023+ | Non-blocking HTTP |
| Manual RSS parsing | feedparser | Stable | Handles edge cases |
| Single scraper class | Source abstraction | Best practice | Maintainable, testable |

**Deprecated/outdated:**
- `apify/actor-crawler-cheerio`: Deprecated, use `apify/cheerio-scraper` or `apify/website-content-crawler`
- `sxd/the-simple-rss-feed-scraper`: Deprecated on Apify Store

## Open Questions

Things that couldn't be fully resolved:

1. **CQCS Accessibility**
   - What we know: Direct WebFetch returned 403 Forbidden
   - What's unclear: Whether Apify actors can bypass, or if auth is needed
   - Recommendation: Test with Apify Website Content Crawler; may need to deprioritize or find alternative

2. **Valor Economico Exact Search URL**
   - What we know: It's part of Globo network (valor.globo.com)
   - What's unclear: Exact search endpoint and result page structure
   - Recommendation: Manual testing needed; may require Playwright for dynamic content

3. **ANS Feed Reliability**
   - What we know: Pattern is gov.br/[agency]/RSS, old feedburner link may be stale
   - What's unclear: Whether current gov.br/ans has working RSS
   - Recommendation: Test gov.br/ans/pt-br/assuntos/noticias/RSS directly

4. **Optimal Batch Size**
   - What we know: 30-50 is typical recommendation
   - What's unclear: Actual limits for these specific sources
   - Recommendation: Start with 30, monitor, adjust based on error rates

## Sources

### Primary (HIGH confidence)
- [Apify Documentation - Platform Limits](https://docs.apify.com/platform/limits) - Rate limits, concurrent runs
- [Apify Documentation - Rate Limiting](https://docs.apify.com/academy/anti-scraping/techniques/rate-limiting) - Best practices
- [Apify Website Content Crawler](https://apify.com/apify/website-content-crawler) - Generic scraping
- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html) - Semaphore patterns

### Secondary (MEDIUM confidence)
- [InfoMoney RSS Feeds - FeedSpot](https://rss.feedspot.com/infomoney_rss_feeds/) - Feed URL structure
- [Estadao RSS Feeds - FeedSpot](https://rss.feedspot.com/estadao_rss_feeds/) - Feed URL structure
- [Gov.br RSS Documentation](https://www.gov.br/pt-br/rss) - Pattern for government feeds
- [ANS News Page](https://www.gov.br/ans/pt-br/assuntos/noticias) - Official news source

### Tertiary (LOW confidence)
- CQCS website structure - Could not access due to 403
- Valor Economico search endpoint - Not verified
- Broadcast/Estadao integration - Unclear if separate from main Estadao

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using established libraries (apify-client, feedparser, asyncio)
- Architecture: HIGH - Source abstraction and batch processing are proven patterns
- News source details: MEDIUM - RSS feeds verified via FeedSpot, but direct testing needed
- Pitfalls: MEDIUM - Based on web scraping best practices, not this specific project

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (30 days - RSS feeds and Apify actors relatively stable)
