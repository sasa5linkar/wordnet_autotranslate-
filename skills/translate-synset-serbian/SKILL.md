# Skill: translate-synset-serbian

## Purpose
Agent workflow for translating an English WordNet synset to Serbian using one or multiple pipelines in this repository and an Ollama model.

## When to use
Use this skill when the user asks to translate by any of:
- English synset ID (`ENG30-########-<pos>`)
- WordNet synset name (`lemma.pos.nn`, e.g. `entity.n.01`)
- lemma + POS (+ optional sense index)

## Pipelines supported
- `langgraph` (LangGraphTranslationPipeline)
- `conceptual` (ConceptualLangGraphTranslationPipeline)
- `all` (runs both)
- `dspy` (reports not implemented in current repo)

## Workflow
1. Resolve synset selector into canonical payload using:
   - `wordnet_autotranslate.workflows.synset_translation_workflow.resolve_wordnet_synset`
2. Run selected pipeline(s):
   - `run_translation_workflow(..., pipeline=...)`
3. Return JSON output for downstream curation.

## CLI usage
```bash
python scripts/translate_synset_workflow.py --english-id ENG30-00001740-n --pipeline all --model gpt-oss:120b
```

Alternative selectors:
```bash
python scripts/translate_synset_workflow.py --synset-name entity.n.01 --pipeline langgraph
python scripts/translate_synset_workflow.py --lemma entity --pos n --sense-index 1 --pipeline conceptual
```

## Notes
- Requires NLTK WordNet availability for lookup.
- LangGraph pipelines require optional dependencies and a reachable Ollama endpoint.
- Serbian adverb POS (`b`) is normalized to WordNet adverb POS (`r`) automatically.
