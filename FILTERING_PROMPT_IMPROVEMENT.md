# Filtering Prompt Improvement: Definition-Anchored Validation# Filtering Prompt Improvement: Balancing Fidelity & Naturalness



**Date**: October 18, 2025  ## Summary

**Branch**: `improving-propmts`  

**File Modified**: `src/wordnet_autotranslate/pipelines/langgraph_translation_pipeline.py`  Updated the filtering prompt to better balance **conceptual fidelity** with **target-language naturalness**, addressing the key challenge in cross-linguistic WordNet translation.

**Method**: `_render_filtering_prompt()` (lines ~995-1045)

## What Changed

---

### Old Approach: Strict Literal Matching

## Problem Analysis```

Validate the following Serbian candidates; keep only *perfect synonyms*.

### Issue IdentifiedReject any that:

The original filtering prompt prioritized **naturalness and cultural appropriateness** over strict semantic alignment:- Differ in meaning or register

- Violate POS or grammatical gender/number

- "prefer words that sound **natural, idiomatic, and culturally appropriate**"- Are dialectal or figurative unless universally interchangeable

- "Include abstract or concrete variants when they reflect how native speakers conceptualize"```

- "Prioritize native semantic norms of {target_lang} over literal translation"

**Problem**: This overly strict approach:

This approach, while promoting natural-sounding translations, was **too permissive** and allowed:- Rejects natural target-language expressions that don't perfectly align

- Prioritizes literal translation over idiomatic usage

1. **Sense drift**: Accepting translations corresponding to different senses of polysemous words- Ignores how native speakers actually conceptualize categories

2. **Semantic broadening**: Including variants that extend beyond the specific concept- Results in artificially narrow synsets

3. **Modified forms**: Keeping expressions with modifiers/particles that shift meaning

4. **Domain variants**: Accepting specialized terms that go beyond the core definition### New Approach: Conceptual Fidelity + Native Naturalness

```

### Example: "institution" Semantic DriftGuidelines:

- Preserve the *core concept* expressed in the English sense,

In demo results, the English synset "institution" (meaning: *an organization founded for a specific purpose*) was translated with Serbian candidates including "ustanova" in different senses:  but prefer words that sound natural, idiomatic, and culturally appropriate

- If multiple target words exist, choose those most typical in modern usage,

- ✅ **ustanova** (organization) - CORRECT sense  even if they cover slightly broader or narrower meanings

- ❌ **ustanova** (establishment/custom) - WRONG sense (cultural/social institution)- Include abstract or concrete variants when they reflect how

- ❌ **institucija** (institution as abstract concept) - Broader than definition  native speakers conceptualize the same category

- Reject only clearly different concepts, POS, or unnatural register

The original filtering prompt accepted these because they were "natural" and "culturally appropriate," even though they didn't match the precise definition.- Prioritize native semantic norms over literal translation when they conflict

```

---

**Benefits**: This flexible approach:

## Solution: Definition-Anchored Validation- ✅ Honors target-language semantic norms

- ✅ Includes idiomatic expressions native speakers actually use

### New Approach- ✅ Allows slight meaning variations if culturally natural

The revised prompt **anchors validation strictly to the translated definition**, not to peer comparison or naturalness alone:- ✅ Produces more usable, authentic synsets

- ✅ Better reflects actual language usage patterns

```

Guidelines:## New Output Schema

- Evaluate each candidate strictly against this definition, not just against other candidates.

- Keep only those that express the same concept described in the definition.### Added Field: `confidence_by_word`

- Discard any that correspond to other senses of the same word or a broader/narrower category.

- Prefer expressions natural and idiomatic in {target_name}, following normal usage and cultural norms.```json

- Reject any forms adding descriptive modifiers, particles, or objects that shift the meaning or argument structure.{

- Remove collocations or domain-specific variants that extend beyond the concept in the definition.  "filtered_synonyms": ["word1", "word2", "word3"],

- Keep only canonical lemmas expressing exactly this sense.  "confidence_by_word": {

```    "word1": "high",

    "word2": "medium",

### Key Changes    "word3": "high"

  },

| Aspect | Before | After |  "removed": [{"word": "X", "reason": "different concept"}],

|--------|--------|-------|  "confidence": "high"

| **Primary criterion** | Naturalness & cultural fit | Definition alignment |}

| **Validation anchor** | Peer comparison | Definition text |```

| **Sense disambiguation** | Permissive (accepts variants) | Strict (rejects other senses) |

| **Modified forms** | Accepted if natural | Rejected if shifts meaning |**Purpose**: Per-word confidence enables:

| **Domain variants** | Included if conceptually related | Removed if extends beyond definition |- Quality metrics at individual literal level

| **Philosophy** | "Native semantic norms over literal translation" | "Express exactly the concept in the definition" |- Downstream filtering by confidence threshold

- Better understanding of synonym reliability

---- More nuanced quality assessment



## Implementation Details## Philosophical Shift



### Before: Naturalness-Focused Prompt### From: Perfect Synonym Matching

- Goal: Find exact equivalents

```python- Method: Reject anything not perfectly aligned

Guidelines:- Result: Narrow, technically correct synsets

- Preserve the *core concept* expressed in the English sense,- Problem: Often misses idiomatic usage

  but prefer words and expressions that sound **natural, idiomatic, and culturally appropriate**

  in {target_name}.### To: Conceptual Equivalence

- If multiple target words exist, choose those most typical in modern usage,- Goal: Capture how natives express the concept

  even if they cover slightly broader or narrower meanings.- Method: Preserve core meaning while allowing natural variation

- Include abstract or concrete variants when they reflect how- Result: Broader, more authentic synsets

  native speakers conceptualize the same category.- Benefit: Reflects actual language patterns

- Reject only those that belong to a clearly different concept,

  part of speech, or register that would feel unnatural in {target_name}.## Key Principles

- Prioritize native semantic norms of {target_name} over literal translation

  if the two conflict.### 1. Core Concept Preservation

```**Maintain** the fundamental semantic category while allowing flexibility in expression.



### After: Definition-Anchored PromptExample:

- English: "institution, establishment"

```python- Serbian: Could include both formal ("ustanova") and colloquial ("zavod") variants

Guidelines:- Old approach: Might reject one as "different register"

- Evaluate each candidate strictly against this definition, not just against other candidates.- New approach: Accept both as valid native expressions

- Keep only those that express the same concept described in the definition.

- Discard any that correspond to other senses of the same word or a broader/narrower category.### 2. Modern Usage Priority

- Prefer expressions natural and idiomatic in {target_name}, following normal usage and cultural norms.**Prefer** words typical in contemporary usage, even if meanings don't perfectly align.

- Reject any forms adding descriptive modifiers, particles, or objects that shift the meaning or argument structure.

- Remove collocations or domain-specific variants that extend beyond the concept in the definition.Example:

- Keep only canonical lemmas expressing exactly this sense.- English: "computer"

```- Serbian: "računar" (literal: calculator) vs "kompjuter" (loanword)

- Old approach: Might favor technical term

### Docstring Updated- New approach: Accept both, note confidence levels



The method docstring now explicitly states the anti-drift purpose:### 3. Abstract/Concrete Flexibility

**Include** both abstract and concrete variants when natives use them interchangeably.

```python

"""Filtering prompt anchored to the definition to prevent sense drift.Example:

- English: "kindness" (abstract quality)

This revised prompt emphasizes strict validation against the translated definition,- Serbian: Might include both "ljubaznost" (quality) and "dobrota" (goodness)

ensuring filtered synonyms express exactly the same concept without drift into- Old approach: Strict semantic boundaries

related but different senses.- New approach: Accept if natives conceptualize similarly

```

### 4. Cultural Appropriateness

---**Reject** only unnatural or clearly inappropriate usage, not just imperfect alignment.



## Expected ImpactExample:

- English: "home"

### 1. Reduced Sense Drift- Serbian: "kuća" (house) vs "dom" (home/dwelling)

- **Before**: Filtering accepted polysemous translations if they were "natural"- Old approach: Might split into separate synsets

- **After**: Filtering rejects translations matching different senses- New approach: Include both if both feel natural

- **Impact**: Fewer homonyms and polysemous variants in final synsets

## Implementation Details

### 2. Stricter Semantic Boundaries

- **Before**: "Slightly broader or narrower meanings" were accepted### Schema Update

- **After**: Only exact conceptual matches to definition are kept```python

- **Impact**: More precise synsets aligned with WordNet semantic categoriesclass FilteringSchema(BaseModel):

    filtered_synonyms: List[str]

### 3. Cleaner Lemma Forms    confidence_by_word: Optional[Dict[str, str]] = Field(default_factory=dict)

- **Before**: Modified forms accepted if natural (e.g., "državna ustanova" - state institution)    removed: Optional[List[Dict[str, str]]] = Field(default_factory=list)

- **After**: Only canonical lemmas without modifiers (e.g., "ustanova" only)    confidence: str

- **Impact**: More consistent with WordNet lemma conventions```



### 4. Complementary to Expansion Improvements### Validation

This filtering improvement works in tandem with the **expansion prompt improvement** (see `EXPANSION_PROMPT_IMPROVEMENT.md`):- Pydantic automatically validates the new field

- Graceful fallback if LLM doesn't provide per-word confidence

- **Expansion**: Prevents drift during synonym generation- Backward compatible with old format

- **Filtering**: Catches any remaining drift during validation

- **Result**: Two-stage defense against semantic drift## Expected Impact



### 5. Quantitative Expectations### On Synset Quality

- **Broader coverage**: More synonyms per synset

Based on demo results (5 synsets):- **Higher authenticity**: More natural-sounding expressions

- **Better usability**: Reflects how natives actually speak

| Metric | Current | Expected with Improvements |

|--------|---------|---------------------------|### On Translation Accuracy

| Average removal rate | 39.6% | 25-30% (more targeted) |- **Conceptual preservation**: Core meaning maintained

| Sense drift cases | 2-3 per run | 0-1 per run |- **Cultural fit**: Better alignment with target language norms

| Definition alignment | ~70% | ~90% |- **Modern relevance**: Prioritizes contemporary usage

| Match with human WordNet | 40% | 50-60% (better precision) |

### On Downstream Use

---- **Query expansion**: Better search results with natural variants

- **Language learning**: Exposes learners to authentic usage

## Testing & Validation- **NLP applications**: More robust coverage of semantic space



### Test Results## Examples

✅ **All 16 tests pass** after implementing the filtering prompt change

### Example 1: Abstract Concept

```**English synset**: {brilliance, splendor, grandeur}

tests/test_langgraph_pipeline.py::test_langgraph_pipeline_returns_structured_dict PASSED

tests/test_langgraph_pipeline.py::test_langgraph_pipeline_batch_processing PASSED**Old approach** (strict matching):

tests/test_langgraph_pipeline.py::test_langgraph_pipeline_african_synset_example PASSED- Serbian: {sjaj} (literal brightness/shine)

[... 13 more tests ...]- Rejects: veličina (greatness), blistavost (dazzling quality)

=============================================================== 16 passed, 4 warnings in 7.86s

```**New approach** (conceptual + natural):

- Serbian: {sjaj, veličina, blistavost, raskoš}

### Backward Compatibility- Rationale: All convey magnificence in natural Serbian

- ✅ JSON schema unchanged

- ✅ API signatures unchanged### Example 2: Modern Technology

- ✅ All existing functionality preserved**English synset**: {computer, computing machine}

- ✅ Only prompt text modified

**Old approach**:

### Next Steps for Validation- Serbian: {računar} (literal: calculator)

- Rejects: kompjuter (loanword, too colloquial)

1. **Re-run demo notebook** with both improved prompts (expansion + filtering)

2. **Compare results** with original demo run**New approach**:

3. **Measure impact** on:- Serbian: {računar, kompjuter}

   - Removal rate- Rationale: Both widely used, kompjuter very common in speech

   - Sense drift reduction

   - Match rate with human WordNet### Example 3: Cultural Concept

   - Per-word confidence distribution**English synset**: {hospitality, cordial reception}

4. **Document findings** in updated results file

**Old approach**:

---- Serbian: {gostoljubivost} (formal hospitality)

- Rejects: radost (joy), toplina (warmth) - too abstract

## Philosophy: Balancing Fidelity and Naturalness

**New approach**:

The new approach **still values naturalness**, but reframes it:- Serbian: {gostoljubivost, domaćinstvo, toplina}

- Rationale: Natives conceptualize hospitality as warmth/hosting

- ❌ **Old view**: "Natural expressions override precise alignment"

- ✅ **New view**: "Natural expressions within the precise conceptual boundary"## Testing



The prompt now says:All 16 tests pass with the updated schema and prompt:

> "Prefer expressions natural and idiomatic in {target_name}, following normal usage and cultural norms."```bash

pytest tests/test_langgraph_pipeline.py -v

But this naturalness preference is **constrained** by:# 16 passed, 4 warnings

> "Keep only those that express the same concept described in the definition."```



This ensures translations are both **semantically precise** AND **naturally expressed**, rather than prioritizing one at the expense of the other.Schema validation updated to require `confidence_by_word`.



---## Documentation Updates



## Related DocumentationUpdated:

- `FilteringSchema` class definition

- **Expansion Prompt Improvement**: `EXPANSION_PROMPT_IMPROVEMENT.md`- Test mocks to include per-word confidence

- **Demo Results (original run)**: `DEMO_RESULTS_AND_CONCLUSIONS.md`- Schema validation tests

- **Code Refactoring**: `REFACTORING_SUMMARY.md`

- **Pipeline Architecture**: `translation_graph_doc.md`## Migration Notes



---### For Existing Code

- **Backward compatible**: Old payloads still work (optional field)

## Summary- **Validation**: Pydantic handles missing `confidence_by_word` gracefully

- **Tests**: Updated to expect new field

The filtering prompt improvement shifts validation from **naturalness-first** to **definition-anchored**, ensuring filtered synonyms express exactly the concept in the translated definition. Combined with the expansion prompt improvement, this creates a two-stage defense against semantic drift while maintaining natural, idiomatic expressions within the correct semantic boundaries.

### For Future Use
- Access per-word confidence: `payload["filtering"]["confidence_by_word"]["word1"]`
- Filter by confidence: `[w for w, c in conf_by_word.items() if c == "high"]`
- Quality metrics: Count high/medium/low confidence words

## Philosophy

This change reflects a fundamental insight about cross-linguistic WordNet construction:

> **Perfect synonym equivalence is less important than capturing how native speakers naturally express concepts.**

The goal is not to create a Serbian mirror of English WordNet, but to build an authentic Serbian WordNet that preserves English conceptual structure while honoring Serbian semantic norms.

## Credits

This improvement addresses real-world challenges in less-resourced language WordNet development, where overly strict matching often produces technically correct but practically unusable results.
