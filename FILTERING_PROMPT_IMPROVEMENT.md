# Filtering Prompt Improvement: Balancing Fidelity & Naturalness

## Summary

Updated the filtering prompt to better balance **conceptual fidelity** with **target-language naturalness**, addressing the key challenge in cross-linguistic WordNet translation.

## What Changed

### Old Approach: Strict Literal Matching
```
Validate the following Serbian candidates; keep only *perfect synonyms*.
Reject any that:
- Differ in meaning or register
- Violate POS or grammatical gender/number
- Are dialectal or figurative unless universally interchangeable
```

**Problem**: This overly strict approach:
- Rejects natural target-language expressions that don't perfectly align
- Prioritizes literal translation over idiomatic usage
- Ignores how native speakers actually conceptualize categories
- Results in artificially narrow synsets

### New Approach: Conceptual Fidelity + Native Naturalness
```
Guidelines:
- Preserve the *core concept* expressed in the English sense,
  but prefer words that sound natural, idiomatic, and culturally appropriate
- If multiple target words exist, choose those most typical in modern usage,
  even if they cover slightly broader or narrower meanings
- Include abstract or concrete variants when they reflect how
  native speakers conceptualize the same category
- Reject only clearly different concepts, POS, or unnatural register
- Prioritize native semantic norms over literal translation when they conflict
```

**Benefits**: This flexible approach:
- ✅ Honors target-language semantic norms
- ✅ Includes idiomatic expressions native speakers actually use
- ✅ Allows slight meaning variations if culturally natural
- ✅ Produces more usable, authentic synsets
- ✅ Better reflects actual language usage patterns

## New Output Schema

### Added Field: `confidence_by_word`

```json
{
  "filtered_synonyms": ["word1", "word2", "word3"],
  "confidence_by_word": {
    "word1": "high",
    "word2": "medium",
    "word3": "high"
  },
  "removed": [{"word": "X", "reason": "different concept"}],
  "confidence": "high"
}
```

**Purpose**: Per-word confidence enables:
- Quality metrics at individual literal level
- Downstream filtering by confidence threshold
- Better understanding of synonym reliability
- More nuanced quality assessment

## Philosophical Shift

### From: Perfect Synonym Matching
- Goal: Find exact equivalents
- Method: Reject anything not perfectly aligned
- Result: Narrow, technically correct synsets
- Problem: Often misses idiomatic usage

### To: Conceptual Equivalence
- Goal: Capture how natives express the concept
- Method: Preserve core meaning while allowing natural variation
- Result: Broader, more authentic synsets
- Benefit: Reflects actual language patterns

## Key Principles

### 1. Core Concept Preservation
**Maintain** the fundamental semantic category while allowing flexibility in expression.

Example:
- English: "institution, establishment"
- Serbian: Could include both formal ("ustanova") and colloquial ("zavod") variants
- Old approach: Might reject one as "different register"
- New approach: Accept both as valid native expressions

### 2. Modern Usage Priority
**Prefer** words typical in contemporary usage, even if meanings don't perfectly align.

Example:
- English: "computer"
- Serbian: "računar" (literal: calculator) vs "kompjuter" (loanword)
- Old approach: Might favor technical term
- New approach: Accept both, note confidence levels

### 3. Abstract/Concrete Flexibility
**Include** both abstract and concrete variants when natives use them interchangeably.

Example:
- English: "kindness" (abstract quality)
- Serbian: Might include both "ljubaznost" (quality) and "dobrota" (goodness)
- Old approach: Strict semantic boundaries
- New approach: Accept if natives conceptualize similarly

### 4. Cultural Appropriateness
**Reject** only unnatural or clearly inappropriate usage, not just imperfect alignment.

Example:
- English: "home"
- Serbian: "kuća" (house) vs "dom" (home/dwelling)
- Old approach: Might split into separate synsets
- New approach: Include both if both feel natural

## Implementation Details

### Schema Update
```python
class FilteringSchema(BaseModel):
    filtered_synonyms: List[str]
    confidence_by_word: Optional[Dict[str, str]] = Field(default_factory=dict)
    removed: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    confidence: str
```

### Validation
- Pydantic automatically validates the new field
- Graceful fallback if LLM doesn't provide per-word confidence
- Backward compatible with old format

## Expected Impact

### On Synset Quality
- **Broader coverage**: More synonyms per synset
- **Higher authenticity**: More natural-sounding expressions
- **Better usability**: Reflects how natives actually speak

### On Translation Accuracy
- **Conceptual preservation**: Core meaning maintained
- **Cultural fit**: Better alignment with target language norms
- **Modern relevance**: Prioritizes contemporary usage

### On Downstream Use
- **Query expansion**: Better search results with natural variants
- **Language learning**: Exposes learners to authentic usage
- **NLP applications**: More robust coverage of semantic space

## Examples

### Example 1: Abstract Concept
**English synset**: {brilliance, splendor, grandeur}

**Old approach** (strict matching):
- Serbian: {sjaj} (literal brightness/shine)
- Rejects: veličina (greatness), blistavost (dazzling quality)

**New approach** (conceptual + natural):
- Serbian: {sjaj, veličina, blistavost, raskoš}
- Rationale: All convey magnificence in natural Serbian

### Example 2: Modern Technology
**English synset**: {computer, computing machine}

**Old approach**:
- Serbian: {računar} (literal: calculator)
- Rejects: kompjuter (loanword, too colloquial)

**New approach**:
- Serbian: {računar, kompjuter}
- Rationale: Both widely used, kompjuter very common in speech

### Example 3: Cultural Concept
**English synset**: {hospitality, cordial reception}

**Old approach**:
- Serbian: {gostoljubivost} (formal hospitality)
- Rejects: radost (joy), toplina (warmth) - too abstract

**New approach**:
- Serbian: {gostoljubivost, domaćinstvo, toplina}
- Rationale: Natives conceptualize hospitality as warmth/hosting

## Testing

All 16 tests pass with the updated schema and prompt:
```bash
pytest tests/test_langgraph_pipeline.py -v
# 16 passed, 4 warnings
```

Schema validation updated to require `confidence_by_word`.

## Documentation Updates

Updated:
- `FilteringSchema` class definition
- Test mocks to include per-word confidence
- Schema validation tests

## Migration Notes

### For Existing Code
- **Backward compatible**: Old payloads still work (optional field)
- **Validation**: Pydantic handles missing `confidence_by_word` gracefully
- **Tests**: Updated to expect new field

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
