# Expansion Prompt Improvement - Preventing Semantic Drift

**Date**: October 18, 2025  
**Issue**: Expansion stage sometimes drifts into different senses of polysemous words  
**Solution**: Revised prompt emphasizing conceptual alignment over surface similarity

---

## Problem Analysis

During demo execution, we observed that the expansion stage occasionally generated synonyms that fit **different senses** of the target words rather than the specific WordNet sense being translated. This "semantic drift" occurred because:

1. **Surface Similarity Bias**: LLM relied on word similarity rather than concept matching
2. **Polysemy Confusion**: Didn't distinguish between multiple senses of the same word
3. **Loose Guidelines**: Original prompt lacked explicit drift prevention instructions

### Example Issue: "Institution"

The original expansion generated candidates that could fit different senses:
- ✅ `sedište` (headquarters) - **correct sense**
- ⚠️ `ustanova` (establishment/institute) - **different but related sense**
- ❌ `baza` (military base) - **wrong connotation**

---

## Solution: Revised Expansion Prompt

### Key Changes

#### Before (Original Prompt)
```python
"""
Generate additional {target_name} synonyms matching this precise sense.

Tasks:
1. Retain all initial translations.
2. Add strictly synonymous words—same POS, meaning, and register.
3. Exclude hypernyms, antonyms, or stylistic shifts.
"""
```

**Issues:**
- Generic instruction to "match this precise sense"
- No explicit drift prevention
- Focused on exclusions (what NOT to do) rather than alignment

#### After (Revised Prompt)
```python
"""
You are expanding a synonym set for a WordNet synset in {target_name}.

Core meaning (sense summary):
{sense_summary}

Translated definition (for reference):
{definition_translation}

Existing {target_name} translations:
{base_synonyms}

Guidelines:
- Generate new synonyms that express **exactly this concept**, not other senses of the same word.
- Stay faithful to the described meaning and avoid extensions that fit different senses.
- Exclude expressions that refer to locations, titles, or figurative uses unless the definition requires them.
- Do not rely on surface similarity to the existing words; reason from the concept itself.
- Keep to canonical lemma forms and natural, modern vocabulary.
"""
```

**Improvements:**
1. **Explicit Sense Grounding**: Uses sense summary as primary reference point
2. **Anti-Drift Instructions**: Explicitly warns against expanding into other senses
3. **Conceptual Reasoning**: Instructs LLM to reason from concept, not word similarity
4. **Context-Aware Exclusions**: Prevents location/title/figurative extensions unless appropriate
5. **Clearer Structure**: Separates context (summary + definition) from instructions

---

## Technical Implementation

### Code Changes

**File**: `src/wordnet_autotranslate/pipelines/langgraph_translation_pipeline.py`  
**Method**: `_render_expansion_prompt()`  
**Lines**: ~933-990

**Signature**:
```python
def _render_expansion_prompt(
    self,
    initial_payload: Dict[str, Any],
    sense_payload: Dict[str, Any],
    definition_payload: Dict[str, Any],
) -> str:
    """Generate prompt for synonym expansion stage (revised: prevents semantic drift).
    
    This revised prompt emphasizes alignment with the core concept to prevent
    expansion into homonyms or polysemous translations. It instructs the LLM
    to reason from the concept itself rather than surface word similarity.
    """
```

**Key Variables**:
- `sense_summary`: Primary semantic anchor (e.g., "A physical establishment serving as headquarters...")
- `definition_translation`: Secondary reference for concept boundaries
- `base_synonyms`: Starting point for expansion (not the primary reasoning base)

---

## Expected Impact

### Immediate Effects

1. **Reduced Semantic Drift**
   - Fewer candidates that fit different senses
   - Better alignment with WordNet sense distinctions
   - More consistent expansion across iterations

2. **Improved Filtering Efficiency**
   - Fewer candidates need removal in filtering stage
   - Higher proportion of high-confidence synonyms
   - Reduced removal rate (currently 39.6%)

3. **Better Conceptual Coherence**
   - Synonyms that truly express the same concept
   - Less reliance on lexical overlap
   - More linguistically appropriate suggestions

### Measurable Metrics (Expected)

| Metric | Before | After (Expected) |
|--------|--------|------------------|
| Removal Rate | 39.6% | ~25-30% |
| High Confidence | 87.5% | ~90-95% |
| Sense Drift Cases | Occasional | Rare |
| Filtering Rejections | "Different concept" common | Less common |

---

## Testing & Validation

### Unit Tests
- ✅ All 16 tests pass (7.06s)
- ✅ No regression in existing functionality
- ✅ Prompt generation still works correctly

### Manual Testing Needed

To validate the improvement, we should:

1. **Re-run Demo Notebook** with new prompt
   - Compare expansion quality
   - Measure removal rate changes
   - Check sense alignment

2. **Test on Problematic Cases**
   - Polysemous words (e.g., "bank", "run", "set")
   - Abstract concepts (e.g., "justice", "freedom")
   - Technical terms with general meanings

3. **Curator Feedback**
   - Are expanded synonyms more aligned?
   - Fewer "wrong sense" rejections?
   - Better rationale quality?

---

## Related Changes

This improvement complements other recent enhancements:

1. **Iterative Expansion** (5 iterations)
   - Now less likely to drift across iterations
   - Each iteration stays focused on core concept

2. **Improved Filtering Prompt**
   - Better equipped to catch remaining drift cases
   - Explicit "different concept" rejection reason

3. **Compound Deduplication**
   - Removes redundant multiword expressions
   - Works independently of drift prevention

---

## Recommendations

### Short-term
1. ✅ **Apply change immediately** (done)
2. 🔄 **Run validation tests** on demo synsets
3. 📊 **Measure impact** on removal rates

### Medium-term
1. **A/B Testing**: Compare old vs new prompt on 50+ synsets
2. **Fine-tune Guidelines**: Adjust based on observed patterns
3. **Add Examples**: Include good/bad expansion examples in prompt

### Long-term
1. **Few-Shot Learning**: Add 2-3 concrete examples to prompt
2. **Sense Disambiguation**: Enhance sense analysis with contrastive examples
3. **Feedback Loop**: Incorporate curator feedback into prompt refinement

---

## Documentation Updates

This change is documented in:
- ✅ This file: `EXPANSION_PROMPT_IMPROVEMENT.md`
- ✅ Code docstring: Enhanced with drift prevention explanation
- ✅ Inline comments: Added reasoning notes
- 🔄 Main README: Update pending
- 🔄 FILTERING_PROMPT_IMPROVEMENT.md: Cross-reference pending

---

## Conclusion

The revised expansion prompt addresses semantic drift by:
1. **Grounding expansion in sense summary** rather than word similarity
2. **Explicitly preventing drift** into other senses
3. **Emphasizing conceptual reasoning** over lexical matching

This improvement should reduce filtering rejections and improve overall translation quality by keeping expansion tightly aligned with the intended WordNet sense.

**Status**: ✅ Implemented and tested  
**Next Step**: Validate on demo synsets and measure impact

---

**Related Documents**:
- `FILTERING_PROMPT_IMPROVEMENT.md` - Filtering stage improvements
- `ITERATIVE_EXPANSION_FEATURE.md` - Multi-iteration expansion
- `DEMO_RESULTS_AND_CONCLUSIONS.md` - Observed semantic drift cases
