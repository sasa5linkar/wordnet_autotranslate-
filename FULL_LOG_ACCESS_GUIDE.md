# Full Log Access Guide

## Quick Answer

**Q: Where are the untruncated logs?**  
**A:** `result["payload"]["calls"]` contains **complete, untruncated** LLM call data.

## Structure Overview

Every translation result has **two** log formats:

```python
result = pipeline.translate_synset(synset)

# 1. TRUNCATED logs (for quick viewing)
truncated = result["payload"]["logs"]
# Raw responses truncated to 500 characters

# 2. FULL UNTRUNCATED logs (for analysis)
full = result["payload"]["calls"]
# Complete raw responses, prompts, and metadata
```

## Why Truncate?

**Performance & Memory:**
- Processing 1,000 synsets with 5 stages = 5,000 LLM calls
- Average response: 2KB → 10MB total in memory
- Full responses can be 50KB+ with reasoning → 250MB+ in memory
- JSON serialization becomes slow and files become huge

**Use Cases:**
- **Truncated logs**: Quick debugging, console inspection, live monitoring
- **Full logs**: Detailed analysis, quality assessment, prompt tuning

## Accessing Full Logs

### In Code

```python
# Access full data for a specific stage
filtering_call = result["payload"]["calls"]["filtering"]

print(f"Stage: {filtering_call['stage']}")
print(f"Prompt: {filtering_call['prompt']}")
print(f"System prompt: {filtering_call['system_prompt']}")
print(f"Raw response: {filtering_call['raw_response']}")
print(f"Parsed payload: {filtering_call['payload']}")
print(f"Messages: {filtering_call['messages']}")
```

### Save to File

```python
# Method 1: Manual save
import json

with open("full_logs.json", "w", encoding="utf-8") as f:
    json.dump(result["payload"]["calls"], f, indent=2, ensure_ascii=False)
```

```python
# Method 2: Use utility function (recommended)
from wordnet_autotranslate.utils.log_utils import save_full_logs

log_path = save_full_logs(result)
print(f"Saved to: {log_path}")
```

### Batch Processing

```python
from wordnet_autotranslate.utils.log_utils import save_batch_logs

# Translate multiple synsets
results = pipeline.translate(synsets[:100])

# Save all logs to directory
log_dir = save_batch_logs(results, output_dir="logs/batch_001")
print(f"Saved {len(results)} log files to: {log_dir}")
```

## Log Structure Details

### Full Call Data Structure

```python
{
  "stage": "synonym_filtering",
  "prompt": "Validate the following Serbian candidates...",
  "system_prompt": "You are an expert translator...",
  "raw_response": "{\"filtered_synonyms\": [...], ...}",  # FULL, untruncated
  "payload": {
    "filtered_synonyms": ["sinonim1", "sinonim2"],
    "removed": [{"word": "X", "reason": "broader meaning"}],
    "confidence": "high"
  },
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ]
}
```

### Truncated Log Structure

```python
{
  "stage": "synonym_filtering",
  "prompt": "Validate the following Serbian candidates...",
  "system_prompt": "You are an expert translator...",
  "raw_response_preview": "{\"filtered_synonyms\": [...], ...}… [truncated]"  # First 500 chars
}
```

## Utility Functions

### `save_full_logs(result, output_path=None)`

Saves complete logs for a single synset with metadata.

**Options:**
- `include_prompts=True` - Include full prompts
- `include_messages=True` - Include message history

**Returns:** Path to saved file

### `save_batch_logs(results, output_dir="logs/batch")`

Saves logs for multiple synsets to a directory.

**Features:**
- One JSON file per synset
- Creates index file (`_index.json`)
- Organized directory structure

**Returns:** Path to output directory

### `analyze_stage_lengths(result)`

Analyzes response sizes for each stage.

**Example output:**
```
expansion            12,456 chars
filtering             8,234 chars
definition_translation 3,456 chars
sense_analysis        2,890 chars
initial_translation   1,234 chars
```

### `extract_validation_errors(result)`

Finds any validation errors or warnings in pipeline stages.

**Returns:** List of validation issues

## Best Practices

### 1. Development Mode (Quick Debugging)

```python
# Use truncated logs for console inspection
for stage, log in result["payload"]["logs"].items():
    print(f"{stage}: {log['raw_response_preview'][:100]}...")
```

### 2. Production Mode (Quality Assessment)

```python
# Save full logs for critical synsets
from wordnet_autotranslate.utils.log_utils import save_full_logs

for synset in critical_synsets:
    result = pipeline.translate_synset(synset)
    save_full_logs(result, f"logs/critical/{synset['id']}.json")
```

### 3. Batch Processing (Selective Logging)

```python
# Only save full logs for synsets with issues
results = pipeline.translate(synsets)

for result in results:
    # Check if there were problems
    if result["translated_synonyms"] == [] or result.get("notes"):
        save_full_logs(result, f"logs/issues/{result['source']['id']}.json")
```

### 4. Analysis (Post-Processing)

```python
import json
from pathlib import Path

# Load logs for analysis
log_files = Path("logs/batch_001").glob("*.json")

for log_file in log_files:
    with open(log_file) as f:
        data = json.load(f)
    
    # Analyze filtering decisions
    removed = data["stages"]["filtering"]["parsed_payload"].get("removed", [])
    if removed:
        print(f"{log_file.stem}: Removed {len(removed)} candidates")
        for item in removed:
            print(f"  - {item['word']}: {item['reason']}")
```

## Examples

### Example 1: Debug Validation Failures

```python
result = pipeline.translate_synset(synset)

# Check if any stage had validation issues
for stage, call in result["payload"]["calls"].items():
    payload = call["payload"]
    if isinstance(payload, dict) and "error" in payload:
        print(f"⚠️ {stage} failed validation")
        print(f"Raw response: {call['raw_response']}")
```

### Example 2: Compare Prompt vs Response

```python
filtering_call = result["payload"]["calls"]["filtering"]

print("=== PROMPT ===")
print(filtering_call["prompt"])

print("\n=== RESPONSE ===")
print(filtering_call["raw_response"])

print("\n=== PARSED ===")
print(json.dumps(filtering_call["payload"], indent=2))
```

### Example 3: Export for External Analysis

```python
# Export to CSV for spreadsheet analysis
import csv

results = pipeline.translate(synsets)

with open("analysis.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Synset ID", "Translation", "Filtered Count", "Removed Count", "Confidence"])
    
    for result in results:
        filtering = result["payload"]["filtering"]
        writer.writerow([
            result["source"]["id"],
            result["translation"],
            len(filtering.get("filtered_synonyms", [])),
            len(filtering.get("removed", [])),
            filtering.get("confidence", "N/A")
        ])
```

## See Also

- `SCHEMA_VALIDATION_INTEGRATION.md` - Schema validation documentation
- `notebooks/02_langgraph_pipeline_demo.ipynb` - Interactive examples
- `src/wordnet_autotranslate/utils/log_utils.py` - Utility source code
