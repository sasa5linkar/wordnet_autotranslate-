# Schema Validation & Retry Logic Integration

## Summary

Successfully integrated Pydantic schema validation and automatic retry logic into the `LangGraphTranslationPipeline` to improve robustness and error handling.

## Changes Made

### 1. Schema Classes Added

Added 5 Pydantic schema classes for validating LLM outputs at each pipeline stage:

- **SenseAnalysisSchema**: Validates sense analysis output
  - `sense_summary` (required, min 3 chars)
  - `contrastive_note` (optional)
  - `key_features` (list)
  - `domain_tags` (optional list)
  - `confidence` (required)

- **DefinitionTranslationSchema**: Validates definition translation output
  - `definition_translation` (required)
  - `notes` (optional)
  - `examples` (optional list)

- **LemmaTranslationSchema**: Validates initial lemma translation output
  - `initial_translations` (list of optional strings, allows null values)
  - `alignment` (dict mapping originals to translations)

- **ExpansionSchema**: Validates synonym expansion output
  - `expanded_synonyms` (list of strings)
  - `rationale` (optional dict with explanations)

- **FilteringSchema**: Validates synonym filtering output
  - `filtered_synonyms` (list of strings)
  - `removed` (optional list of dicts with word-reason pairs)
  - `confidence` (required: high|medium|low)

### 2. Validation Helper Functions

- **`validate_stage_payload()`**: Generic validation function that:
  - Validates payloads against Pydantic schemas
  - Returns validated data via `model_dump()`
  - On validation failure:
    - Logs warning with validation errors
    - Creates fallback dict with default values
    - Handles `PydanticUndefined` properly for `default_factory` fields
  - Merges fallback with partial payload data

- **`_validate_payload_for_stage()`**: Instance method that:
  - Maps stage names to appropriate schema classes
  - Automatically selects correct schema based on stage
  - Delegates to `validate_stage_payload()` for actual validation

### 3. Enhanced `_call_llm()` Method

Updated to include retry logic and automatic validation:

```python
def _call_llm(self, prompt: str, stage: str, retries: int = 2) -> Dict[str, Any]:
```

**New Features:**
- **Retry parameter**: Defaults to 2 attempts (3 total tries)
- **Automatic validation**: Validates all payloads against stage-specific schemas
- **Success checking**: Verifies payload contains valid data before returning
- **Retry logging**: Prints informative messages on each retry attempt
- **Graceful degradation**: Returns error payload after max retries exceeded

**Flow:**
1. Invoke LLM with prompt
2. Decode JSON response
3. Validate against schema for current stage
4. Check if payload has valid data
5. Return on success, retry on failure
6. Log errors and return fallback after max retries

### 4. Updated Filtering Prompt

Improved `_render_filtering_prompt()` to request structured rejections:

**Old format:**
```json
{
  "filtered_synonyms": ["word1", "word2"]
}
```

**New format:**
```json
{
  "filtered_synonyms": ["word1", "word2"],
  "removed": [{"word": "X", "reason": "broader meaning"}],
  "confidence": "high|medium|low"
}
```

### 5. Test Updates

Updated all test mocks (`_DummyLLM`, `_MultiSynonymLLM`, etc.) to return correct schema formats:

- Added support for 7-stage pipeline (was 3-stage)
- Updated assertions to check new payload structure
- Fixed expected call counts (6 instead of 3)
- Updated terminology ("literals" instead of "candidates")

**Test Results:** All 16 tests passing ✅

## Benefits

1. **Robust Error Handling**: Automatic retry on malformed LLM outputs
2. **Data Validation**: Ensures all stage outputs conform to expected schemas
3. **Graceful Degradation**: Falls back to defaults rather than crashing
4. **Better Debugging**: Validation warnings show exactly what's wrong
5. **Type Safety**: Pydantic ensures correct data types at runtime
6. **Transparency**: Structured rejections show why candidates were removed
7. **Quality Metrics**: Confidence levels allow downstream quality assessment

## Files Modified

1. `src/wordnet_autotranslate/pipelines/langgraph_translation_pipeline.py`
   - Added Pydantic imports
   - Added 5 schema classes
   - Added validation helper functions
   - Enhanced `_call_llm()` with retry logic
   - Improved filtering prompt

2. `tests/test_langgraph_pipeline.py`
  - Updated all mock LLMs for 7-stage pipeline
  - Fixed test assertions for new payload structure
  - Adjusted expected call counts

3. `test_schema_validation.py` (new file)
   - Comprehensive test suite for schema validation
   - Tests all 5 schemas with valid and invalid data
   - Validates fallback behavior

## Usage Example

```python
# The pipeline now automatically validates and retries
pipeline = LangGraphTranslationPipeline(
    source_lang="en",
    target_lang="sr",
    llm=llm_instance
)

# If LLM returns malformed JSON, pipeline will:
# 1. Log validation warning
# 2. Retry up to 2 times
# 3. Return fallback payload if still failing
result = pipeline.translate_synset(synset)

# Result payload includes validation metadata
print(result["payload"]["filtering"]["confidence"])  # "high|medium|low"
print(result["payload"]["filtering"]["removed"])  # [{"word": "X", "reason": "..."}]
```

## Next Steps (Optional Enhancements)

1. Make retry count configurable per pipeline instance
2. Add retry backoff delays for rate-limited APIs
3. Log validation metrics for quality monitoring
4. Add schema versioning for backward compatibility
5. Create detailed validation reports for analysis
