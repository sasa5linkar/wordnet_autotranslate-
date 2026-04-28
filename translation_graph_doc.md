# LangGraph Translation Pipeline - Architecture

**Auto-generated:** This document is automatically generated from the code.  
**Purpose:** Visualize and document the translation pipeline graph structure.  
**Last Updated:** 1760629865.8840325

## Overview

The LangGraph Translation Pipeline uses a state machine to orchestrate the translation
of WordNet synsets through multiple specialized stages. Each stage refines and adds to
the accumulated state, building toward a complete translation result.

## Graph Structure

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	analyse_sense(analyse_sense)
	translate_definition(translate_definition)
	translate_all_lemmas(translate_all_lemmas)
	expand_synonyms(expand_synonyms)
	filter_synonyms(filter_synonyms)
	review_definition_quality(review_definition_quality)
	assemble_result(assemble_result)
	__end__([<p>__end__</p>]):::last
	__start__ --> analyse_sense;
	analyse_sense --> translate_definition;
	expand_synonyms --> filter_synonyms;
	filter_synonyms --> review_definition_quality;
	review_definition_quality --> assemble_result;
	translate_all_lemmas --> expand_synonyms;
	translate_definition --> translate_all_lemmas;
	assemble_result --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc

```

## Pipeline Stages

### 1. 📊 **analyse_sense**
**Purpose:** Understand the semantic nuance of the source synset before translation.

**Input:**
- Source synset (lemmas, definition, examples, POS)

**Processing:**
- Identifies distinguishing semantic features
- Extracts key aspects that differentiate this sense
- Assesses domain and topical context
- Builds confidence in sense understanding

**Output:**
- `sense_summary`: Concise English description (1-2 sentences)
- `key_features`: List of 2-4 distinguishing aspects
- `domain_tags`: Optional topical labels
- `confidence`: Assessment (high/medium/low)

**Why First?** Understanding the precise sense prevents mistranslation and ensures
semantic fidelity throughout the pipeline.

---

### 2. 📝 **translate_definition**
**Purpose:** Translate the definition while preserving the analyzed sense.

**Input:**
- Source synset
- Sense analysis results (from Stage 1)

**Processing:**
- Translates definition to target language
- Maintains semantic precision using sense context
- Generates example sentences in target language
- Adds lexicographer notes if needed

**Output:**
- `definition_translation`: Definition in target language
- `notes`: Optional clarifications
- `examples`: Example sentences in target language

**Why Second?** The sense analysis guides accurate definition translation,
preventing ambiguity and ensuring the correct semantic interpretation.

---

### 3. 🔤 **translate_all_lemmas**
**Purpose:** Produce direct translations for each English lemma while preserving sense alignment.

**Input:**
- Source synset
- Sense analysis (from Stage 1)

**Processing:**
- Translates each lemma individually
- Maintains array order for downstream alignment
- Emits `null` where no direct equivalent exists

**Output:**
- `initial_translations`: Ordered list of lemma translations (with optional `None` slots)
- `alignment`: Mapping of source lemmas to translations

**Why Third?** Establishing a baseline set of translations provides anchors for later expansion.

---

### 4. 🚀 **expand_synonyms**
**Purpose:** Discover additional candidate synonyms beyond the direct translations.

**Input:**
- Initial translations (from Stage 3)
- Sense analysis
- Translated definition (from Stage 2)

**Processing:**
- Iteratively proposes new synonyms using conceptual reasoning
- Records provenance (which iteration produced each synonym)
- Captures rationale for transparency

**Output:**
- `expanded_synonyms`: Aggregate list of unique candidates
- `rationale`: Mapping of synonym → justification
- `synonym_provenance`: Iteration index for each synonym
- `iterations_run` and `converged` flags

**Why Fourth?** Expansion builds breadth around the concept before filtering.

---

### 5. ✅ **filter_synonyms**
**Purpose:** Eliminate candidates that drift from the intended sense.

**Input:**
- Expanded candidate list (from Stage 4)
- Sense analysis & translated definition

**Processing:**
- Applies definition-anchored heuristics
- Removes hypernyms, narrow modifiers, and scope-shifting forms
- Assigns per-synonym confidence levels

**Output:**
- `filtered_synonyms`: Final high-quality list
- `confidence_by_word`: Confidence per synonym
- `removed`: Explanations for rejected candidates
- `confidence`: Overall stage confidence

**Why Fifth?** Quality control ensures only sense-perfect literals advance.

---

### 6. 🧪 **review_definition_quality**
**Purpose:** Polish the translated definition for grammar, circularity, and stylistic clarity.

**Input:**
- Filtered synonym list (from Stage 5)
- Translated definition (from Stage 2)

**Processing:**
- Detects circular definitions referencing synonyms
- Checks agreement, inflection, and lexicographic tone
- Suggests revised wording if issues arise

**Output:**
- `status`: `ok` or `needs_revision`
- `issues`: Categorized list of detected problems
- `revised_definition`: Improved gloss when needed
- `notes`: Summary observations

**Why Sixth?** A final editorial pass protects against linguistic flaws before publishing.

---

### 7. 📦 **assemble_result**
**Purpose:** Combine all stage outputs into a structured final result.

**Input:**
- Outputs from every previous stage

**Processing:**
- Extracts vetted synonyms and translations
- Applies compound deduplication
- Merges notes and quality findings
- Builds curator-friendly summary

**Output:**
- Complete `TranslationResult` with translation, definition, synonyms, examples, notes
- Full payload + call logs for auditing
- Summary statistics for curators

**Why Last?** Final assembly packages the refined data for downstream usage and review.

---

## State Flow

The graph uses a `TranslationGraphState` TypedDict that accumulates information:

```python
TranslationGraphState = {
	"synset": Dict[str, Any],                    # Input synset (always present)
	"sense_analysis": Dict[str, Any],            # Stage 1 output
	"definition_translation": Dict[str, Any],    # Stage 2 output
	"initial_translation_call": Dict[str, Any],  # Stage 3 output
	"expansion_call": Dict[str, Any],            # Stage 4 output
	"filtering_call": Dict[str, Any],            # Stage 5 output
	"definition_quality_call": Dict[str, Any],   # Stage 6 output
	"result": Dict[str, Any],                    # Stage 7 output
}
```

Each stage:
1. Receives the current state
2. Accesses data from previous stages
3. Calls the LLM with a stage-specific prompt
4. Updates state with its results
5. Returns updated state to next stage

## Design Rationale

### Sequential Processing
The pipeline is intentionally sequential (no parallel branches) because:
- Each stage builds on previous results
- Sense analysis informs definition translation
- Definition translation guides synonym generation
- Assembly requires all upstream data

### Modular Stages
Each stage is isolated and testable:
- Clear input/output contracts
- Independent LLM prompts
- Separate error handling per stage
- Easy to modify or extend individual stages

### State Accumulation
State grows through the pipeline:
- No information is lost
- Full audit trail of all decisions
- Downstream stages access all upstream results
- Final payload contains complete provenance

## Extensibility

### Adding New Stages
To add a stage (e.g., quality estimation):

1. Add state field to `TranslationGraphState`
2. Implement stage function: `def _estimate_quality(self, state) -> TranslationGraphState`
3. Add node: `graph.add_node("estimate_quality", self._estimate_quality)`
4. Add edge: `graph.add_edge("filter_synonyms", "estimate_quality")`
5. Update subsequent edges

### Adding Conditional Branches
For conditional logic (e.g., skip if confidence is low):

```python
def route_by_confidence(state):
    if state["sense_analysis"]["payload"].get("confidence") == "low":
        return "manual_review"
    return "translate_definition"

graph.add_conditional_edges(
    "analyse_sense",
    route_by_confidence,
    {"translate_definition": "translate_definition", "manual_review": "manual_review"}
)
```

## Monitoring & Debugging

Each stage logs:
- Full prompt sent to LLM
- Raw LLM response
- Parsed payload
- Stage name and metadata

Access logs via: `result["payload"]["logs"][stage_name]`

## Performance Considerations

- **Sequential execution**: ~3 LLM calls per synset
- **No caching**: Each synset translated independently
- **Timeout**: 600 seconds per LLM call (configurable)
- **Streaming**: `translate_stream()` for large batches

## Related Files

- **Implementation:** `src/wordnet_autotranslate/pipelines/langgraph_translation_pipeline.py`
- **Tests:** `tests/test_langgraph_pipeline.py`
- **Example Usage:** `notebooks/02_langgraph_pipeline_demo.ipynb`

## Regenerating This Document

Run the visualization script to regenerate all diagrams and documentation:

```bash
python visualize_translation_graph.py
```

This ensures documentation stays synchronized with code changes.

---

**Note:** This is an auto-generated document. Manual edits will be overwritten.
To update, modify the graph structure in the source code and re-run visualization.
