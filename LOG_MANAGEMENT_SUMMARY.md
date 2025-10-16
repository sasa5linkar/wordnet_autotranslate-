# Log Management Summary

## Overview

This document provides a comprehensive summary of how logs are managed in the WordNet Auto-Translation pipeline.

## Two-Tier Logging System

The pipeline uses a **two-tier logging system** to balance performance with accessibility:

### Tier 1: Truncated Logs (Quick Access)
- **Location**: `result["payload"]["logs"]`
- **Size**: Raw responses truncated to 500 characters
- **Purpose**: Quick debugging, console inspection, live monitoring
- **Memory**: Minimal (~2.5 MB for 1,000 synsets)

### Tier 2: Full Logs (Complete Data)
- **Location**: `result["payload"]["calls"]`
- **Size**: Complete, untruncated LLM responses
- **Purpose**: Detailed analysis, quality assessment, prompt tuning
- **Memory**: Substantial (~50-250 MB for 1,000 synsets)

## Why This Design?

### Memory & Performance
When processing large batches:
- 1,000 synsets × 5 stages = 5,000 LLM calls
- Average response: 2 KB → Full storage = 10 MB
- Reasoning models can produce 50 KB+ responses → 250 MB+

### Use Case Optimization
- **Development**: Need quick console output → use truncated
- **Production**: Need audit trail → save full logs selectively
- **Analysis**: Need complete data → export full logs to files

## Accessing Full Logs

### Direct Access
```python
# Get full untruncated data for a stage
filtering_call = result["payload"]["calls"]["filtering"]
print(filtering_call["raw_response"])  # Complete response
```

### Using Utilities
```python
from wordnet_autotranslate.utils.log_utils import save_full_logs

# Save to file automatically
log_path = save_full_logs(result)
```

### Batch Processing
```python
from wordnet_autotranslate.utils.log_utils import save_batch_logs

results = pipeline.translate(synsets)
save_batch_logs(results, "logs/batch_001")
```

## Log Structure

### Full Call Object
```python
{
  "stage": "synonym_filtering",
  "prompt": "...",                    # Complete prompt
  "system_prompt": "...",             # System instructions
  "raw_response": "...",              # FULL untruncated response
  "payload": {...},                   # Parsed JSON
  "messages": [...]                   # Complete message history
}
```

### Truncated Log Object
```python
{
  "stage": "synonym_filtering",
  "prompt": "...",
  "system_prompt": "...",
  "raw_response_preview": "...… [truncated]"  # First 500 chars only
}
```

## Best Practices

### 1. Development
Use truncated logs for rapid iteration:
```python
for stage, log in result["payload"]["logs"].items():
    print(f"{stage}: {log['raw_response_preview'][:100]}")
```

### 2. Production
Save full logs selectively for important cases:
```python
if result["translated_synonyms"] == []:
    save_full_logs(result, f"logs/failed/{synset_id}.json")
```

### 3. Analysis
Export full logs for post-processing:
```python
results = pipeline.translate(synsets)
save_batch_logs(results, "logs/analysis")

# Later: analyze with external tools
```

### 4. Monitoring
Check response sizes to identify issues:
```python
from wordnet_autotranslate.utils.log_utils import analyze_stage_lengths

lengths = analyze_stage_lengths(result)
if lengths["filtering"] > 10000:
    print("⚠️ Unusually large filtering response")
```

## Utility Functions

### `save_full_logs(result, output_path=None)`
Saves complete logs with metadata for a single synset.

**Features:**
- Auto-generates filename if not specified
- Includes metadata (synset ID, timestamp, etc.)
- Pretty-formatted JSON
- Optional exclusion of prompts/messages

### `save_batch_logs(results, output_dir="logs/batch")`
Saves logs for multiple synsets to organized directory.

**Features:**
- One file per synset
- Creates index file for easy lookup
- Preserves directory structure

### `analyze_stage_lengths(result)`
Reports size of raw responses for each stage.

**Use cases:**
- Identify verbose responses
- Monitor model behavior
- Debug truncation issues

### `extract_validation_errors(result)`
Finds validation failures across all stages.

**Use cases:**
- Quality monitoring
- Prompt debugging
- Error analysis

## Memory Management Tips

### For Large Batches
```python
# Process in chunks, save incrementally
for chunk in chunks(synsets, size=100):
    results = pipeline.translate(chunk)
    save_batch_logs(results, f"logs/chunk_{i}")
    # results goes out of scope, memory freed
```

### For Interactive Use
```python
# Keep truncated in memory, save full to disk
result = pipeline.translate_synset(synset)
print(result["payload"]["logs"])  # Quick view
save_full_logs(result)             # Persist full data
del result["payload"]["calls"]     # Free memory
```

### For Analysis
```python
# Load only what you need
import json

with open("logs/synset.json") as f:
    data = json.load(f)

# Just check filtering decisions
removed = data["stages"]["filtering"]["parsed_payload"]["removed"]
```

## Integration with Pipeline

The logging system is fully integrated with:

1. **Schema Validation**: All validated payloads included in logs
2. **Retry Logic**: Each retry attempt logged separately
3. **Error Handling**: Validation errors preserved in logs
4. **Metadata**: Domain info, confidence levels, rejection reasons

## Files & Documentation

### Source Code
- `src/wordnet_autotranslate/pipelines/langgraph_translation_pipeline.py` - Main pipeline with logging
- `src/wordnet_autotranslate/utils/log_utils.py` - Utility functions

### Documentation
- `FULL_LOG_ACCESS_GUIDE.md` - Complete guide with examples
- `QUICK_REF_LOGS.md` - One-page cheat sheet
- `SCHEMA_VALIDATION_INTEGRATION.md` - Schema validation details

### Notebooks
- `notebooks/02_langgraph_pipeline_demo.ipynb` - Interactive examples

## Examples

See `FULL_LOG_ACCESS_GUIDE.md` for detailed examples including:
- Debug validation failures
- Compare prompts vs responses
- Export for external analysis
- Batch processing patterns
- Quality monitoring workflows

## Summary

The two-tier logging system provides:
- ✅ Performance: Minimal memory footprint by default
- ✅ Flexibility: Full data always available when needed
- ✅ Convenience: Utilities for easy log management
- ✅ Integration: Works seamlessly with validation & retry logic
- ✅ Scalability: Handles both single synsets and large batches

**Key Takeaway**: Truncation is for performance, but complete data is always preserved in `result["payload"]["calls"]` for when you need it.
