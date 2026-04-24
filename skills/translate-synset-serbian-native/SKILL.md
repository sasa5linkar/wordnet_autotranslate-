---
name: translate-synset-serbian-native
description: Native Codex workflow for translating a single English WordNet synset to Serbian without Ollama, LangChain, or LangGraph runtime calls. Use when Codex should resolve an explicit ILI like i35545, an ENG30 synset id, a WordNet synset name, or lemma plus POS; inspect Princeton WordNet data; draft Serbian JSON outputs; compare baseline, langgraph, conceptual, or all reasoning modes; or intentionally retranslate an existing synset.
---

# Native Single-Synset Translation

Resolve the selector first, then translate. Do not call the Python LangChain or Ollama pipelines for native-agent runs.

## Resolve The Source Synset

Run the deterministic resolver and keep the JSON payload as the working source object:

```powershell
.\.venv313\Scripts\python scripts\resolve_synset_selector.py --ili i35545 --with-relations
```

Supported selectors:

- `--ili`
- `--english-id`
- `--synset-name`
- `--lemma` together with `--pos`

Use `--with-relations` by default for native-agent work so the payload includes hypernyms, hyponyms, meronyms, holonyms, similar synsets, lexname, and topic domains.

## Produce Native-Agent Output

Return JSON compatible with the repo's existing workflow envelope:

```json
{
  "selector_id": "ENG30-00001740-n",
  "source_synset": {},
  "pipelines": {
    "baseline": {},
    "langgraph": {},
    "conceptual": {}
  }
}
```

Use these reasoning modes:

- `baseline`: translate only gloss plus literals.
- `langgraph`: emulate the existing multi-phase workflow with sense analysis, definition translation, initial literal translation, synonym expansion, synonym filtering, and result assembly.
- `conceptual`: build a concept package, expand EN and SR definitions, generate candidates, select literals, draft the final Serbian gloss, and validate the synset.
- `all`: run all three modes side by side in one JSON document.

Keep structured JSON keys aligned with the current repo output whenever practical.

## Gloss Quality Rules

Apply these rules before finalizing Serbian output:

- Prefer short, native-sounding Serbian dictionary-style glosses over abstract metalanguage.
- For particles, conjunctions, discourse markers, pronouns, prepositions, auxiliaries, and other function words, keep the gloss especially short and usage-oriented.
- Do not use stiff phrases such as `krajnja granica` unless Serbian examples clearly support that wording.
- If a candidate gloss sounds like linguistics commentary instead of a lexicographic definition, rewrite it.

For discourse particles and other construction-sensitive items:

- Separate the core literal from context-bound surface variants.
- Keep only stable lemma-level forms as primary literals.
- Treat variants that depend on negation or a specific syntactic frame as notes or lower-priority variants unless they clearly function as independent literals.

Before saving:

- Check at least 3 natural Serbian example sentences.
- Make sure the gloss fits those examples without paraphrasing them awkwardly.
- If examples support `neočekivan slučaj` better than `krajnja granica`, prefer the more natural wording.

## Save Results

If the user gives an output path, write there. Otherwise prefer a path under `data/native_translation_runs/`.

For reproducibility, include:

- the resolved `source_synset`
- the chosen `pipeline` or `pipelines`
- the final Serbian literals and gloss
- concise notes on uncertainty or lexical tradeoffs

## Retranslation Policy

Do not skip a synset because it already exists in Serbian WordNet or because it was translated before. Retranslation and comparison runs are expected.
