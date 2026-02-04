---
phase: 02-vertical-slice-validation
plan: 04
subsystem: ai-classification
tags: [azure-openai, pydantic, structured-outputs, classification, llm]
requires: [02-02-centralized-configuration]
provides:
  - Azure OpenAI classification service
  - Structured output Pydantic models
  - Portuguese summarization
  - Fallback classification handling
affects:
  - 02-05-api-endpoints (will expose classification through API)
  - 02-06-scraping-orchestration (will use for two-phase scrape→classify)
tech-stack:
  added: []
  patterns:
    - Pydantic structured outputs with Azure OpenAI
    - Fallback classification for LLM unavailability
    - Portuguese-language system prompts
    - temperature=0 for deterministic outputs
key-files:
  created:
    - app/schemas/classification.py
    - app/services/classifier.py
  modified:
    - app/services/__init__.py
decisions:
  - id: azure-openai-structured-outputs
    choice: Use Azure OpenAI beta.chat.completions.parse with response_format
    rationale: Guarantees JSON schema conformance without parsing errors
    alternatives: [JSON mode with manual parsing, Function calling]
    date: 2026-02-04
  - id: portuguese-system-prompts
    choice: System prompts in Portuguese with explicit "Responda em português" instruction
    rationale: Better output quality for Portuguese-language summarization
    alternatives: [English prompts with translation, Bilingual prompts]
    date: 2026-02-04
  - id: fallback-classification
    choice: Return Monitor status with Portuguese fallback message when LLM unavailable
    rationale: Graceful degradation - system continues functioning without AI
    alternatives: [Raise error, Skip classification, Queue for retry]
    date: 2026-02-04
  - id: temperature-zero
    choice: temperature=0 for all classification requests
    rationale: Deterministic outputs for consistent classification behavior
    alternatives: [temperature=0.3 for variety, temperature=0.7 for creativity]
    date: 2026-02-04
  - id: token-limit-protection
    choice: Limit aggregate classification to 10 most recent news items
    rationale: Prevents token limit errors while covering most important news
    alternatives: [Summarize all items, Chunk into batches, Use longer context model]
    date: 2026-02-04
duration: 2.1 minutes
completed: 2026-02-04
---

# Phase 2 Plan 04: Azure OpenAI Classification Service Summary

**One-liner:** Azure OpenAI structured output classification with Pydantic models for Portuguese insurer news analysis

## What Was Built

Created Azure OpenAI integration for AI-powered insurer status classification with guaranteed JSON schema conformance through Pydantic structured outputs.

**Classification Service:**
- `ClassificationService` with AzureOpenAI client initialization
- `classify_single_news()` - Classifies individual news items (Critical/Watch/Monitor/Stable)
- `classify_insurer_news()` - Aggregates multiple news for overall insurer status
- Portuguese system prompts for consistent Portuguese-language outputs
- Fallback classification when LLM unavailable or disabled
- `health_check()` method for service monitoring

**Pydantic Schemas:**
- `NewsClassification` - Single news item classification with status, summary_bullets, sentiment, reasoning
- `InsurerClassification` - Aggregated insurer status with overall_status, key_findings, risk_factors, sentiment_breakdown
- Literal types for status (Critical/Watch/Monitor/Stable) and sentiment (positive/negative/neutral)
- Field descriptions guide Azure OpenAI structured output generation

**Key Features:**
- **Structured Outputs:** Uses `response_format=NewsClassification` for guaranteed schema conformance
- **Portuguese Output:** System prompts explicitly request Portuguese for all text fields
- **Deterministic:** `temperature=0` ensures consistent classification behavior
- **Graceful Degradation:** Returns fallback classification when LLM unavailable
- **Token Protection:** Limits aggregate classification to 10 news items to prevent token limit errors

## Implementation Details

**Classification Criteria:**
- **CRITICAL:** Financial crisis, ANS intervention, bankruptcy risk, fraud, criminal charges
- **WATCH:** M&A activity, significant leadership changes, regulatory actions, significant losses
- **MONITOR:** Rate changes, network changes, market expansion, partnership announcements
- **STABLE:** No significant news or routine operational updates only

**Azure OpenAI Integration:**
- Uses `openai.AzureOpenAI` client from official SDK
- Beta API: `client.beta.chat.completions.parse()` for structured outputs
- Reads credentials from centralized `Settings` (02-02)
- Checks `is_azure_openai_configured()` before initialization
- Respects `use_llm_summary` config flag for enabling/disabling classification

**Error Handling:**
- Catches all exceptions during LLM calls
- Returns fallback classification on error
- Logs warnings when Azure OpenAI not configured
- Logs errors with insurer context for debugging

## Technical Changes

**New Files:**
1. **app/schemas/classification.py** (61 lines)
   - NewsClassification with 4 fields
   - InsurerClassification with 5 fields
   - Literal types for validation
   - Field descriptions for LLM guidance

2. **app/services/classifier.py** (212 lines)
   - ClassificationService class
   - Portuguese system prompts
   - classify_single_news method
   - classify_insurer_news method
   - Fallback classification methods
   - health_check method

**Modified Files:**
1. **app/services/__init__.py**
   - Added ClassificationService export
   - Fixed excel_service imports (parse_excel_insurers not parse_excel_upload)

## Testing & Validation

**Import Validation:**
- Schemas import correctly from app.schemas.classification
- Service imports correctly from app.services.classifier
- ClassificationService exported from app.services

**Fallback Behavior:**
- Returns Monitor status with Portuguese message when unconfigured
- service.classify_single_news() returns fallback when client=None
- service.classify_insurer_news() returns fallback when client=None

**Health Check:**
- Returns {"status": "error", "message": "Azure OpenAI not configured"} when unconfigured
- Returns {"status": "disabled", ...} when use_llm_summary=False
- Returns {"status": "ok", "model": ...} when configured and working

## Dependencies

**Requires (Completed Plans):**
- 02-02: Centralized configuration with Azure OpenAI settings
- Phase 1: Foundation with database and schemas infrastructure

**Enables (Future Plans):**
- 02-05: API endpoints for classification
- 02-06: Scraping orchestration with two-phase scrape→classify workflow
- Phase 5: Summary generation with LLM-powered insights

## Deviations from Plan

### Auto-Fixed Issues

**1. [Rule 3 - Blocking] Fixed incorrect excel_service import name**
- **Found during:** Task 3
- **Issue:** Plan specified `parse_excel_upload` but actual function is `parse_excel_insurers`
- **Fix:** Updated import to use correct function name
- **Files modified:** app/services/__init__.py
- **Commit:** 74e4442

## Integration Points

**Configuration Integration:**
- Reads from `app.config.get_settings()`
- Uses `azure_openai_endpoint`, `azure_openai_api_key`, `azure_openai_api_version`, `azure_openai_deployment`
- Checks `is_azure_openai_configured()` method
- Respects `use_llm_summary` flag

**Schema Integration:**
- Uses Pydantic BaseModel for structured outputs
- Literal types ensure valid status/sentiment values
- Field descriptions guide LLM output generation
- default_factory for optional/collection fields

**Service Pattern:**
- Follows existing service pattern (ApifyScraperService)
- Exported from services package
- health_check() method for monitoring
- Graceful degradation with fallbacks

## Next Phase Readiness

**Ready for 02-05 (API Endpoints):**
- ClassificationService available for dependency injection
- NewsClassification schema ready for API response models
- health_check() available for /health endpoint

**Ready for 02-06 (Orchestration):**
- classify_single_news() ready for per-item classification
- classify_insurer_news() ready for batch classification
- Fallback handling prevents orchestration failures

**Known Limitations:**
- No retry logic for transient Azure OpenAI errors
- Token limit protection only in aggregate (10 items max)
- No caching of classification results
- No streaming for long responses

**Future Enhancements (Out of Scope):**
- Retry with exponential backoff for transient errors
- Caching layer for classification results
- Batch processing for multiple insurers
- Streaming responses for real-time classification
- Classification confidence scores
- A/B testing for prompt variations

## Commits

| Commit | Message | Files |
|--------|---------|-------|
| a791693 | feat(02-04): add classification Pydantic schemas | app/schemas/classification.py |
| 57458f9 | feat(02-04): add ClassificationService with Azure OpenAI | app/services/classifier.py |
| 74e4442 | feat(02-04): export ClassificationService from services | app/services/__init__.py |

---

**Plan Status:** ✅ Complete
**Duration:** 2.1 minutes
**Tasks:** 3/3 complete
**Quality:** All verification checks passed
