# Phase 4: AI Classification Pipeline - Research

**Researched:** 2026-02-04
**Domain:** Azure OpenAI classification, sentiment analysis, news content analysis
**Confidence:** HIGH (existing implementation verified, extending proven patterns)

## Summary

This research investigates how to complete the Azure OpenAI classification pipeline for Phase 4, specifically adding news content analysis categories (financial crisis, regulatory action, M&A, leadership changes) and ensuring proper storage and toggle functionality. The good news is that **most of the infrastructure is already in place** from Phase 2 (02-04). The existing `ClassificationService` uses Azure OpenAI's structured outputs with Pydantic response_format, Portuguese prompts, temperature=0, and proper fallback handling.

Phase 4's requirements focus on **enhancing what exists** rather than building new infrastructure:
1. **CLASS-02**: The classification criteria are already in the system prompts (financial crisis, regulatory action, M&A, leadership changes) - they just need verification and potential refinement
2. **CLASS-04**: Sentiment analysis already exists in `NewsClassification.sentiment` - it's populated during classification
3. **CLASS-05**: Classification results already stored in `NewsItem` model (status, sentiment, summary fields)
4. **CLASS-06**: `use_llm_summary` flag exists in config.py and is respected by `ClassificationService`

The main work involves: verifying the existing implementation meets requirements, adding any missing category indicators to the classification output, and ensuring the end-to-end flow works correctly.

**Primary recommendation:** Validate existing implementation against requirements, enhance the classification Pydantic schema to include explicit category indicators (financial_crisis, regulatory_action, m_and_a, leadership_change), and add integration tests to verify the complete pipeline.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | 1.42+ | Azure OpenAI Python SDK | Native Pydantic structured output support via `beta.chat.completions.parse()` |
| pydantic | 2.8+ | Response schema validation | Integrated with OpenAI SDK for structured outputs |
| azure-identity | (optional) | Entra ID auth | Alternative to API key authentication |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | 8.x | Retry logic | When API calls need more sophisticated retry than built-in |

### Already Installed
The project already has these dependencies installed from Phase 2:
- `openai` for Azure OpenAI integration
- `pydantic` for schema validation
- `pydantic-settings` for configuration

**No additional installation required.**

## Architecture Patterns

### Existing Project Structure (Phase 2)
```
app/
├── config.py              # use_llm_summary flag already exists
├── services/
│   ├── classifier.py      # ClassificationService exists with full implementation
│   └── relevance_scorer.py # Two-pass AI filtering implemented
├── schemas/
│   ├── classification.py  # NewsClassification, InsurerClassification exist
│   └── news.py            # InsurerStatus, Sentiment enums exist
└── models/
    └── news_item.py       # status, sentiment, summary fields exist
```

### Pattern 1: Azure OpenAI Structured Outputs with Pydantic
**What:** Pass Pydantic model to `response_format` parameter for guaranteed schema conformance
**When to use:** Any LLM classification requiring structured JSON output
**Already Implemented:**
```python
# Source: app/services/classifier.py (existing)
completion = self.client.beta.chat.completions.parse(
    model=self.model,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT_SINGLE},
        {"role": "user", "content": user_prompt},
    ],
    response_format=NewsClassification,  # Pydantic model
    temperature=0,  # Deterministic outputs
)
return completion.choices[0].message.parsed
```

### Pattern 2: Category-Based Classification via Prompts
**What:** Define classification criteria in system prompt, return structured result
**When to use:** Multi-category classification (Critical/Watch/Monitor/Stable)
**Already Implemented:**
```python
# Source: app/services/classifier.py (existing prompt)
SYSTEM_PROMPT_SINGLE = """Você é um analista financeiro especializado em seguradoras brasileiras.
Analise a notícia fornecida e classifique o status da seguradora.

Critérios de classificação:
- CRITICAL: Crise financeira, intervenção da ANS, risco de falência, fraude, acusações criminais
- WATCH: Atividade de M&A, mudanças significativas na liderança, ações regulatórias, perdas significativas
- MONITOR: Mudanças de tarifa, alterações na rede, expansão de mercado, anúncios de parcerias
- STABLE: Sem notícias significativas ou apenas atualizações operacionais rotineiras
"""
```

### Pattern 3: Configuration Toggle for LLM Features
**What:** Environment variable controls whether LLM features are enabled
**When to use:** Allowing cost control and fallback behavior
**Already Implemented:**
```python
# Source: app/config.py (existing)
use_llm_summary: bool = True

# Source: app/services/classifier.py (existing)
self.use_llm = settings.use_llm_summary
if not self.client or not self.use_llm:
    return self._fallback_classification()
```

### Pattern 4: Graceful Fallback Classification
**What:** Return safe default when LLM unavailable or disabled
**When to use:** Ensuring pipeline doesn't fail when AI unavailable
**Already Implemented:**
```python
# Source: app/services/classifier.py (existing)
def _fallback_classification(self) -> NewsClassification:
    return NewsClassification(
        status="Monitor",
        summary_bullets=["Classificação automática indisponível"],
        sentiment="neutral",
        reasoning="Classificação de fallback - LLM não configurado ou desabilitado",
    )
```

### Anti-Patterns to Avoid
- **Duplicate prompts**: Don't create new prompts when existing ones already cover the criteria
- **Separate sentiment analysis call**: Sentiment is already returned in single classification call
- **Manual JSON parsing**: Use Pydantic structured outputs, not json.loads()
- **Ignoring existing toggle**: The `use_llm_summary` flag exists; don't create a duplicate

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Status classification | New classifier | Existing ClassificationService | Already implements Azure OpenAI structured outputs |
| Sentiment analysis | Separate Azure AI Language call | NewsClassification.sentiment | Combined in single LLM call |
| LLM toggle | New config flag | settings.use_llm_summary | Already exists and is wired up |
| Category storage | New fields | NewsItem.status | Already stores classification result |
| Fallback behavior | New error handling | _fallback_classification() | Already implemented |

**Key insight:** Phase 4 requirements are largely **already implemented** in Phase 2. The work is verification and potential enhancement, not new construction.

## Common Pitfalls

### Pitfall 1: Duplicating Existing Functionality
**What goes wrong:** Creating new classification logic when it already exists
**Why it happens:** Not fully reviewing existing codebase before planning
**How to avoid:** Check classifier.py, classification.py schemas before writing new code
**Warning signs:** Creating files that duplicate existing service names

### Pitfall 2: Separate Sentiment Analysis
**What goes wrong:** Making additional API calls for sentiment when it's already returned
**Why it happens:** Treating sentiment as separate from classification
**How to avoid:** The `NewsClassification` schema already includes `sentiment` field
**Warning signs:** Multiple API calls per news item, doubled token costs

### Pitfall 3: Missing Category Indicators in Output
**What goes wrong:** Classification result shows status but not which criteria triggered it
**Why it happens:** Original schema focused on status, not category indicators
**How to avoid:** Consider adding explicit boolean fields for category indicators
**Warning signs:** Reports can't show "why" an insurer is Watch/Critical

### Pitfall 4: Not Validating Existing Toggle Works
**What goes wrong:** Assuming USE_LLM_SUMMARY works without testing
**Why it happens:** Config exists but end-to-end path not verified
**How to avoid:** Integration test that sets use_llm_summary=False and verifies fallback
**Warning signs:** No test coverage for disabled state

### Pitfall 5: Inconsistent Portuguese Output
**What goes wrong:** LLM returns mixed English/Portuguese
**Why it happens:** User prompt language influences output language
**How to avoid:** System prompt already says "Responda em português brasileiro"
**Warning signs:** English words appearing in summaries

### Pitfall 6: Overwriting Existing Classification
**What goes wrong:** Re-classifying already-classified items on retry
**Why it happens:** No check for existing classification before calling LLM
**How to avoid:** Check `item.status` before classification; already done in runs.py
**Warning signs:** Unnecessary API costs, duplicate processing

## Code Examples

Verified patterns from existing codebase:

### Existing Classification Schema (app/schemas/classification.py)
```python
# Source: app/schemas/classification.py (already exists)
class NewsClassification(BaseModel):
    status: Literal["Critical", "Watch", "Monitor", "Stable"] = Field(
        description="Insurer status based on news content impact"
    )
    summary_bullets: list[str] = Field(
        description="3-5 bullet points summarizing the news impact in Portuguese",
        min_length=1,
        max_length=5,
    )
    sentiment: Literal["positive", "negative", "neutral"] = Field(
        description="Overall sentiment of the news"
    )
    reasoning: str = Field(
        description="Brief explanation (1-2 sentences) of why this status was assigned"
    )
```

### Enhanced Schema with Category Indicators (Potential Enhancement)
```python
# Potential enhancement to classification.py
class NewsClassification(BaseModel):
    status: Literal["Critical", "Watch", "Monitor", "Stable"] = Field(
        description="Insurer status based on news content impact"
    )
    summary_bullets: list[str] = Field(
        description="3-5 bullet points summarizing the news impact in Portuguese",
        min_length=1,
        max_length=5,
    )
    sentiment: Literal["positive", "negative", "neutral"] = Field(
        description="Overall sentiment of the news"
    )
    reasoning: str = Field(
        description="Brief explanation (1-2 sentences) of why this status was assigned"
    )
    # NEW: Explicit category indicators per CLASS-02
    category_indicators: list[Literal[
        "financial_crisis",
        "regulatory_action",
        "m_and_a",
        "leadership_change",
        "rate_change",
        "network_change",
        "market_expansion",
        "partnership",
        "routine_operations",
    ]] = Field(
        default_factory=list,
        description="Categories detected in the news content"
    )
```

### Existing Classification Call Pattern (app/services/classifier.py)
```python
# Source: app/services/classifier.py (already exists)
def classify_single_news(
    self,
    insurer_name: str,
    news_title: str,
    news_description: str | None = None,
) -> NewsClassification | None:
    if not self.client or not self.use_llm:
        logger.info("LLM classification disabled or not configured")
        return self._fallback_classification()

    content = f"Título: {news_title}"
    if news_description:
        content += f"\n\nDescrição: {news_description}"

    try:
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_SINGLE},
                {"role": "user", "content": user_prompt},
            ],
            response_format=NewsClassification,
            temperature=0,
        )
        return completion.choices[0].message.parsed
    except Exception as e:
        logger.error(f"Classification failed for {insurer_name}: {e}")
        return self._fallback_classification()
```

### Existing Storage Pattern (app/routers/runs.py)
```python
# Source: app/routers/runs.py (already exists)
classification = classifier.classify_single_news(
    insurer_name=insurer.name,
    news_title=scraped.title,
    news_description=scraped.description,
)

news_item = NewsItem(
    run_id=run.id,
    insurer_id=result.insurer_id,
    title=scraped.title,
    description=scraped.description,
    source_url=scraped.url,
    source_name=scraped.source,
    published_at=scraped.published_at,
    # Classification results stored here
    status=classification.status if classification else None,
    sentiment=classification.sentiment if classification else None,
    summary="\n".join(classification.summary_bullets) if classification else None,
)
```

### Configuration Toggle (app/config.py)
```python
# Source: app/config.py (already exists)
class Settings(BaseSettings):
    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-08-01-preview"
    use_llm_summary: bool = True  # CLASS-06 toggle

    def is_azure_openai_configured(self) -> bool:
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_api_key
            and self.azure_openai_deployment
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JSON mode + manual parsing | Pydantic structured outputs | OpenAI 1.40+ (2024-08) | Guaranteed schema conformance |
| Separate sentiment API | Combined classification | Best practice | Single API call, lower cost |
| Try/except JSON parsing | response_format=Model | 2024-08-01-preview | Type-safe parsed response |

**API Version Requirements:**
- Azure OpenAI structured outputs require API version `2024-08-01-preview` or later
- The project already uses `2024-08-01-preview` in config.py

**Deprecated/outdated:**
- `response_format={"type": "json_object"}`: Use Pydantic models instead
- Manual JSON parsing with `json.loads()`: Use `.parsed` attribute from structured output

## Requirements Mapping

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| CLASS-02: Classification based on news content (financial crisis, regulatory action, M&A, leadership changes) | IMPLEMENTED | SYSTEM_PROMPT_SINGLE contains all criteria |
| CLASS-04: Sentiment (positive/negative/neutral) | IMPLEMENTED | NewsClassification.sentiment field |
| CLASS-05: Results stored with insurer records | IMPLEMENTED | NewsItem.status, sentiment, summary fields |
| CLASS-06: Toggle via USE_LLM_SUMMARY | IMPLEMENTED | settings.use_llm_summary, checked in classify_single_news() |

## Gap Analysis

Based on requirements review, here are the gaps:

### Gap 1: No Explicit Category Indicators
**Current:** Classification returns status but not which specific categories triggered it
**Required:** Per CLASS-02, classification should be "based on financial crisis, regulatory action, M&A, leadership changes"
**Recommendation:** Add `category_indicators` field to NewsClassification schema
**Impact:** LOW - enhancement, not blocker

### Gap 2: Category Indicators Not in Database
**Current:** NewsItem stores status, sentiment, summary only
**Required:** If adding category indicators, need to store them
**Recommendation:** Add `category_indicators` column to NewsItem model (JSON or comma-separated)
**Impact:** LOW - optional enhancement

### Gap 3: Integration Test Coverage
**Current:** No comprehensive test of classification pipeline
**Required:** Verify end-to-end flow works as expected
**Recommendation:** Add integration tests that verify classification, storage, and report access
**Impact:** MEDIUM - needed for validation

## Open Questions

Things that couldn't be fully resolved:

1. **Category Indicators Granularity**
   - What we know: Requirements mention categories but don't specify exact output format
   - What's unclear: Should categories be stored separately or just influence status?
   - Recommendation: Add to schema for better reporting; store as JSON field

2. **Sentiment in Reports**
   - What we know: Template already displays sentiment badges
   - What's unclear: Is current display sufficient for requirements?
   - Recommendation: Verify with template review; appears complete

3. **Aggregate Classification Storage**
   - What we know: `classify_insurer_news()` exists for aggregate classification
   - What's unclear: Where/when is aggregate result stored?
   - Recommendation: Review if aggregate classification needs storage (may be report-time only)

## Sources

### Primary (HIGH confidence)
- [Microsoft Learn - Azure OpenAI Structured Outputs](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/structured-outputs) - API patterns, Pydantic integration
- Existing codebase: `app/services/classifier.py`, `app/schemas/classification.py` - Implementation patterns

### Secondary (MEDIUM confidence)
- [OpenAI Platform - Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs) - General patterns (Azure mirrors)

### Tertiary (LOW confidence)
- WebSearch results on prompt engineering for financial classification - General best practices

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Already implemented, using established patterns
- Architecture: HIGH - Existing code provides clear patterns to follow
- Gaps: MEDIUM - Gap analysis based on requirements interpretation
- Pitfalls: HIGH - Based on actual codebase review

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (30 days - Azure OpenAI API stable, existing implementation verified)

## Planner Guidance

**Primary focus:** Verification and integration testing, not new implementation

**Tasks should focus on:**
1. Validate existing classification meets CLASS-02 criteria (may already be complete)
2. Verify sentiment analysis (CLASS-04) is working end-to-end
3. Verify storage (CLASS-05) is working end-to-end
4. Verify toggle (CLASS-06) works by testing with use_llm_summary=False
5. Optional: Add category_indicators field if explicit categorization is needed

**Tasks should NOT:**
- Recreate ClassificationService
- Add separate sentiment analysis
- Create new config flags
- Duplicate existing patterns

**Key files to verify/enhance:**
- `app/schemas/classification.py` - May need category_indicators field
- `app/services/classifier.py` - Verify prompt completeness
- `app/models/news_item.py` - May need category_indicators column
- `tests/` - Add integration tests
