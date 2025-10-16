# 🔍 Quick Reference: Accessing Full Logs

## TL;DR

```python
# ✅ FULL untruncated logs are HERE:
full_logs = result["payload"]["calls"]

# ❌ NOT here (these are truncated):
truncated = result["payload"]["logs"]
```

## One-Liners

```python
# Save full logs to file
from wordnet_autotranslate.utils.log_utils import save_full_logs
save_full_logs(result, "my_logs.json")

# Access specific stage
result["payload"]["calls"]["filtering"]["raw_response"]

# Check response sizes
from wordnet_autotranslate.utils.log_utils import analyze_stage_lengths
analyze_stage_lengths(result)

# Save batch logs
from wordnet_autotranslate.utils.log_utils import save_batch_logs
save_batch_logs(results, "logs/batch")
```

## Why Two Formats?

| Format | Location | Size | Use Case |
|--------|----------|------|----------|
| **Truncated** | `result["payload"]["logs"]` | 500 chars | Quick debugging, console viewing |
| **Full** | `result["payload"]["calls"]` | Complete | Analysis, quality assessment, saving |

## Memory Impact

Processing 1,000 synsets:
- **Truncated only**: ~2.5 MB in memory
- **With full logs**: ~50-250 MB in memory

💡 **Tip**: Use truncated for live monitoring, save full logs selectively for important synsets.

## Common Patterns

### Pattern 1: Save Critical Synsets Only

```python
if len(result["translated_synonyms"]) == 0:
    save_full_logs(result, f"logs/failed/{synset_id}.json")
```

### Pattern 2: Console Inspection

```python
# Quick look at truncated
print(result["payload"]["logs"]["filtering"]["raw_response_preview"])

# Deep dive with full
print(result["payload"]["calls"]["filtering"]["raw_response"])
```

### Pattern 3: Batch Export

```python
results = pipeline.translate(synsets)
save_batch_logs(results, "logs/export")
# Creates one .json per synset + _index.json
```

## See Full Guide

📖 Read `FULL_LOG_ACCESS_GUIDE.md` for complete documentation with examples.
