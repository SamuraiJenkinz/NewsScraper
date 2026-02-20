---
phase: 11-insurer-matching-pipeline
verified: 2026-02-19T20:35:00Z
status: passed
score: 18/18 must-haves verified
---

# Phase 11: Insurer Matching Pipeline Verification Report

**Phase Goal:** Every Factiva article is matched to one or more of the 897 tracked insurers and Factiva is the sole active news collection path in the pipeline

**Verified:** 2026-02-19T20:35:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After a pipeline run, each article stored in the database has at least one insurer_id assignment drawn from the 897 tracked insurers | VERIFIED | lines 195-230 in runs.py: sentinel Noticias Gerais ANS 000000 ensures all articles get insurer_id assignment; target_ids defaults to general_insurer.id when match.insurer_ids is empty |
| 2 | Articles clearly mentioning a specific insurer by name or known search term are matched without AI involvement | VERIFIED | insurer_matcher.py lines 65-145: deterministic_match uses word-boundary regex on normalized name/search_terms; returns before AI for 1-3 matches |
| 3 | Ambiguous articles are sent to Azure OpenAI for insurer identification with structured match result | VERIFIED | insurer_matcher.py lines 189-210: 0 or >3 matches trigger ai_matcher.ai_match when ai_enabled=True; ai_matcher.py lines 129-254: structured output via client.beta.chat.completions.parse with InsurerMatchResponse Pydantic model |
| 4 | The pipeline collection step invokes Factiva with no Apify code path remaining in active flow | VERIFIED | runs.py lines 98, 563: both execute_run and execute_category_run call _execute_factiva_pipeline; lines 131-139: FactivaCollector.collect called; old ScraperService functions exist lines 278, 387 but not called in active flow |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| app/schemas/matching.py | MatchResult schema with 4 methods | VERIFIED | 42 lines, exports MatchResult + MatchMethod, all 4 method types present |
| app/services/insurer_matcher.py | InsurerMatcher with deterministic + AI fallback | VERIFIED | 265 lines, NFKD normalization, word-boundary regex, AI fallback on 0 or >3 matches |
| app/services/ai_matcher.py | AIInsurerMatcher with Azure OpenAI | VERIFIED | 322 lines, InsurerMatchResponse Pydantic model, hallucination guard, ApiEvent recording |
| app/routers/runs.py | Refactored pipeline using Factiva | VERIFIED | FactivaCollector imported line 22, _execute_factiva_pipeline lines 109-258, both endpoints use Factiva |

**All artifacts verified:** 4/4

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| runs.py | factiva.py | FactivaCollector.collect | WIRED | Line 22 import, line 131 instantiation, line 139 collect call with query_params and run_id |
| runs.py | deduplicator.py | ArticleDeduplicator.deduplicate | WIRED | Line 23 import, line 158 instantiation, line 159 deduplicate call |
| runs.py | insurer_matcher.py | InsurerMatcher.match_batch | WIRED | Line 24 import, line 186 instantiation, line 187 match_batch call with articles, insurers, run_id |
| insurer_matcher.py | ai_matcher.py | AIInsurerMatcher.ai_match fallback | WIRED | Line 16 import, line 33 instantiation, lines 192 and 204 ai_match calls for ambiguous cases |
| insurer_matcher.py | models/insurer.py | Type hints and queries | WIRED | Line 14 import, used in deterministic_match signature line 68, match_article line 150 |
| ai_matcher.py | models/api_event.py | ApiEvent logging | WIRED | Line 27 import, lines 239-247 and 265-274 record_event calls |

**All key links verified:** 6/6

### Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| FACT-04: Insurer matching for every article | SATISFIED | Deterministic matcher Plan 01 + AI matcher Plan 02 integrated; sentinel insurer for unmatched ensures all articles assigned |
| FACT-06: Factiva as sole active source | SATISFIED | Both execute_run and execute_category_run call _execute_factiva_pipeline; ScraperService not in active flow |

**Requirements coverage:** 2/2 satisfied

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| app/routers/runs.py | 278, 387 | Unused functions _execute_single_insurer_run, _execute_category_run | Info | Technical debt - old ScraperService functions remain but not called; should be removed in Phase 15 cleanup |

**Blocker anti-patterns:** 0
**Warning anti-patterns:** 0
**Info anti-patterns:** 1 technical debt for future cleanup

### Human Verification Required

None - all truths verified programmatically.

## Detailed Verification Evidence

### Truth 1: Every article has insurer_id assignment

**Verification method:** Code analysis of pipeline storage logic

**Evidence from runs.py lines 195-201:**
- Loop through articles and match_results
- Use sentinel general_insurer.id when match.insurer_ids is empty
- Cap at 3 insurers per article to prevent runaway duplication
- All articles get at least one insurer_id either matched or sentinel

**Sentinel creation lines 170-182:**
- ANS code 000000 (real ANS codes are 6-digit non-zero)
- Name Noticias Gerais
- Auto-created if not exists when pipeline runs

**Result:** VERIFIED - No article can be stored without insurer_id assignment.

### Truth 2: Deterministic matching without AI for clear cases

**Verification method:** Code analysis of InsurerMatcher.deterministic_match

**Evidence from insurer_matcher.py lines 65-145:**
- Combines title and description into single searchable content
- NFKD normalization via unicodedata.normalize for Portuguese accent handling
- Word-boundary regex pattern to avoid substring false positives
- Skips short names under 4 chars to prevent false positives
- Returns matched_ids before any AI involvement

**Flow verification:**
- 1 match returns deterministic_single confidence 0.95
- 2-3 matches returns deterministic_multi confidence 0.85
- 0 or >3 matches routes to AI if enabled, else unmatched

**Result:** VERIFIED - Deterministic matching happens first, AI only for ambiguous cases.

### Truth 3: AI disambiguation for ambiguous articles

**Verification method:** Code analysis of AIInsurerMatcher.ai_match

**Evidence from ai_matcher.py lines 129-254:**
- Builds insurer context limited to 200 insurers
- Calls Azure OpenAI client.beta.chat.completions.parse with InsurerMatchResponse format
- Temperature 0 for deterministic outputs
- Hallucination guard validates returned IDs against provided list
- ApiEvent recording with isolated session
- Graceful degradation when unconfigured or failed

**Structured output model lines 32-44:**
- insurer_ids list of int
- confidence 0.0 to 1.0
- reasoning string explanation

**Result:** VERIFIED - AI receives insurer context, returns structured MatchResult, validates IDs, logs events.

### Truth 4: Factiva as sole active collection path

**Verification method:** AST analysis + code inspection

**Active endpoint analysis:**
- POST /api/runs/execute line 70: calls _execute_factiva_pipeline line 98
- POST /api/runs/execute/category line 536: calls _execute_factiva_pipeline line 563

**Pipeline flow verification from runs.py lines 109-258:**
1. Load FactivaConfig
2. FactivaCollector.collect
3. URL deduplication
4. Semantic deduplication
5. Load insurers
6. Ensure sentinel insurer
7. InsurerMatcher.match_batch
8. Store and classify
9. Critical alerts
10. Generate and send report

**ScraperService status:**
- Old functions exist at lines 278 and 387
- NOT called by any active endpoint
- Remain for potential rollback but not in execution path

**Health endpoint verification lines 740-748:**
- Reports Factiva status instead of Apify scraper status

**Result:** VERIFIED - Both execution endpoints use Factiva pipeline exclusively. ScraperService not in active flow.

## Must-Haves Summary

### From Plan 11-01 Deterministic Matcher

| Must-Have | Status | Evidence |
|-----------|--------|----------|
| Articles clearly mentioning insurer matched deterministically | VERIFIED | deterministic_match word-boundary regex with NFKD normalization |
| Portuguese accents do not prevent matching | VERIFIED | normalize_text NFKD decomposition lines 37-63 |
| Short names do not produce false positives | VERIFIED | 4-char threshold line 98, short names skipped |
| Multi-insurer articles return both IDs | VERIFIED | deterministic_multi method for 2-3 matches lines 180-187 |
| Unmatched articles return empty list | VERIFIED | Lines 201-211 return method unmatched, insurer_ids empty |

**Plan 11-01:** 5/5 must-haves verified

### From Plan 11-02 AI Matcher

| Must-Have | Status | Evidence |
|-----------|--------|----------|
| Ambiguous articles sent to Azure OpenAI | VERIFIED | Lines 189-210 in insurer_matcher.py call ai_match for 0 or >3 |
| AI receives insurer context and returns structured result | VERIFIED | InsurerMatchResponse Pydantic model, lines 177-193 build context |
| Unconfigured or failed AI returns unmatched no crash | VERIFIED | Lines 151-158 unconfigured, 256-281 exception handling |
| Each AI match logged as ApiEvent | VERIFIED | Lines 238-247 success, 265-274 failure, api_name ai_matcher |

**Plan 11-02:** 4/4 must-haves verified

### From Plan 11-03 Pipeline Integration

| Must-Have | Status | Evidence |
|-----------|--------|----------|
| Pipeline invokes FactivaCollector no Apify | VERIFIED | Lines 131-139 FactivaCollector.collect, no ScraperService in active flow |
| Each stored article has insurer_id assignment | VERIFIED | Lines 195-201 sentinel fallback ensures all articles assigned |
| Deterministic first then AI for ambiguous | VERIFIED | match_article lines 167-210 shows deterministic to AI fallback flow |
| Unmatched use sentinel General News insurer | VERIFIED | Lines 170-182 create ANS 000000 Noticias Gerais, line 197 fallback |
| Multi-insurer creates one NewsItem per insurer cap 3 | VERIFIED | Lines 195-230 loop over target_ids with 3-cap line 200 |
| Scraper health endpoint removed or replaced | VERIFIED | Lines 740-748 report Factiva status instead of Apify scraper |

**Plan 11-03:** 6/6 must-haves verified

## Summary

**Total must-haves:** 18 (5 from 11-01 + 4 from 11-02 + 6 from 11-03 + 3 from phase context)
**Verified:** 18/18 (100%)

**Phase goal achievement:** COMPLETE

1. Every Factiva article matched to insurers deterministic or AI with sentinel for unmatched
2. Deterministic matching handles clear cases without AI
3. AI disambiguation for ambiguous cases with structured output
4. Factiva is sole active collection path no Apify in execution flow

**Requirements satisfied:**
- FACT-04: AI-assisted matching assigns articles to insurers
- FACT-06: Factiva replaces all Apify/RSS sources

**Technical debt noted:**
- Old ScraperService functions remain unused
- Should be removed in Phase 15 cleanup per roadmap

---

_Verified: 2026-02-19T20:35:00Z_
_Verifier: Claude (gsd-verifier)_
