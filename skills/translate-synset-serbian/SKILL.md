---
name: translate-synset-serbian
description: Translate English WordNet synsets to Serbian inside Codex using pure agent workflows or optional repo-backed Ollama comparisons. Use when the user asks Codex to translate, draft, curate, compare, or batch-process Serbian WordNet synsets by ENG30 ID, synset name, lemma+POS, spreadsheet/list rows, or raw synset data without wanting to run CLI commands.
---

# Translate Synset Serbian

## Default Behavior

Translate inside the Codex session. Do not ask the user to run CLI commands.

Default to `agent-multiphase` when the user says "translate this synset" or gives selectors without naming a workflow. Use local repo code only for lookup/context unless the user explicitly asks for Ollama, LangGraph, Conceptual, baseline, or repo pipeline output.

If the user asks for "all three workflows", use `agent-all`: `agent-baseline`, `agent-multiphase`, and `agent-conceptual`.

If the user asks for "all repo workflows", "Ollama", or "LangGraph", use the repository pipelines through `run_translation_workflow`; report backend/dependency failures plainly and continue with pure agent output when useful.

## Workflow Options

- `agent-baseline`: Pure Codex version of the dissertation baseline. Use only English literals, POS, definition, and examples. Return direct Serbian literals and a Serbian gloss.
- `agent-multiphase`: Pure Codex version of the LangGraph generate-and-filter workflow. Analyze sense, translate gloss, generate literal candidates, expand candidates, filter candidates, then assemble the final synset.
- `agent-conceptual`: Pure Codex version of the concept-oriented workflow. Build a concept package, avoid circular glosses, generate precise Serbian literals, select/reject candidates, write a final gloss, and validate the synset.
- `agent-all`: Run all three pure agent workflows side-by-side.
- `repo-baseline`, `repo-langgraph`, `repo-conceptual`, `repo-all`: Optional repository-backed workflows. These may require `langgraph`, `langchain-ollama`, and a reachable Ollama backend.

## Resolve Synsets

Accept selectors in any of these forms:

- ENG30 ID: `ENG30-########-<pos>`
- WordNet name: `entity.n.01`
- lemma + POS, with optional sense index
- table/list rows containing any of the above
- raw synset payloads containing `lemmas`, `definition`, `examples`, and `pos`

Prefer direct Python imports over CLI wrappers:

```python
from wordnet_autotranslate.workflows.synset_translation_workflow import (
    resolve_wordnet_synset,
    synset_to_payload,
)
```

If needed, run a small internal Python snippet from Codex to resolve selectors. Do not make the user run it.

Canonical payload:

```json
{
  "id": "ENG30-00001740-n",
  "english_id": "ENG30-00001740-n",
  "name": "entity.n.01",
  "pos": "n",
  "lemmas": ["entity"],
  "definition": "that which is perceived or known or inferred to have its own distinct existence",
  "examples": []
}
```

## Serbian Drafting Rules

- Default to Serbian Latin script unless the user requests Cyrillic or the target data clearly uses Cyrillic.
- Keep WordNet style: concise literals, concise gloss, no encyclopedia prose.
- Preserve synset sense, not just the headword.
- Prefer lexical Serbian equivalents over long explanations when valid.
- For nouns, prefer nominative singular unless the concept requires another form.
- For verbs, prefer infinitive.
- For adjectives/adverbs, preserve POS and register.
- Avoid circular definitions: do not define a literal with the same literal unless unavoidable.
- Mark uncertain, region-specific, archaic, or calque-like candidates in notes instead of hiding uncertainty.

## Pure Agent Output Schema

Return structured JSON when the user wants machine-readable results; otherwise give a concise table plus notes.

For one workflow:

```json
{
  "selector_id": "ENG30-00001740-n",
  "source_synset": {},
  "pipelines": {
    "agent-multiphase": {
      "status": "ok",
      "translation": "entitet",
      "translated_synonyms": ["entitet"],
      "definition_translation": "ono sto se opaza, zna ili zakljucuje kao nesto sa sopstvenim zasebnim postojanjem",
      "confidence": "medium",
      "notes": []
    }
  }
}
```

For `agent-all`, include these keys under `pipelines`:

- `agent-baseline`
- `agent-multiphase`
- `agent-conceptual`

## Agent-Baseline Steps

1. Read source literals, POS, definition, and examples only.
2. Translate each literal directly if it is a valid Serbian lexical item for the sense.
3. Translate the gloss directly and compactly.
4. Return `translation`, `translated_synonyms`, `definition_translation`, `confidence`, and `notes`.

## Agent-Multiphase Steps

1. `sense_analysis`: summarize the exact WordNet sense, domain, contrastive risks, and POS constraints.
2. `definition_translation`: draft a Serbian gloss faithful to the definition.
3. `initial_translation`: translate source literals directly.
4. `expansion`: add Serbian synonyms or near-synonyms that fit the same synset.
5. `filtering`: reject candidates that are too broad, too narrow, wrong POS, unnatural, circular, or register-mismatched.
6. `assemble_result`: choose representative `translation`, final `translated_synonyms`, gloss, confidence, and notes.

## Agent-Conceptual Steps

1. `concept_package`: describe the language-neutral concept, POS, domain, hypernym-like class, examples, and terms to avoid in a circular gloss.
2. `expanded_definition_en`: restate the source sense in precise English.
3. `expanded_definition_sr`: restate the concept in Serbian without committing to final literals.
4. `literal_candidates`: propose Serbian lexical candidates with fit/naturalness notes.
5. `selection`: choose final literals and list rejected candidates with reasons.
6. `final_gloss`: write a short Serbian WordNet-style gloss.
7. `validation`: check POS, sense fidelity, synonymy, naturalness, circularity, and whether the entry is ready for curation.
8. `assemble_result`: return selected literals, final gloss, validation status, confidence, and curator notes.

## Repo-Backed Optional Runs

When the user explicitly asks for repo/Ollama workflows, call:

```python
from wordnet_autotranslate.workflows.synset_translation_workflow import (
    WorkflowConfig,
    run_translation_workflow,
)
```

Use `pipeline="baseline"`, `"langgraph"`, `"conceptual"`, or `"all"`. If dependencies or the Ollama backend fail, preserve the error in the report and offer/produce the equivalent pure agent workflow.

## Batch Behavior

For multiple synsets, process row-by-row. Keep each result independent and include:

- selector or row number
- resolved synset ID/name/POS
- selected workflow(s)
- final Serbian literals
- final Serbian gloss
- confidence
- notes or validation issues

For large batches, summarize successes/failures and write a JSON report into `reports/` only when the user asks for a saved artifact.
