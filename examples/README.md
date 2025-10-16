# Examples Directory

This folder hosts ready-to-use bilingual example data that powers the
WordNet auto-translation pipelines and GUI. The primary artifact is an
enhanced JSON export that mirrors what the Serbian Synset Browser
produces when you download curated pairings.

## Current Contents

- `serbian_english_synset_pairs_enhanced.json` – a rich sample dataset
	capturing Serbian ⟷ English synset alignments plus relation metadata.

The JSON is UTF-8 encoded and contains two top-level keys:

```json
{
	"pairs": [
		{
			"serbian_id": "ENG30-03574555-n",
			"english_id": "ENG30-03574555-n",
			"serbian_synonyms": ["ustanova"],
			"english_lemmas": ["institution", "establishment"],
			"serbian_definition": "…",
			"english_definition": "…",
			"serbian_usage": "…",
			"english_examples": ["…"],
			"serbian_pos": "n",
			"english_pos": "n",
			"serbian_relations": {"…"},
			"english_relations": {"…"},
			"pairing_metadata": {"pair_type": "automatic", … }
		}
	],
	"metadata": {
		"total_pairs": 123,
		"format_version": "2.0",
		"created_by": "Serbian WordNet Synset Browser",
		"export_timestamp": "2024-06-01T12:00:00",
		"includes_relations": true,
		"includes_metadata": true,
		"description": "Enhanced export with Serbian and English relations for translation context"
	}
}
```

Field names match the structure expected by the Streamlit GUI and by the
`SerbianWordnetPipeline`. Relation blocks (`serbian_relations` and
`english_relations`) bundle hypernyms, hyponyms, lemma-level data, and
any auxiliary context harvested from the Serbian WordNet XML.

## How to Use the Sample Dataset

### In the Streamlit Synset Browser

1. Launch the browser (`python launch_gui.py`).
2. In the sidebar, open **Import / Export** → **Import enhanced JSON**.
3. Select `examples/serbian_english_synset_pairs_enhanced.json`.
4. The pre-populated pairs will appear in the pairing workspace, ready to
	 review, edit, or export again.

When you build new pairings inside the GUI, the **Download Enhanced Pairs
(JSON)** button exports data in the exact format shown above, so you can
replace or version the file in this directory as needed.

### In Pipelines or Scripts

- Treat the file as a quick fixture for integration tests or demos.
- Convert it to other formats (CSV, Parquet) if you need analytics, but
	keep the canonical JSON for round-trip compatibility with the GUI.
- The `LangGraphTranslationPipeline` examples in `tests/` also rely on
	this schema when mocking LLM responses.

## Adding or Updating Example Data

1. Generate or edit pairings inside the GUI, then export the enhanced
	 JSON.
2. Save the file back into `examples/`, ideally naming it
	 `<targetlang>_<sourcelang>_synset_pairs_enhanced.json` for clarity.
3. Ensure the `metadata.format_version` stays at `2.0` unless the
	 validation logic in `SynsetBrowserApp._validate_import_data` is
	 updated.
4. Run the GUI import once to confirm the JSON loads without warnings.
5. Include a short changelog entry in your pull request describing the
	 origin of the new examples.

If you curate language-specific corpora outside the GUI, replicate the
same keys the browser expects. Optional fields (usage examples, relations
or metadata) can be omitted, but keeping them populated improves the
translation experience.

## Legacy Text-Based Examples (Optional)

The original translation pipeline still supports lightweight text
examples organised as:

```
examples/
└── <language-code>/
		├── words.txt
		└── sentences.txt
```

This structure is useful for quick prototypes or languages where full
synset pairings are not yet available. The files may contain any plain
text lists; lines starting with `#` are treated as comments.

However, the GUI and the end-to-end Serbian flow now rely on the enhanced
JSON exports described above. Prefer contributing data in that format so
all tooling stays in sync.

## Contributing

Pull requests that add fresh bilingual pairings, expand relation
coverage, or improve metadata are welcome. Please keep large source XML
files in `data/` (git-ignored) and only commit derived example files that
are safe to share.