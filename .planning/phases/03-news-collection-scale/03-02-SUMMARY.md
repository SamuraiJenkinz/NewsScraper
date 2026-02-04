---
phase: 03-news-collection-scale
plan: 02
subsystem: news-sources
tags: [rss, feedparser, aiohttp, infomoney, estadao, ans]
dependencies:
  requires: ["03-01"]
  provides: ["RSSNewsSource", "InfoMoneySource", "EstadaoSource", "ANSSource"]
  affects: ["03-04", "03-06"]
tech-stack:
  added: ["feedparser>=6.0.0", "aiohttp>=3.9.0"]
  patterns: ["RSS feed parsing", "async concurrent fetching", "keyword filtering"]
key-files:
  created:
    - app/services/sources/rss_source.py
    - app/services/sources/infomoney.py
    - app/services/sources/estadao.py
    - app/services/sources/ans.py
  modified:
    - requirements.txt
    - app/services/sources/__init__.py
decisions:
  - id: RSS-GET
    description: "Use GET instead of HEAD for health checks (some servers block HEAD)"
  - id: G1-ESTADAO
    description: "Use G1 Economia RSS for EstadaoSource (Estadao deprecated their RSS feeds)"
metrics:
  duration: "~4 minutes"
  completed: "2026-02-04"
---

# Phase 03 Plan 02: RSS Sources Summary

Generic RSS feed source with feedparser/aiohttp plus InfoMoney, G1 Economia, and ANS implementations.

## What Was Built

### RSSNewsSource Base Class
- `app/services/sources/rss_source.py`
- Concurrent feed fetching with aiohttp ClientSession
- feedparser handles malformed XML, encoding, date formats
- Keyword filtering supports quoted phrases and OR syntax
- Description truncated to 500 chars for memory efficiency
- Graceful error handling returns empty list on failures

### InfoMoney Source (NEWS-03)
- `app/services/sources/infomoney.py`
- 3 RSS feeds: mercados, economia, business sections
- Auto-registers with SourceRegistry on import

### Estadao/G1 Source (NEWS-06)
- `app/services/sources/estadao.py`
- Uses G1 Economia RSS (Estadao deprecated their feeds)
- SOURCE_NAME kept as 'estadao' for backward compatibility

### ANS Source (NEWS-05)
- `app/services/sources/ans.py`
- Official gov.br regulatory news feed
- 1 feed URL for ANS releases

## Key Implementation Details

### Async Feed Fetching
```python
async with aiohttp.ClientSession() as session:
    tasks = [self._fetch_feed(session, url) for url in self.FEED_URLS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Keyword Filtering
```python
# Handles: '"Bradesco Saude" OR "ANS 123456"'
cleaned = query_lower.replace('"', " ").replace(" or ", " ")
keywords = [w.strip() for w in cleaned.split() if len(w.strip()) > 2]
```

### Date Parsing
- Uses feedparser's parsed date structs (published_parsed, updated_parsed)
- Graceful fallback if date parsing fails

## Deviations from Plan

### [Rule 3 - Blocking] Estadao RSS Feeds Deprecated
- **Found during:** Task 3
- **Issue:** Estadao.com.br RSS endpoints return HTTP 404
- **Fix:** Substituted G1 Economia RSS (Globo) as working alternative
- **Files modified:** app/services/sources/estadao.py
- **Commit:** d6f8b4d

### [Rule 1 - Bug] Health Check HEAD Blocked
- **Found during:** Task 3 verification
- **Issue:** ANS gov.br blocks HEAD requests (HTTP 403)
- **Fix:** Changed health_check to use GET instead of HEAD
- **Files modified:** app/services/sources/rss_source.py
- **Commit:** d6f8b4d

## Commits

| Hash | Type | Description |
|------|------|-------------|
| b155081 | chore | Add feedparser and aiohttp dependencies |
| 2ae73a3 | feat | Add generic RSS news source base class |
| d6f8b4d | feat | Add InfoMoney, Estadao (G1), and ANS RSS sources |

## Verification Results

```
Dependencies: feedparser 6.0.12, aiohttp 3.12.15
Sources registered: ['google_news', 'infomoney', 'estadao', 'ans', 'valor', 'cqcs']
All 3 new RSS sources registered
All sources inherit from RSSNewsSource
Feed URLs:
   InfoMoney: 3 feeds
   Estadao: 1 feeds (G1 Economia)
   ANS: 1 feeds
Backward compatibility: scraper.py OK
```

## Requirements Coverage

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| NEWS-03 (InfoMoney) | DONE | InfoMoneySource with 3 RSS feeds |
| NEWS-05 (ANS releases) | DONE | ANSSource with gov.br RSS |
| NEWS-06 (Broadcast/Estadao) | DONE | EstadaoSource with G1 Economia RSS |

## Next Phase Readiness

**Blockers:** None

**Ready for:**
- Plan 03-04: Batch Processor (can process items from RSS sources)
- Plan 03-05: Relevance Scorer (RSS items have same ScrapedNewsItem format)
- Plan 03-06: Integration (RSS sources in SourceRegistry)
