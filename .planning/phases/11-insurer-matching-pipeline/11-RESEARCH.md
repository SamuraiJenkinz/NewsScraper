# Phase 11: Insurer Matching Pipeline — Research Findings

**Researched:** 2026-02-19
**Confidence:** HIGH
**Domain:** News article to insurer entity matching in Brazilian insurance intelligence system

## Executive Summary

Phase 11 implements a hybrid matching system that assigns Factiva articles to specific insurers from the 902 tracked Brazilian insurance companies. The system combines deterministic string matching for clear cases with AI-assisted disambiguation for ambiguous articles. Research reveals a straightforward integration path: the infrastructure already exists (Azure OpenAI structured outputs, 902 insurers with name/search_terms fields, Factiva collection pipeline), and we're replacing the existing per-insurer scraping loop with a batch-then-match flow.

**Key architectural insight:** BrasilIntel currently collects news per-insurer using 6 Apify/RSS sources. Phase 11 flips this: Factiva batch-collects all Brazilian insurance news (industry codes + keywords), then matches articles to insurers post-hoc. This is fundamentally different from the existing flow and requires careful pipeline refactoring.

**Critical finding:** The existing NewsItem model has `insurer_id` as a required NOT NULL foreign key, but the new flow collects articles BEFORE knowing which insurer they belong to. We must either:
1. Allow NULL insurer_id temporarily during collection, then populate via matching
2. Use a staging table for unmatched articles
3. Perform matching before database insert

**Recommendation:** Option 3 (match before insert) is cleanest — maintains data integrity, no schema migration, matches current transaction boundaries.

## Key Findings

**Stack:** Python 3.11 + FastAPI + SQLAlchemy + Azure OpenAI + sentence-transformers (already integrated)
**Architecture:** Hybrid deterministic + AI matching → insurer_id assignment → pipeline switchover to Factiva-only
**Critical design decision:** Match articles BEFORE NewsItem insert to preserve existing NOT NULL insurer_id constraint

## Technology Stack

### Core Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | Current | Web framework | Already in use, matches MDInsights |
| SQLAlchemy | Current | ORM | Already configured, supports migrations |
| Azure OpenAI | API v2023-05-15 | AI disambiguation | Already integrated for classification |
| sentence-transformers | 2.2.2+ | Semantic dedup | Already in Phase 10 for deduplication |

### Matching Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| unicodedata | stdlib | Accent normalization | Portuguese text (insurers have accents) |
| re | stdlib | Word boundary matching | Avoid substring false positives |
| difflib | stdlib | Fuzzy matching (optional) | If exact matching too strict |

### Already Installed
- `openai` — Azure OpenAI client with structured outputs support
- `tenacity` — Retry logic for API calls
- `structlog` — Structured logging
- `httpx` — HTTP client (Factiva collector)

### No New Dependencies Required
All matching logic can be implemented with stdlib + existing Azure OpenAI integration.

## Feature Landscape

### Table Stakes (Must Have)
| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Deterministic name matching | Performance + cost (avoid AI for obvious matches) | Low | Simple string normalization + search |
| AI disambiguation | Handles ambiguous/multi-insurer articles | Medium | Structured output already proven in classifier |
| Handle unmatched articles | Not all articles are insurer-specific | Low | Store as "unmatched" category |
| Portuguese text normalization | Brazilian company names have accents | Low | `unicodedata.normalize('NFKD', text)` |
| Multi-insurer support | Single article can mention multiple companies | Medium | Check schema — may need many-to-many |

### Differentiators (Nice to Have)
| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Confidence scoring | Track match quality for audit | Low | Return confidence with each match |
| Fuzzy matching fallback | Catch typos/variants | Medium | Use difflib.SequenceMatcher |
| Match caching | Avoid re-matching identical titles | Low | In-memory cache for batch |
| Match analytics | Dashboard showing match rate stats | Medium | Add fields to Run model |

### Anti-Features (Explicitly Avoid)
| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Per-insurer Factiva queries | Too slow (902 queries), wastes API calls | Batch query with industry codes, match post-hoc |
| Embeddings for matching | Overkill — names are exact strings | Use simple string matching, save embeddings for dedup |
| Custom NER models | Over-engineering, Azure OpenAI sufficient | Structured output with insurer context |
| Blocking on AI failures | AI should be enhancement, not dependency | Fall back to "unmatched" category |

## Architecture Patterns

### Recommended Architecture

```
Pipeline Flow (NEW - Phase 11):

1. FactivaCollector.collect(query_params)
   → Returns List[Dict] of normalized articles
   → Uses industry codes (i82*) + keywords (seguro, seguradora, etc.)
   → No insurer_id yet

2. ArticleDeduplicator.deduplicate(articles)
   → URL dedup + semantic dedup
   → Returns List[Dict] (same schema as input)

3. InsurerMatcher.match_batch(articles, insurers)  ← NEW SERVICE
   → For each article:
     a. Try deterministic match (name/search_terms in title/description)
     b. If ambiguous or no match, try AI disambiguation
     c. Return List[MatchResult(article_idx, insurer_ids, confidence, method)]

4. For each article + match result:
   → Create NewsItem with insurer_id (or NULL if unmatched — requires migration)
   → Commit to database

5. ClassificationService.classify_single_news(...)
   → Existing Phase 4 logic, no changes needed
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| FactivaCollector | Fetch + normalize articles from Factiva API | FactivaConfig (query params), ApiEvent (logging) |
| ArticleDeduplicator | Remove duplicate articles (URL + semantic) | None (pure function) |
| InsurerMatcher | Assign articles to insurers (deterministic + AI) | Insurer (ORM), Azure OpenAI, ClassificationService patterns |
| Pipeline (runs.py) | Orchestrate collection → dedup → match → store → classify | All of the above |

### Data Flow

```
FactivaConfig (DB)
  ↓
  query_params (industry_codes, keywords, page_size)
  ↓
FactivaCollector.collect() → List[article_dict]
  ↓
ArticleDeduplicator.deduplicate() → List[article_dict] (fewer)
  ↓
InsurerMatcher.match_batch() → List[MatchResult]
  ↓
  For each (article, match):
    ├─ Create NewsItem(insurer_id=match.insurer_id or NULL)
    ├─ db.add(news_item)
    └─ db.commit()
  ↓
ClassificationService.classify_single_news() → NewsClassification
  ↓
Update NewsItem with classification fields
```

## Patterns to Follow

### Pattern 1: Deterministic Matching Strategy

**What:** Fast string-based matching for obvious cases

**When:** Article clearly mentions insurer name or search_term

**Example:**
```python
import unicodedata
import re

def normalize_text(text: str) -> str:
    """Remove accents, lowercase, strip whitespace."""
    # NFKD = decompose accents, filter out combining marks
    nfkd = unicodedata.normalize('NFKD', text)
    ascii_text = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    return ascii_text.lower().strip()

def deterministic_match(article: dict, insurers: list[Insurer]) -> list[int]:
    """
    Match article to insurers by exact name/search_term presence.

    Returns list of insurer IDs (may be empty or multiple).
    """
    title = normalize_text(article.get('title', ''))
    description = normalize_text(article.get('description', ''))
    content = f"{title} {description}"

    matched_ids = []

    for insurer in insurers:
        # Normalize insurer name and search_terms
        name_norm = normalize_text(insurer.name)

        # Check name presence (whole word boundary to avoid substring matches)
        if re.search(rf'\b{re.escape(name_norm)}\b', content):
            matched_ids.append(insurer.id)
            continue

        # Check search_terms (comma-separated)
        if insurer.search_terms:
            for term in insurer.search_terms.split(','):
                term_norm = normalize_text(term.strip())
                if term_norm and re.search(rf'\b{re.escape(term_norm)}\b', content):
                    matched_ids.append(insurer.id)
                    break  # One match per insurer is enough

    return matched_ids
```

### Pattern 2: AI-Assisted Disambiguation

**What:** Azure OpenAI structured output for ambiguous articles

**When:** Deterministic matching returns 0 or >3 results (ambiguous)

**Example:**
```python
from pydantic import BaseModel, Field
from openai import AzureOpenAI

class InsurerMatchResult(BaseModel):
    """Structured output for AI insurer matching."""
    insurer_ids: list[int] = Field(
        description="List of insurer IDs mentioned in the article (may be empty)",
        default_factory=list
    )
    confidence: float = Field(
        description="Confidence score 0-1 for this match",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(
        description="Brief explanation of why these insurers were selected"
    )

def ai_match(article: dict, insurers: list[Insurer], client: AzureOpenAI) -> InsurerMatchResult:
    """
    Use Azure OpenAI to identify which insurers are mentioned in the article.

    Provides insurer context (id, name, search_terms) to the model.
    """
    # Build insurer reference list for the model
    insurer_context = "\n".join([
        f"ID {ins.id}: {ins.name} (search terms: {ins.search_terms or 'none'})"
        for ins in insurers[:100]  # Limit context size, prioritize top insurers
    ])

    system_prompt = f"""You are an AI assistant helping to match Brazilian insurance news articles to specific insurance companies.

Available insurers:
{insurer_context}

Analyze the article and identify which insurer(s) are mentioned. Return their IDs from the list above.
If no insurers are clearly mentioned, return an empty list.
If multiple insurers are mentioned, return all relevant IDs."""

    user_prompt = f"""Article title: {article['title']}

Article description: {article.get('description', 'No description available')}

Which insurer(s) are mentioned in this article?"""

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",  # Or configured deployment name
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=InsurerMatchResult,
        temperature=0,  # Deterministic
    )

    return completion.choices[0].message.parsed
```

### Pattern 3: Hybrid Matching Service

**What:** Combine deterministic + AI matching with fallback logic

**When:** All article matching in Phase 11

**Example:**
```python
class InsurerMatcher:
    """
    Hybrid insurer matching service.

    Tries deterministic matching first, falls back to AI for ambiguous cases.
    """

    def __init__(self):
        self.client = self._init_openai_client()
        self.logger = structlog.get_logger(__name__)

    def match_article(
        self,
        article: dict,
        insurers: list[Insurer],
        use_ai: bool = True
    ) -> MatchResult:
        """
        Match a single article to insurers.

        Returns MatchResult with insurer_ids, confidence, and method used.
        """
        # Try deterministic first
        det_matches = self._deterministic_match(article, insurers)

        # Clear single match → high confidence
        if len(det_matches) == 1:
            return MatchResult(
                insurer_ids=det_matches,
                confidence=0.95,
                method="deterministic_single",
                reasoning="Exact name match found"
            )

        # Clear multiple matches → medium confidence
        if 2 <= len(det_matches) <= 3:
            return MatchResult(
                insurer_ids=det_matches,
                confidence=0.85,
                method="deterministic_multi",
                reasoning=f"Found {len(det_matches)} exact matches"
            )

        # Ambiguous (0 or >3 matches) → try AI if enabled
        if use_ai and self.client:
            try:
                ai_result = self._ai_match(article, insurers)
                return MatchResult(
                    insurer_ids=ai_result.insurer_ids,
                    confidence=ai_result.confidence,
                    method="ai_disambiguation",
                    reasoning=ai_result.reasoning
                )
            except Exception as e:
                self.logger.warning("ai_match_failed", error=str(e))

        # No match or AI disabled
        return MatchResult(
            insurer_ids=[],
            confidence=0.0,
            method="unmatched",
            reasoning="No clear match found"
        )

    def match_batch(
        self,
        articles: list[dict],
        insurers: list[Insurer]
    ) -> list[MatchResult]:
        """Match multiple articles efficiently."""
        return [self.match_article(a, insurers) for a in articles]
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Per-Insurer Factiva Queries
**What:** Making 902 separate Factiva API calls, one per insurer
**Why bad:** Extremely slow (15+ minutes), wastes API quota, same content fetched multiple times
**Instead:** Single batch query with industry codes (i82*) + keywords, then match articles to insurers post-hoc

### Anti-Pattern 2: Modifying Articles In-Place During Matching
**What:** Adding `insurer_id` field to article dicts during matching
**Why bad:** Mutates data structure, makes testing harder, unclear ownership
**Instead:** Return separate MatchResult objects, keep articles immutable until NewsItem creation

### Anti-Pattern 3: Synchronous AI Calls in Loop
**What:** Calling Azure OpenAI for each article sequentially
**Why bad:** Slow for large batches (100+ articles), doesn't utilize async
**Instead:** Batch AI calls or use asyncio.gather() for parallel requests (future optimization)

### Anti-Pattern 4: Ignoring Match Confidence
**What:** Treating all matches as equally valid
**Why bad:** Can't audit low-quality matches, no visibility into ambiguous cases
**Instead:** Store confidence scores, add admin dashboard section for low-confidence matches

## Scalability Considerations

| Concern | At 100 articles | At 500 articles | At 1000+ articles |
|---------|-----------------|-----------------|-------------------|
| Deterministic matching | <1s (simple string ops) | <5s (still fast) | <10s (O(n*m) but fast) |
| AI disambiguation | ~30s (GPT-4o-mini fast) | ~2min (batch or parallel) | ~5min (need async batching) |
| Database inserts | <1s (bulk insert) | <3s (transaction) | <10s (batch commits) |
| Memory usage | ~10MB (article dicts) | ~50MB (manageable) | ~100MB (still fine) |

**Optimization path:** Start with sequential AI calls (simple), add async batching in Phase 12+ if needed.

## Domain-Specific Considerations

### Brazilian Portuguese Text Handling
- **Accent normalization required:** Many insurer names have accents (SulAmérica, Bradesco Saúde)
- **Case insensitivity:** "AMIL" vs "Amil" should match
- **Whitespace variations:** "Sul America" vs "SulAmerica"
- **Use `unicodedata.normalize('NFKD')` to decompose accents before matching**

### ANS Codes
- **6-digit codes:** All insurers have unique ANS codes (e.g., "419011")
- **NOT commonly used in news:** Articles rarely mention ANS codes
- **Don't use for matching:** Focus on names and search_terms instead
- **Useful for deduplication:** Can help verify insurer identity if mentioned

### Search Terms Field
- **Format:** Comma-separated string in Insurer.search_terms column
- **Current data:** Only 1 insurer has search_terms populated ("test company, health insurance")
- **Phase 11 opportunity:** Admin can add search_terms for high-profile insurers (e.g., "AMIL" → "Amil, United Health Brazil")
- **Not required:** Matching works with just names, search_terms are bonus

### Multi-Insurer Articles
- **Common in Brazilian market:** Articles about M&A, regulatory actions often mention multiple insurers
- **Schema check required:** Does NewsItem support multiple insurer_ids or is it 1:1?
- **Current schema:** `insurer_id` is single ForeignKey (1:1) — **BLOCKER for multi-insurer**
- **Options:**
  1. Create multiple NewsItem rows (same article, different insurer_id) — simplest
  2. Add junction table NewsItemInsurer (many-to-many) — cleaner but requires migration
  3. Store as JSON array in new field — hacky, avoid

**Recommendation:** Option 1 (duplicate NewsItem rows) for Phase 11 MVP, consider Option 2 in future if reporting gets complex.

## Critical Findings

### Existing Schema Constraint
**NewsItem.insurer_id is NOT NULL** — articles MUST have an insurer assignment.

**Options:**
1. **Migration:** Allow NULL insurer_id, add "unmatched" category
2. **Staging table:** Collect to temp table, match, then insert to NewsItem
3. **Match before insert:** Perform matching before database insert (current recommendation)

**Chosen approach:** Match before insert (Option 3) — preserves data integrity, no migration needed.

### Pipeline Switchover Impact
**Current flow (Phase 8):**
```python
for insurer in insurers:
    articles = scraper.scrape_insurer(insurer, ...)  # 6 sources per insurer
    for article in articles:
        news_item = NewsItem(insurer_id=insurer.id, ...)
        db.add(news_item)
```

**New flow (Phase 11):**
```python
articles = factiva_collector.collect(query_params)  # Batch fetch
articles = deduplicator.deduplicate(articles)
matches = matcher.match_batch(articles, insurers)

for article, match in zip(articles, matches):
    for insurer_id in match.insurer_ids:  # May create multiple NewsItems
        news_item = NewsItem(
            insurer_id=insurer_id or UNMATCHED_ID,  # Need special handling
            ...
        )
        db.add(news_item)
```

**Breaking changes:**
- No longer iterate over insurers (iterate over articles instead)
- Need to handle unmatched articles (create special "General News" insurer?)
- Multi-insurer articles create duplicate NewsItem rows
- Classification step moves to after matching (not during collection)

### Apify Removal Strategy
**Phase 11 requirement:** "No Apify code path remaining in active collection flow"

**Current Apify usage:**
- `app/services/sources/google_news.py` — GoogleNewsSource (Apify actor)
- `app/services/sources/valor.py` — ValorSource (Apify crawler)
- `app/services/sources/cqcs.py` — CQCSSource (Apify crawler)
- `app/services/scraper.py` — ApifyScraperService (legacy wrapper)

**Phase 11 scope:**
- **Remove from pipeline:** Don't call ScraperService in runs.py — use FactivaCollector instead
- **Keep classes:** Leave source files in place (Phase 15 deletes them)
- **Update health check:** Remove scraper health check from /health endpoint

**Phase 15 cleanup (future):**
- Delete source files: google_news.py, valor.py, cqcs.py
- Delete ApifyScraperService class
- Remove apify-client dependency
- Remove Apify config from Settings

## Pitfalls & Mitigations

### Pitfall 1: Short/Ambiguous Insurer Names
**What:** Common words that are also insurer names (e.g., "Liberty", "Porto")
**Prevention:**
- Use whole-word boundary regex (`\b{name}\b`) to avoid substring matches
- Require minimum word length for deterministic matching (e.g., >3 chars)
- Add context check (must appear near "seguradora" or other insurance keywords)

### Pitfall 2: AI Cost Explosion
**What:** Calling GPT-4 for every article without deterministic matching first
**Prevention:**
- Always try deterministic matching before AI
- Use GPT-4o-mini (cheaper, faster) not GPT-4
- Cache AI results for identical titles (dedup should prevent this anyway)
- Monitor API costs via ApiEvent logging

### Pitfall 3: Unmatched Articles Crash Pipeline
**What:** NOT NULL constraint on insurer_id fails for unmatched articles
**Prevention:**
- Create special "Unmatched" insurer (id=0, name="Notícias Gerais") in seed script
- OR allow NULL insurer_id (requires migration)
- Log unmatched rate — if >30%, improve matching logic

### Pitfall 4: Portuguese Text Encoding Issues
**What:** Unicode errors when comparing accented names
**Prevention:**
- Always use `unicodedata.normalize('NFKD')` before comparison
- Store normalized search terms in database (preprocessed)
- Test with real Brazilian insurer names (e.g., "Bradesco Saúde", "SulAmérica")

### Pitfall 5: Multi-Insurer Article Duplication
**What:** Creating 5+ NewsItem rows for single article mentioning many insurers
**Prevention:**
- Cap multi-insurer matches at 3 (if >3, send to AI to pick top 3)
- Add unique constraint on (run_id, source_url, insurer_id) to prevent exact duplicates
- Log multi-insurer rate — if >20%, review matching strictness

## Research Gaps

### Questions Needing Phase-Specific Research
1. **Multi-insurer UI impact:** How do reports display the same article under multiple insurers? (Phase 5 report templates)
2. **Classification efficiency:** Should we classify once per article or once per (article, insurer) pair? (Phase 4 classifier)
3. **Match audit dashboard:** What admin UI is needed to review/override low-confidence matches? (Phase 8 admin)
4. **Performance at scale:** 1000 articles × 902 insurers = 902K comparisons — is this fast enough? (Need benchmarking)

### Open Questions
- Should we implement fuzzy matching (difflib) in Phase 11 or defer to Phase 12?
- What's the acceptable unmatched rate? (10%? 20%?)
- Do we need a manual review queue for low-confidence AI matches?

## Implementation Recommendations

### Phase 11-01: Deterministic Matcher
**Priority:** HIGH
**Complexity:** LOW
**Rationale:** Fast, free, handles 80% of cases

**Deliverables:**
- `app/services/insurer_matcher.py` with `deterministic_match()` function
- Text normalization utilities (accent removal, lowercase)
- Unit tests with real Brazilian insurer names
- Match confidence scoring

### Phase 11-02: AI-Assisted Matcher
**Priority:** HIGH
**Complexity:** MEDIUM
**Rationale:** Handles ambiguous cases, already have Azure OpenAI integration

**Deliverables:**
- Add `InsurerMatchResult` schema to `app/schemas/matching.py`
- Add `ai_match()` method to InsurerMatcher service
- Integrate with existing Azure OpenAI client from ClassificationService
- Add ApiEvent logging for AI match calls

### Phase 11-03: Pipeline Integration
**Priority:** HIGH
**Complexity:** MEDIUM
**Rationale:** Replaces existing Apify flow with Factiva + matching

**Deliverables:**
- Refactor `runs.py` to use FactivaCollector instead of ScraperService
- Wire InsurerMatcher between deduplication and NewsItem creation
- Handle unmatched articles (create "General News" insurer or allow NULL)
- Handle multi-insurer articles (duplicate NewsItem rows)
- Remove Apify health check from /api/runs/health/scraper
- Update Run model to track match stats (matched_count, unmatched_count, ai_count)

### Testing Strategy
1. **Unit tests:** Text normalization, deterministic matching logic
2. **Integration tests:** AI matching with mock Azure OpenAI responses
3. **End-to-end test:** Collect → dedup → match → store with test Factiva data
4. **Manual validation:** Run on production Factiva data, review match quality

### Success Metrics
- **Match rate:** ≥85% of articles matched to at least one insurer
- **AI usage:** ≤20% of articles require AI disambiguation (deterministic covers 80%)
- **Multi-insurer rate:** ≤10% of articles matched to >1 insurer
- **Performance:** Full pipeline (collect → match → store) completes in <5 minutes for 100 articles

## Sources

**Codebase analysis (HIGH confidence):**
- `C:\BrasilIntel\app\models\insurer.py` — Insurer ORM model with search_terms field
- `C:\BrasilIntel\app\models\news_item.py` — NewsItem ORM with insurer_id FK constraint
- `C:\BrasilIntel\app\collectors\factiva.py` — FactivaCollector implementation (Phase 10)
- `C:\BrasilIntel\app\services\deduplicator.py` — ArticleDeduplicator with sentence-transformers (Phase 10)
- `C:\BrasilIntel\app\services\classifier.py` — Azure OpenAI structured output pattern
- `C:\BrasilIntel\app\schemas\classification.py` — Pydantic structured output models
- `C:\BrasilIntel\app\routers\runs.py` — Existing pipeline orchestration

**Database inspection (HIGH confidence):**
- 902 insurers in database
- Only 1 has search_terms populated (test data)
- NewsItem.insurer_id is NOT NULL FK to insurers

**Phase context (HIGH confidence):**
- Phase 10 completion: Factiva collection + deduplication working
- Phase 11 context: Decision to match articles post-collection, not per-insurer queries
- v1.1 goal: Replace all Apify sources with Factiva as sole news source

**Portuguese language considerations (MEDIUM confidence):**
- Based on existing Brazilian insurance domain knowledge
- Accent normalization is standard practice for Portuguese text processing
- Validated against existing insurer names in database
