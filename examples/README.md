## Examples Overview

This folder contains ready-to-import example data for the Serbian WordNet Synset Browser GUI. The main example lives under `examples/sr/` and demonstrates how Serbian and English synsets are paired in a JSON file you can import into the app.

### Directory
- `sr/serbian_english_synset_pairs_enhanced.json` — enhanced Serbian↔English synset pairing example (v2.0)

## Serbian example (enhanced v2.0)

File: `examples/sr/serbian_english_synset_pairs_enhanced.json`

This JSON uses the app’s enhanced export format (v2.0). It’s ready to import and includes richer context for each pair.

Top-level structure:
- `pairs`: list of pairing objects (each links a Serbian synset to an English synset)
- `metadata`: file-level info

Serbian fields (per pair):
- `serbian_id` (string): Serbian synset ID in ENG30-format, e.g. `ENG30-03574555-n`.
- `serbian_synonyms` (string[]): Serbian synonyms.
- `serbian_definition` (string): Serbian definition.
- `serbian_usage` (string | null): Optional usage example.
- `serbian_pos` (string): Part of speech (e.g., `n`, `v`, `a`, `r`).
- `serbian_domain` (string | null): Optional domain label.
- `serbian_relations` (object): Summary of SR WordNet relations with:
	- `total_relations` (number)
	- `relations_by_type` (object)
	- `available_relations` (object[] with target details when loaded)
	- `external_relations` (object[] for targets not in memory)

English fields (per pair):
- `english_id` (string): English synset identifier (ENG30-format or name).
- `english_definition` (string)
- `english_lemmas` (string[])
- `english_examples` (string[])
- `english_pos` (string)
- `english_name` (string): WordNet name like `institution.n.01`.
- `english_relations` (object): Princeton WordNet relations (synset-level and lemma-level keys).

Pairing metadata:
- `pairing_metadata` (object):
	- `pair_type` (string): `automatic` | `manual`
	- `quality_score` (number)
	- `translator` (string)
	- `translation_date` (string)

File metadata:
- `metadata.total_pairs` (number)
- `metadata.created_by` (string): Usually `Serbian WordNet Synset Browser`.
- `metadata.format_version` (string): `"2.0"` for enhanced format.
- `metadata.export_timestamp` (string, ISO datetime)
- `metadata.includes_relations` (boolean)
- `metadata.includes_metadata` (boolean)
- `metadata.description` (string)

Notes on versions:
- The importer accepts both `1.0` (minimal) and `2.0` (enhanced) formats.
- This example is `2.0` and contains relations and metadata fields as exported by the app.

## How to use this example in the GUI

1) Launch the GUI
- Ensure the GUI dependencies are installed.

On Windows PowerShell:

```powershell
# (Optional) create and activate a virtual environment
python -m venv .venv; .\.venv\Scripts\Activate.ps1

# Install the package with GUI extras
python -m pip install -U pip
pip install -e .[gui]

# Start the Streamlit app
python .\launch_gui.py
```

Then open the app in your browser at http://localhost:8501 if it doesn’t open automatically.

2) Import the example pairs
- In the app sidebar, find “Import Pairs”.
- Click to upload and select `examples/sr/serbian_english_synset_pairs_enhanced.json`.
- Choose import mode:
	- Merge with existing: adds new pairs and skips duplicates (duplicates are detected by `serbian_id`).
	- Replace existing: discards current pairs and loads only from the file.

3) Review and export (optional)
- After import, expand a pair to review Serbian and English details.
- Use “Export Pairs” to save your current selection. The export uses format version `2.0` with additional helpful metadata.

## Validating the JSON format (optional)

The importer expects:
- Root object with a `pairs` array.
- Each pair must include `serbian_id` and `english_id` (both strings).
- `metadata.format_version` may be `1.0` or `2.0` if present.

The included example file satisfies these rules and is ready to import.

## Contributing additional examples

If you add more examples:
- Place them under a language folder (e.g., `examples/sr/your_file.json`).
- Match the import structure (`pairs` + `metadata`).
- If you include advanced fields (relations, usage examples, etc.), keep the format consistent with the app’s exporter so they’re importable.