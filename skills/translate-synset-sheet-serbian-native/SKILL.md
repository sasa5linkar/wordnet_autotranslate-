---
name: translate-synset-sheet-serbian-native
description: Native Codex workflow for translating Serbian WordNet batch inputs from Excel, CSV, or public Google Sheets without Ollama, LangChain, or LangGraph runtime calls. Use when Codex should prepare a workbook-driven queue, resolve ILI or ENG30 or synset-name or lemma-plus-POS rows, keep working until every pending row is finished, and save structured JSON results for each row, including intentional retranslations.
---

# Native Sheet Translation

Prepare the batch first, then process every pending work item until none remain.

## Prepare The Batch

Run the native batch-prep script:

```powershell
.\.venv313\Scripts\python scripts\prepare_native_translation_batch.py path\to\input.xlsx --pipeline all
```

The script creates a run folder with:

- `input/`
- `logs/`
- `summary/`
- `work_items/pending/`
- `results/`

Rows may use:

- `ili`
- `english_id`
- `synset_name`
- `lemma` plus `pos`

Do not add duplicate-skipping logic. Each row is independent, even when the same synset appears multiple times.

## Process Pending Work Items

Open each JSON file under `work_items/pending/` and translate it natively with the requested reasoning mode:

- `baseline`
- `langgraph`
- `conceptual`
- `all`

Use the queue manager script so only one item is claimed at a time:

```powershell
.\.venv313\Scripts\python scripts\manage_native_translation_batch.py claim-next D:\path\to\run_dir
```

After you draft a `translation_result` object, finalize it with:

```powershell
.\.venv313\Scripts\python scripts\manage_native_translation_batch.py complete D:\path\to\run_dir D:\path\to\work_item.json --result-file D:\path\to\translation_result.json
```

If the item cannot be completed, record a structured failure with:

```powershell
.\.venv313\Scripts\python scripts\manage_native_translation_batch.py fail D:\path\to\run_dir D:\path\to\work_item.json --message "short reason"
```

For each completed item:

1. Write the final row result JSON under `results/success/...` using the same pipeline and selector path pattern.
2. Move the processed work item out of `work_items/pending/` into `work_items/completed/`.
3. If translation fails, write a structured error JSON under `results/error/...` and move the work item into `work_items/failed/`.

Keep going until `work_items/pending/` is empty.

## Gloss Quality Rules

When drafting each row result:

- Prefer short, native-sounding Serbian dictionary-style glosses over abstract metalanguage.
- For particles, conjunctions, discourse markers, pronouns, prepositions, auxiliaries, and other function words, keep the gloss especially short and usage-oriented.
- Do not use stiff phrases such as `krajnja granica` unless Serbian examples clearly support that wording.
- If a gloss sounds like linguistics commentary instead of a real Serbian dictionary definition, rewrite it before completing the row.

For construction-sensitive items:

- Separate the core literal from context-bound surface variants.
- Keep stable lemma-level forms as primary literals.
- Treat variants tied to negation or a narrow syntactic frame as contextual variants unless they clearly function as independent literals.

Before calling `complete` for a row:

- Check at least 3 natural Serbian example sentences.
- Confirm that the selected gloss fits those examples naturally.
- Prefer `neočekivan slučaj` or similar natural wording over abstract phrases such as `krajnja granica` when the examples point that way.

## Row Result Shape

Prefer this structure for each completed row:

```json
{
  "row_number": 2,
  "status": "success",
  "selector_kind": "ili",
  "selector_value": "i35545",
  "pipeline": "all",
  "synset_payload": {},
  "translation_result": {}
}
```

Use the same `translation_result` envelope as the single-synset native skill.

## Completion Rule

Do not stop after preparing the queue. Finish only when every pending row has either:

- a success result and a completed work item, or
- an error result and a failed work item

If the user asks for best-effort behavior, continue past row-level failures. If the user explicitly asks for fail-fast behavior, stop after the first blocking error.
