# Phase 10: Factiva News Collection - Research

**Researched:** 2026-02-19
**Domain:** Enterprise news aggregation via Dow Jones Factiva API
**Confidence:** HIGH

## Summary

Phase 10 integrates Dow Jones Factiva news collection as BrasilIntel's enterprise news source, replacing the current 6-source Apify/RSS scraping system. MDInsights provides a proven reference implementation that can be directly ported with minimal adaptation. The core technical stack (httpx, tenacity, sentence-transformers) is already present in BrasilIntel's requirements.txt, and Phase 9 has established all necessary infrastructure (TokenManager, ApiEvent, FactivaConfig models, migration 007).

The Factiva API uses X-Api-Key authentication only (no JWT required for news endpoints), fetches articles in batch via a search endpoint, and provides individual article body retrieval. Deduplication using sentence-transformers with 0.85 cosine similarity threshold is proven effective in MDInsights for wire-service-heavy content. The FactivaConfig model created in Phase 9 provides admin-configurable query parameters (industry codes, keywords, page size).

**Primary recommendation:** Port MDInsights' FactivaCollector and ArticleDeduplicator with minimal changes — proven code, compatible stack, established patterns.

## Standard Stack

The established libraries for Factiva news collection and semantic deduplication:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.27.0+ | HTTP client for Factiva API | Already in requirements.txt, async-ready, proven in MDInsights |
| tenacity | 8.0.0+ | Retry logic with exponential backoff | Already in requirements.txt, Phase 9 TokenManager uses it |
| sentence-transformers | latest | Semantic deduplication embeddings | MDInsights proven standard, all-MiniLM-L6-v2 model (80MB, fast) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | 24.0.0+ | Structured logging | Already in BrasilIntel, maintain consistency |
| SQLAlchemy | 2.0.0+ | ORM for NewsItem persistence | Existing BrasilIntel models |
| Pydantic | 2.0.0+ | Settings validation | Existing Settings class has MMC API config |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sentence-transformers | Manual TF-IDF + fuzzy matching | Semantic similarity (0.85 threshold) proven more accurate for wire service content in MDInsights |
| httpx | requests library | httpx already standardized in BrasilIntel for async compatibility |

**Installation:**
```bash
# Already in requirements.txt (Phase 9):
# httpx>=0.27.0
# tenacity>=8.0.0

# NEW dependency for Phase 10:
pip install sentence-transformers
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── collectors/
│   └── factiva.py           # FactivaCollector (ported from MDInsights)
├── services/
│   ├── deduplicator.py      # ArticleDeduplicator (ported from MDInsights)
│   └── scraper.py           # ScraperService (Phase 11 will integrate FactivaCollector)
├── models/
│   ├── api_event.py         # ApiEvent (Phase 9 - complete)
│   ├── factiva_config.py    # FactivaConfig (Phase 9 - complete)
│   └── news_item.py         # NewsItem (existing)
├── auth/
│   └── token_manager.py     # TokenManager (Phase 9 - complete, NOT used for news)
```

### Pattern 1: Factiva API Client with X-Api-Key Auth
**What:** Two-step Factiva workflow: (1) Batch search with industry codes/keywords, (2) Individual article body fetch
**When to use:** All Factiva news collection operations
**Example:**
```python
# Source: C:\BrasilIntel\MDInsights\app\collectors\factiva.py (MDInsights proven)
class FactivaCollector:
    BASE_SEARCH_PATH = "/coreapi/recent-news/v1/search"
    BASE_ARTICLE_PATH = "/coreapi/recent-news/v1/article"

    def _build_headers(self) -> Dict[str, str]:
        """X-Api-Key only — no JWT needed for news endpoint."""
        return {
            "X-Api-Key": self.api_key,
            "Accept": "application/json",
        }

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Factiva search with retry logic."""
        url = f"{self.base_url}{self.BASE_SEARCH_PATH}"
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params, headers=self._build_headers())
            response.raise_for_status()
            return response.json()
```

### Pattern 2: Semantic Deduplication with Union-Find
**What:** Sentence-transformers embeddings + cosine similarity + Union-Find grouping for duplicate detection
**When to use:** After Factiva batch fetch, before NewsItem persistence
**Example:**
```python
# Source: C:\BrasilIntel\MDInsights\app\services\deduplicator.py (MDInsights proven)
class ArticleDeduplicator:
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.85
    ):
        """Fast model (80MB), 0.85 threshold proven for wire service content."""
        self._model = SentenceTransformer(model_name)

    def deduplicate(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group similar articles, keep earliest by published_at, merge sources."""
        texts = [f"{article['title']} {article.get('description', '')}" for article in articles]
        embeddings = self._model.encode(texts, convert_to_tensor=True)
        cos_scores = util.cos_sim(embeddings, embeddings)

        # Union-Find groups duplicates
        uf = _UnionFind(len(articles))
        for i in range(len(articles)):
            for j in range(i + 1, len(articles)):
                if cos_scores[i][j].item() >= self.similarity_threshold:
                    uf.union(i, j)

        # Merge each group: earliest article, longest description, merged source_name
        return [self._merge_articles(articles, group) for group in groups.values()]
```

### Pattern 3: Factiva Response Normalization
**What:** Map Factiva-specific field names to BrasilIntel's NewsItem schema
**When to use:** After individual article fetch, before deduplication
**Example:**
```python
# Source: C:\BrasilIntel\MDInsights\app\collectors\factiva.py (MDInsights proven)
def _normalize_article(
    self,
    search_item: Dict[str, Any],
    article_body: Dict[str, Any],
) -> Dict[str, Any]:
    """Normalize Factiva API article to NewsItem schema."""
    return {
        "title": (search_item.get("headline") or "").strip(),
        "description": (
            article_body.get("plaintext")      # Prefer full body
            or search_item.get("snippet")      # Fall back to snippet
            or ""
        ),
        "url": (
            article_body.get("links", {}).get("self")
            or search_item.get("links", {}).get("self")
            or ""
        ),
        "published_at": datetime.fromtimestamp(
            int(search_item.get("publicationTimestampInMilliseconds", 0)) / 1000.0,
            tz=timezone.utc
        ).replace(tzinfo=None),  # Store as naive UTC
        "source_name": "Factiva",
        # Phase 11 will add insurer_id via AI matching
    }
```

### Pattern 4: ApiEvent Recording for Dashboard Observability
**What:** Record all Factiva API interactions to api_events table for Phase 14 dashboard
**When to use:** After every search, after collection complete, on failures
**Example:**
```python
# Source: C:\BrasilIntel\MDInsights\app\collectors\factiva.py (MDInsights proven)
def _record_event(
    self,
    event_type: ApiEventType,
    success: bool,
    detail: Optional[str] = None,
    run_id: Optional[int] = None,
) -> None:
    """Record news API event. Never crash if recording fails."""
    try:
        with SessionLocal() as session:
            event = ApiEvent(
                event_type=event_type,          # NEWS_FETCH
                api_name="news",
                timestamp=datetime.utcnow(),
                success=success,
                detail=detail[:500] if detail else None,  # Truncate for DB
                run_id=run_id,  # Nullable for out-of-pipeline calls
            )
            session.add(event)
            session.commit()
    except Exception as exc:
        # Never propagate DB errors into collection flow
        self.logger.warning("factiva_api_event_record_failed", error=str(exc))
```

### Anti-Patterns to Avoid
- **Don't use JWT for news endpoint:** Factiva Recent News uses X-Api-Key only (Phase 9 TokenManager is for Phase 13 email API)
- **Don't fetch individual articles in parallel without rate limit protection:** MDInsights uses sequential fetch with @retry — safe default, optimize in Phase 14 if needed
- **Don't hard-code industry codes:** Use FactivaConfig model (created in Phase 9) for admin-configurable queries
- **Don't skip deduplication:** Wire services syndicate heavily — 48-hour window means overlap, dedup is mandatory

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Semantic similarity | TF-IDF + Levenshtein distance | sentence-transformers all-MiniLM-L6-v2 | Captures semantic meaning (e.g., "insurance giant" vs "major insurer"), proven 0.85 threshold in MDInsights |
| Duplicate grouping | Nested loops with threshold checks | Union-Find data structure | O(n²) similarity checks but O(α(n)) grouping, handles transitive duplicates correctly |
| HTTP retries | Manual try/except loops | tenacity with exponential backoff | Handles transient errors (429, 5xx, network), avoids retry storms, already in requirements.txt |
| Article body fetch failures | Crash on 404 | Fall back to search snippet | Paywalled/expired articles are common, snippet provides minimal coverage |

**Key insight:** MDInsights has production-tested all these patterns with Factiva's wire-service-heavy content. Port proven code rather than reimplementing.

## Common Pitfalls

### Pitfall 1: Confusing Auth Methods (JWT vs X-Api-Key)
**What goes wrong:** Using TokenManager.get_token() for Factiva news collection
**Why it happens:** Phase 9 created TokenManager for MMC Core API, but news endpoint uses different auth
**How to avoid:**
- News/equity endpoints: X-Api-Key header only (no JWT)
- Email endpoint (Phase 13): Bearer token (JWT from TokenManager) + X-Api-Key
- Check Settings.is_mmc_api_key_configured() for news, Settings.is_mmc_email_configured() for email
**Warning signs:** 401 errors from Factiva when sending Bearer token

### Pitfall 2: Missing Deduplication Across 48-Hour Window
**What goes wrong:** Duplicate articles inserted across daily pipeline runs
**Why it happens:** 48-hour Factiva query window overlaps with previous day's fetch
**How to avoid:**
- Dedup within batch (Phase 10-03 ArticleDeduplicator)
- Phase 11 will add cross-batch dedup via database URL checks before insertion
- CONTEXT.md says "48-hour window with dedup handling cross-run overlap"
**Warning signs:** Same article appears in multiple daily reports with different timestamps

### Pitfall 3: Assuming All Articles Have Full Bodies
**What goes wrong:** description field is None or empty for paywalled/expired articles
**Why it happens:** Factiva search returns snippet for all, but individual article fetch can fail (404, 403)
**How to avoid:**
- Try individual fetch with @retry(stop_after_attempt(2))
- Catch 4xx errors and return empty dict (not raise)
- Normalizer falls back to search snippet when article_body is empty
- Log warning but don't crash collection
**Warning signs:** Empty description fields in NewsItem records, "factiva_article_fetch_failed" logs

### Pitfall 4: Not Recording API Events
**What goes wrong:** Phase 14 admin dashboard shows "no data" for Factiva health
**Why it happens:** Forgetting to call _record_event() on success/failure
**How to avoid:**
- Record NEWS_FETCH on successful collection (with article count in detail JSON)
- Record NEWS_FETCH failure on search errors (with error type in detail JSON)
- Never let event recording crash the collection flow (wrap in try/except)
**Warning signs:** api_events table has no news entries after Factiva runs

### Pitfall 5: Hard-Coding Brazilian Insurance Industry Codes
**What goes wrong:** Industry codes change, admins can't adjust queries without code deployment
**Why it happens:** Copying MDInsights' hardcoded "i82,i832" defaults
**How to avoid:**
- Use FactivaConfig.industry_codes (created in Phase 9)
- Seed migration with sensible defaults (CONTEXT.md says "Sub-sector specific")
- Phase 14 will add admin UI to edit codes
- Parse comma-separated codes at query time
**Warning signs:** No results from Factiva after insurance industry reclassification

## Code Examples

Verified patterns from MDInsights production code:

### Factiva Search Query Construction
```python
# Source: C:\BrasilIntel\MDInsights\app\collectors\factiva.py (lines 111-146)
def collect(self, query_params: Dict[str, Any], run_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Collect articles from Factiva for the past 48 hours."""
    # Date window: 48 hours (catches late-indexed articles)
    today = datetime.now(timezone.utc)
    yesterday = today - timedelta(days=2)  # 48 hours back
    from_date = yesterday.strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")

    # Parse FactivaConfig comma-separated values to lists
    industry_codes = [c.strip() for c in query_params.get("industry_codes", "").split(",") if c.strip()]
    company_codes = [c.strip() for c in query_params.get("company_codes", "").split(",") if c.strip()]
    keywords = [k.strip() for k in query_params.get("keywords", "").split(",") if k.strip()]

    # Build search params
    params = {
        "fromDate": from_date,
        "toDate": to_date,
        "sortBy": "date",
        "sortOrder": "desc",
        "deduplication": "similar",  # Factiva server-side dedup (not sufficient alone)
        "pageSize": min(query_params.get("page_size", 25), 100),  # Hard cap 100
    }
    if industry_codes:
        params["industryCodes"] = ",".join(industry_codes)
    if company_codes:
        params["companyCodes"] = ",".join(company_codes)
    if keywords:
        params["keywords"] = " ".join(keywords)

    search_response = self._search(params)
    articles_raw = search_response.get("data") or search_response.get("articles") or []

    # Fetch individual article bodies
    normalized_articles = []
    for item in articles_raw:
        article_id = item.get("articleId") or item.get("id")
        article_body = {}
        if article_id:
            try:
                article_body = self._fetch_article(str(article_id))
            except Exception:
                # Fall back to snippet if body fetch fails
                pass
        normalized_articles.append(self._normalize_article(item, article_body))

    return normalized_articles
```

### Deduplication with Survivor Selection
```python
# Source: C:\BrasilIntel\MDInsights\app\services\deduplicator.py (lines 173-224)
def _merge_articles(
    self,
    articles: List[Dict[str, Any]],
    indices: List[int]
) -> Dict[str, Any]:
    """Merge duplicate articles: earliest published_at, longest description, merged sources."""
    group_articles = [articles[i] for i in indices]

    # Sort by published_at (None values go to end)
    sorted_articles = sorted(
        group_articles,
        key=lambda a: a.get('published_at') or datetime.max
    )

    # Use earliest article as base
    keeper = sorted_articles[0].copy()

    # Merge source names (unique, preserve order)
    sources = []
    seen_sources = set()
    for article in sorted_articles:
        source = article['source_name']
        if source not in seen_sources:
            sources.append(source)
            seen_sources.add(source)

    keeper['source_name'] = ", ".join(sources)  # "Factiva, Bloomberg, Reuters"

    # Use longest description (wire services vary in snippet length)
    descriptions = [
        article.get('description', '')
        for article in sorted_articles
        if article.get('description')
    ]
    if descriptions:
        keeper['description'] = max(descriptions, key=len)

    return keeper
```

### Partial Article Body Handling
```python
# Source: C:\BrasilIntel\MDInsights\app\collectors\factiva.py (lines 318-352)
@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
)
def _fetch_article(self, article_id: str) -> Dict[str, Any]:
    """Fetch full article body. Return empty dict on 4xx (not found, paywalled)."""
    url = f"{self.base_url}{self.BASE_ARTICLE_PATH}/{article_id}"
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=self._build_headers())

        # 4xx = article unavailable (not found, paywalled, access denied)
        # Return empty dict so normalizer uses snippet fallback
        if 400 <= response.status_code < 500:
            self.logger.warning(
                "factiva_article_client_error",
                article_id=article_id,
                status_code=response.status_code,
            )
            return {}  # Normalizer will fall back to snippet

        response.raise_for_status()  # 5xx raises for retry
        return response.json()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 6 separate Apify/RSS sources | Single Factiva batch query | Phase 10 (v1.1) | Unified enterprise feed, no source-specific failures |
| Manual keyword dedup (source-specific) | Semantic dedup (cross-source) | Phase 10-03 | Catches wire service syndication across outlets |
| Per-insurer queries (897 queries) | Batch query + post-hoc AI matching | Phase 10/11 design | 1 API call vs 897, faster pipeline |
| Hardcoded search terms | FactivaConfig admin UI | Phase 10 (model), Phase 14 (UI) | Query tuning without deployment |

**Deprecated/outdated:**
- Apify scraping: Phase 15 removes all Apify source classes after Factiva proven stable
- feedparser RSS: Phase 15 removes feedparser dependency after Factiva switch
- Manual search term tweaking: Phase 14 provides admin UI for FactivaConfig

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal Brazilian Insurance Industry Codes**
   - What we know: Factiva uses DJII taxonomy with ~350,000 codes, insurance is broadly "i82"
   - What's unclear: Sub-sector codes for life/P&C/reinsurance/health plans specific to Brazil
   - Recommendation:
     - Start with MDInsights defaults ("i82,i832") in FactivaConfig seed
     - Phase 14 admin can tune based on result quality
     - Document code discovery process in admin UI help text
     - Research citations: [Dow Jones Developer Platform](https://dowjones.developerprogram.org/site/docs/factiva_apis/factiva_code_api/index.gsp), [DJII Taxonomy API](https://apitemple.com/api/djii-taxonomy)

2. **Portuguese Keyword Coverage**
   - What we know: CONTEXT.md says "Claude's discretion — researcher determines optimal Portuguese search terms"
   - What's unclear: Whether Factiva's "keywords" param requires exact terms or supports stemming/fuzzy matching
   - Recommendation:
     - Seed with broad terms: "seguro, seguradora, resseguro, saúde suplementar, plano de saúde, vida em grupo"
     - Test with/without accents: "saúde" vs "saude"
     - Phase 14 admin can refine based on precision/recall metrics
     - Monitor api_events for zero-result searches

3. **Geographic Filtering Strategy**
   - What we know: CONTEXT.md says "Claude's discretion — researcher determines best geographic filter (Brazil-only vs Brazil + international coverage)"
   - What's unclear: Factiva API parameter for geographic scope, whether Brazilian insurance news is tagged with Brazil location code
   - Recommendation:
     - Start WITHOUT geographic filter (rely on industry codes + keywords for relevance)
     - If noise is high, add "Brazil" or "Brasil" to keywords param
     - Phase 14 can add geographic codes to FactivaConfig if Factiva supports region filtering
     - Check MDInsights production logs for false positive patterns

4. **Semantic Dedup Threshold Tuning for Factiva**
   - What we know: MDInsights uses 0.85 threshold for insurance/reinsurance wire service content
   - What's unclear: Whether Brazilian Portuguese + insurance-specific vocabulary needs different threshold
   - Recommendation:
     - Start with 0.85 (proven baseline)
     - Log similarity scores for deduplicated pairs in first production week
     - If false negatives (obvious duplicates not caught), lower to 0.80
     - If false positives (distinct articles merged), raise to 0.90
     - Make threshold admin-configurable in Phase 14

## Sources

### Primary (HIGH confidence)
- **C:\BrasilIntel\MDInsights\app\collectors\factiva.py** - Production Factiva client with X-Api-Key auth, query construction, article body fetch, response normalization
- **C:\BrasilIntel\MDInsights\app\services\deduplicator.py** - Production semantic deduplicator with Union-Find, 0.85 threshold, all-MiniLM-L6-v2 model
- **C:\BrasilIntel\app\auth\token_manager.py** (Phase 9) - TokenManager implementation (NOT used for news, reference for Phase 13 email)
- **C:\BrasilIntel\app\models\factiva_config.py** (Phase 9) - FactivaConfig ORM model with industry_codes, company_codes, keywords fields
- **C:\BrasilIntel\app\models\api_event.py** (Phase 9) - ApiEvent ORM model with NEWS_FETCH event type
- **C:\BrasilIntel\requirements.txt** - Existing dependencies: httpx 0.27.0+, tenacity 8.0.0+, structlog 24.0.0+

### Secondary (MEDIUM confidence)
- [Dow Jones Developer Platform - Factiva APIs](https://dowjones.developerprogram.org/site/docs/factiva_apis/factiva_code_api/index.gsp) - Official API documentation for Factiva code taxonomy
- [Factiva APIs Documentation (Postman)](https://www.postman.com/dj-cse/dow-jones-apis/documentation/l9tpql6/factiva-apis) - API contracts and examples
- [DJII Taxonomy API](https://apitemple.com/api/djii-taxonomy) - Industry code discovery endpoint
- [GitHub - dowjones/factiva-news-python](https://github.com/dowjones/factiva-news-python) - Official Python SDK (not used, direct httpx preferred for simplicity)

### Tertiary (LOW confidence)
- WebSearch results on Factiva industry codes for Brazilian insurance — specific sub-sector codes (life/P&C/reinsurance/health) not found in public documentation, require Factiva code API discovery

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries present in requirements.txt or proven in MDInsights production
- Architecture: HIGH - MDInsights production patterns directly portable to BrasilIntel structure
- Pitfalls: HIGH - All pitfalls documented from MDInsights production experience and Phase 9 decisions

**Research date:** 2026-02-19
**Valid until:** 2026-03-21 (30 days — Factiva API stable, sentence-transformers model unchanged)

---

*Research complete. Ready for planning.*
