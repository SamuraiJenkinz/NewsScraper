# Phase 4 Plan 1: Category Indicators Summary

**One-liner:** Added explicit category_indicators field to classification pipeline enabling "why" reporting (financial_crisis, m_and_a, regulatory_action, etc.)

---
phase: 04-ai-classification-pipeline
plan: 01
subsystem: classification
tags: [ai, classification, schema, database, reporting]

dependencies:
  requires: ["02-04-classification-service", "02-01-database-models"]
  provides: ["category_indicators_field", "classification_reasoning"]
  affects: ["05-01-report-enhancement"]

tech_stack:
  added: []
  patterns: ["pydantic-literal-types", "comma-separated-storage"]

key_files:
  created: []
  modified:
    - app/schemas/classification.py
    - app/models/news_item.py
    - app/routers/runs.py
    - app/services/classifier.py

decisions:
  - id: "category-indicators-literal"
    title: "Use Pydantic Literal type for category indicators"
    rationale: "Ensures type safety and validation at schema level"
    alternatives: ["plain strings", "enum"]
    chosen: "Literal type with 10 predefined categories"

  - id: "comma-separated-storage"
    title: "Store category_indicators as comma-separated string"
    rationale: "SQLite doesn't have native array type, simplest approach for MVP"
    alternatives: ["JSON column", "separate table"]
    chosen: "Comma-separated string in nullable column"

  - id: "portuguese-category-descriptions"
    title: "Provide Portuguese descriptions for each category in prompt"
    rationale: "LLM needs clear guidance in Brazilian Portuguese context"
    alternatives: ["English descriptions", "minimal guidance"]
    chosen: "Detailed Portuguese descriptions for each category"

metrics:
  duration: "2 minutes"
  completed: "2026-02-04"
---

## Objective

Enhance the classification pipeline with explicit category indicators per CLASS-02. The existing classification returns status (Critical/Watch/Monitor/Stable) but doesn't expose WHICH criteria triggered it. Adding category_indicators field enables reports to show "why" an insurer is flagged (e.g., "M&A activity detected", "Regulatory action").

## What Was Delivered

### 1. Enhanced NewsClassification Schema
- Added `CategoryIndicator` Literal type with 10 valid categories:
  - financial_crisis (crise financeira, risco de falência)
  - regulatory_action (intervenção ANS, ações regulatórias)
  - m_and_a (fusões e aquisições)
  - leadership_change (mudanças de liderança)
  - fraud_criminal (fraude, acusações criminais)
  - rate_change (mudanças de tarifa)
  - network_change (alterações na rede)
  - market_expansion (expansão de mercado)
  - partnership (parcerias)
  - routine_operations (operações rotineiras)
- Added `category_indicators: list[CategoryIndicator]` field to NewsClassification
- Field includes default_factory=list for optional indicators

### 2. Database Storage
- Added `category_indicators` column to NewsItem model (String(500), nullable)
- Updated single insurer mode to store comma-separated category_indicators
- Updated category mode to store comma-separated category_indicators
- Both execution paths now persist classification reasoning

### 3. Enhanced Classification Prompt
- Updated SYSTEM_PROMPT_SINGLE with category indicator descriptions in Portuguese
- Each category includes clear Portuguese explanation for LLM guidance
- Updated fallback classification to return category_indicators=["routine_operations"]
- Ensures consistent schema even when LLM unavailable

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Add category_indicators to NewsClassification schema | 7de8b46 | app/schemas/classification.py |
| 2 | Add category_indicators storage to NewsItem model | 3d63d9c | app/models/news_item.py, app/routers/runs.py |
| 3 | Update classifier prompt to request category indicators | 8c68563 | app/services/classifier.py |

## Technical Implementation

### Schema Changes
```python
# New Literal type for validation
CategoryIndicator = Literal[
    "financial_crisis",
    "regulatory_action",
    "m_and_a",
    "leadership_change",
    "fraud_criminal",
    "rate_change",
    "network_change",
    "market_expansion",
    "partnership",
    "routine_operations"
]

# Added to NewsClassification
category_indicators: list[CategoryIndicator] = Field(
    default_factory=list,
    description="Categories detected in the news content that influenced the status"
)
```

### Storage Pattern
```python
# Comma-separated storage for SQLite compatibility
category_indicators=",".join(classification.category_indicators)
    if classification and classification.category_indicators
    else None
```

### Prompt Enhancement
Added detailed Portuguese descriptions for each category to guide the LLM in identifying appropriate indicators based on news content.

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

All verification checks passed:
1. ✅ Schema validation successful
2. ✅ NewsItem model includes category_indicators column
3. ✅ Prompt includes Portuguese category descriptions
4. ✅ Fallback classification returns category_indicators=["routine_operations"]

## Success Criteria Met

- ✅ NewsClassification has category_indicators: list[CategoryIndicator] field
- ✅ CategoryIndicator is a Literal type with 10 valid values
- ✅ NewsItem model has category_indicators column (String, nullable)
- ✅ runs.py stores classification.category_indicators as comma-separated string in both locations
- ✅ SYSTEM_PROMPT_SINGLE includes category indicator descriptions in Portuguese
- ✅ Fallback classification returns category_indicators=["routine_operations"]

## Next Phase Readiness

**Phase 5 (Report Enhancement) is ready to proceed:**
- category_indicators field available in NewsItem records
- Data persisted as comma-separated strings for easy parsing
- Fallback ensures field always present (never None if classification exists)

**Recommendations for Phase 5:**
- Parse comma-separated category_indicators in report generator
- Display categories as badges/tags in HTML report
- Group news items by category for better organization
- Consider category-based filtering in report UI

## Known Issues & Limitations

**Database Migration:**
- Existing news_items records will have NULL category_indicators
- New classifications will populate field going forward
- Consider running re-classification job for historical data if needed

**Storage Format:**
- Comma-separated string requires parsing to reconstruct list
- Future enhancement: migrate to JSON column for native array support
- Current approach sufficient for MVP reporting needs

**Category Detection Accuracy:**
- Depends on Azure OpenAI's Portuguese language understanding
- May require prompt refinement based on production results
- Monitor classification quality in Phase 5 testing

## Files Modified

### app/schemas/classification.py
- Added CategoryIndicator Literal type
- Added category_indicators field to NewsClassification

### app/models/news_item.py
- Added category_indicators column (String(500), nullable)

### app/routers/runs.py
- Updated single insurer mode to store category_indicators
- Updated category mode to store category_indicators

### app/services/classifier.py
- Enhanced SYSTEM_PROMPT_SINGLE with category descriptions
- Updated _fallback_classification to include routine_operations category

## Lessons Learned

**Pydantic Literal Types:**
- Provides strong type safety for constrained values
- Better than plain strings for API schema validation
- Generates clear OpenAPI documentation

**Comma-Separated Storage:**
- Simple and effective for small lists in SQLite
- Easy to query with LIKE operators if needed
- Sufficient for MVP, can migrate to JSON later

**Portuguese Prompt Engineering:**
- LLM needs explicit category descriptions in target language
- Clear examples improve classification consistency
- Portuguese terms essential for Brazilian news context

---

*Completed: 2026-02-04*
*Duration: ~2 minutes*
*Wave: 1 of 2 in Phase 4*
