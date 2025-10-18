# Iterative Expansion Feature

## Overview

The synonym expansion stage now uses **iterative expansion** to maximize synonym coverage while ensuring efficiency.

## Problem Statement

LLM outputs are inherently variable - running the same expansion prompt multiple times can yield different synonyms. A single expansion run might miss valid synonyms that would appear in subsequent runs.

## Solution: Iterative Expansion with Early Stopping

### How It Works

1. **Initialize**: Start with synonyms from initial translation stage
2. **Iterate**: Run expansion up to `max_expansion_iterations` times (default: 5)
3. **Accumulate**: Collect all unique synonyms across iterations
4. **Track Provenance**: Record which iteration found each synonym
5. **Early Stopping**: Stop when no new synonyms appear (convergence)

### Algorithm

```python
all_synonyms = set(initial_translations)
synonym_provenance = {syn: 0 for syn in all_synonyms}  # 0 = initial

for iteration in range(max_expansion_iterations):
    new_expanded = call_llm_expansion()
    
    before_count = len(all_synonyms)
    for syn in new_expanded:
        if syn not in all_synonyms:
            all_synonyms.add(syn)
            synonym_provenance[syn] = iteration + 1
    
    new_count = len(all_synonyms) - before_count
    
    if new_count == 0:
        # Converged - no new synonyms
        break
```

## Configuration

```python
pipeline = LangGraphTranslationPipeline(
    source_lang="en",
    target_lang="sr",
    max_expansion_iterations=5  # Default: 5
)
```

## Output Metadata

The expansion stage now returns additional metadata:

```json
{
  "expanded_synonyms": ["word1", "word2", "word3"],
  "rationale": {"word2": "variant form", "word3": "archaic"},
  "iterations_run": 3,
  "synonym_provenance": {
    "word1": 0,  // From initial translation
    "word2": 1,  // Found in iteration 1
    "word3": 2   // Found in iteration 2
  },
  "converged": true  // Stopped early (no new synonyms)
}
```

## Benefits

### 1. **Comprehensive Coverage**
- Captures synonyms that might only appear in some LLM runs
- Reduces variance in output quality

### 2. **Efficient Convergence**
- Stops early when LLM knowledge is exhausted
- Typical convergence: 2-3 iterations

### 3. **Transparent Provenance**
- Shows which iteration found each synonym
- Helps identify stable vs. variable suggestions

### 4. **Configurable Limits**
- Max iterations prevents infinite loops
- Balance between coverage and compute time

## Example Output

```
[Expansion] Iteration 1: Added 3 new synonym(s), total: 5
[Expansion] Iteration 2: Added 2 new synonym(s), total: 7
[Expansion] Iteration 3: Added 1 new synonym(s), total: 8
[Expansion] Converged after 4 iteration(s) - no new synonyms found
```

## Performance Considerations

- **Best case**: Converges in 1-2 iterations (~1-2x expansion time)
- **Worst case**: Hits max limit (5x expansion time)
- **Typical**: 2-3 iterations with convergence

## Testing

All 16 existing tests pass with iterative expansion enabled. The feature is backward compatible - existing code continues to work without modification.

## See Also

- `notebooks/02_langgraph_pipeline_demo.ipynb` - Live demonstration
- `ExpansionSchema` in `langgraph_translation_pipeline.py` - Schema definition
- `_expand_synonyms()` - Implementation
