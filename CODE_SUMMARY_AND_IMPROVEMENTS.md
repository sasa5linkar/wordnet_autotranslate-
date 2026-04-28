# WordNet Auto-Translation: Code Summary & Improvement Suggestions

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Layout](#2-repository-layout)
3. [Component-by-Component Summary](#3-component-by-component-summary)
   - 3.1 [Package Root (`__init__.py`)](#31-package-root)
   - 3.2 [TranslationPipeline](#32-translationpipeline)
   - 3.3 [LangGraphTranslationPipeline](#33-langgraphtranslationpipeline)
   - 3.4 [SerbianWordnetPipeline](#34-serbianwordnetpipeline)
   - 3.5 [SynsetHandler](#35-synsethandler)
   - 3.6 [XmlSynsetParser & Synset dataclass](#36-xmlsynsetparser--synset-dataclass)
   - 3.7 [LanguageUtils](#37-languageutils)
   - 3.8 [log_utils](#38-log_utils)
   - 3.9 [Streamlit GUI (synset_browser.py)](#39-streamlit-gui-synset_browserpy)
   - 3.10 [Jupyter Notebooks](#310-jupyter-notebooks)
   - 3.11 [Helper Scripts](#311-helper-scripts)
   - 3.12 [Tests](#312-tests)
   - 3.13 [Configuration (`pyproject.toml`)](#313-configuration-pyprojecttoml)
4. [Data Flow Diagram](#4-data-flow-diagram)
5. [Suggestions for Improvement](#5-suggestions-for-improvement)
   - 5.1 [Critical Bugs & Code Correctness](#51-critical-bugs--code-correctness)
   - 5.2 [Incomplete Implementations (TODOs)](#52-incomplete-implementations-todos)
   - 5.3 [Code Quality & Style](#53-code-quality--style)
   - 5.4 [Architecture & Design](#54-architecture--design)
   - 5.5 [Testing](#55-testing)
   - 5.6 [Documentation](#56-documentation)
   - 5.7 [Performance](#57-performance)
   - 5.8 [Security & Dependency Management](#58-security--dependency-management)
6. [Priority Roadmap](#6-priority-roadmap)

---

## 1. Project Overview

**wordnet_autotranslate** is a Python library for automatically expanding
[Princeton WordNet](https://wordnet.princeton.edu/) into less-resourced
languages. It targets the Serbian WordNet as its primary demo language but is
designed to be extensible to any language. The workflow is:

1. Load English synsets from NLTK WordNet.
2. Analyse each synset's semantic sense using a large language model (LLM).
3. Translate the definition and lemmas into the target language.
4. Expand and filter synonym candidates.
5. Optionally validate/judge the output with a second LLM pass.
6. Export results to WordNet-LMF-compatible XML.

The project also ships an interactive Streamlit browser for examining and
pairing Serbian synsets with their English counterparts.

---

## 2. Repository Layout

```
wordnet_autotranslate/
├── src/
│   └── wordnet_autotranslate/          # Installable Python package
│       ├── __init__.py                 # Public API surface
│       ├── pipelines/
│       │   ├── translation_pipeline.py          # DSPy-based pipeline (stub)
│       │   ├── langgraph_translation_pipeline.py # LangGraph + Ollama pipeline
│       │   └── serbian_wordnet_pipeline.py       # End-to-end Serbian pipeline
│       ├── models/
│       │   ├── synset_handler.py       # NLTK WordNet wrapper
│       │   └── xml_synset_parser.py    # Serbian XML parser
│       ├── gui/
│       │   └── synset_browser.py       # Streamlit GUI
│       └── utils/
│           ├── language_utils.py       # POS normalisation, text helpers
│           └── log_utils.py            # LLM call log persistence helpers
├── tests/                              # pytest test suite
│   ├── test_basic.py
│   ├── test_xml_parser.py
│   ├── test_synset_handler.py
│   ├── test_langgraph_pipeline.py
│   ├── test_import_export.py
│   └── test_gui_optional_deps.py
├── notebooks/
│   ├── 01_introduction.ipynb
│   └── 02_langgraph_pipeline_demo.ipynb
├── examples/                           # Target-language word/sentence files
│   └── serbian_english_synset_pairs_enhanced.json
├── launch_gui.py                       # CLI helper to start Streamlit
├── demo_functionality.py               # Manual end-to-end smoke test
├── examine_wordnet_synsets.py          # Script to inspect NLTK synset features
├── visualize_translation_graph.py      # Generate Mermaid / PNG graph
├── pyproject.toml                      # Build system + dependency spec
└── *.md                                # Documentation files
```

---

## 3. Component-by-Component Summary

### 3.1 Package Root

**File:** `src/wordnet_autotranslate/__init__.py`

Re-exports the main public symbols so consumers only need
`from wordnet_autotranslate import …`:

| Symbol | Provided by |
|---|---|
| `TranslationPipeline` | `pipelines/translation_pipeline.py` |
| `LangGraphTranslationPipeline` | `pipelines/langgraph_translation_pipeline.py` |
| `SerbianWordnetPipeline` | `pipelines/serbian_wordnet_pipeline.py` |
| `SynsetHandler` | `models/synset_handler.py` |
| `XmlSynsetParser`, `Synset` | `models/xml_synset_parser.py` |
| `LanguageUtils` | `utils/language_utils.py` |

---

### 3.2 TranslationPipeline

**File:** `src/wordnet_autotranslate/pipelines/translation_pipeline.py`

A **stub** pipeline that was intended to use DSPy for synset translation. Currently:

- `__init__` sets `source_lang`, `target_lang`, and the path to the
  `examples/` directory.
- `load_english_synsets()` returns an empty list (TODO).
- `load_target_synsets()` returns an empty list (TODO).
- `load_examples()` reads `words.txt` and `sentences.txt` from
  `examples/<target_lang>/`, using an `@lru_cache`-backed helper to avoid
  repeated disk reads.
- `translate()` returns an empty list (TODO).

**Key design note:** `_load_text_file` is a module-level cached function;
it skips blank lines and comment lines (starting with `#`).

---

### 3.3 LangGraphTranslationPipeline

**File:** `src/wordnet_autotranslate/pipelines/langgraph_translation_pipeline.py`

The **production-ready** multi-stage translation pipeline. It orchestrates LLM
calls through a LangGraph state machine backed by a local Ollama instance
(default model: `gpt-oss:120b`).

#### Architecture — 6-stage graph

```
START
  │
  ▼
analyse_sense        ← Stage 1: Understand the semantic nuance
  │
  ▼
translate_definition ← Stage 2: Translate the English gloss
  │
  ▼
translate_all_lemmas ← Stage 3: Directly translate every English lemma
  │
  ▼
expand_synonyms      ← Stage 4: Broaden the candidate pool
  │
  ▼
filter_synonyms      ← Stage 5: Quality-gate — remove imperfect matches
  │
  ▼
assemble_result      ← Stage 6: Package everything into TranslationResult
  │
  ▼
END
```

#### Key classes

| Class | Purpose |
|---|---|
| `TranslationGraphState` | TypedDict state container passed between nodes |
| `TranslationResult` (dataclass) | Final output with `translation`, `translated_synonyms`, `definition_translation`, `examples`, `curator_summary`, `payload`, etc. |
| `SenseAnalysisSchema` | Pydantic model validating stage-1 LLM output |
| `DefinitionTranslationSchema` | Pydantic model validating stage-2 LLM output |
| `LemmaTranslationSchema` | Pydantic model validating stage-3 LLM output |
| `ExpansionSchema` | Pydantic model validating stage-4 LLM output |
| `FilteringSchema` | Pydantic model validating stage-5 LLM output |

#### Key methods

| Method | Role |
|---|---|
| `_build_graph()` | Constructs and compiles the LangGraph state machine |
| `translate_synset(synset)` | Translates a single synset dict |
| `translate(synsets)` | Batch wrapper |
| `translate_stream(synsets)` | Generator variant |
| `_call_llm(prompt, stage)` | LLM invocation with JSON retry logic |
| `_decode_llm_payload(raw)` | Robust JSON extraction (handles `<think>` tags, fenced code blocks, etc.) |
| `_validate_payload_for_stage(stage, payload)` | Selects and applies the right Pydantic schema |
| `_get_wordnet_domain_info(english_id)` | Fetches `lexname` and `topic_domains` from NLTK |
| `_assemble_result(state)` | Collects all stage outputs into a `TranslationResult` |

#### Dependencies

Loaded lazily so the rest of the package can be used without them:
`langgraph`, `langchain-core`, `langchain-ollama`.

---

### 3.4 SerbianWordnetPipeline

**File:** `src/wordnet_autotranslate/pipelines/serbian_wordnet_pipeline.py`

A simplified end-to-end pipeline designed specifically for generating a draft
Serbian WordNet from English synsets.

#### Stages

1. **`load_english_synsets()`** — iterates over `wn.all_synsets()` up to
   `pilot_limit` and returns plain dicts with `id`, `pos`, `lemmas`, `gloss`,
   `examples`, `hypernyms`.

2. **`generate_serbian_synset(syn)`** — currently a **placeholder** that
   prefixes each English lemma with `srp_` and the gloss with `(SRP)`. When
   DSPy is available it is meant to call a proper LLM prompt (the hook exists
   but the real logic is marked TODO).

3. **`judge_synset(eng, srp)`** — quality gate. Currently always returns
   `True` (placeholder).

4. **`export_to_xml(synsets, path)`** — writes a `<SRPWN>` root element
   containing `<SYNSET>`, `<SYNONYM>`, `<LITERAL>`, `<DEF>`, `<EXAMPLES>`,
   and `<ILR>` elements in a WordNet-LMF-compatible style.

5. **`run(output_xml)`** — orchestrates the four stages above.

#### POS mapping

English adverb `'r'` is mapped to Serbian `'b'` before export.

---

### 3.5 SynsetHandler

**File:** `src/wordnet_autotranslate/models/synset_handler.py`

A **wrapper around NLTK WordNet** that exposes synset data as plain dicts,
suitable for serialisation and downstream LLM prompting.

#### Key capabilities

- Graceful degradation when NLTK is not installed (`NLTK_AVAILABLE` flag).
- Lazy WordNet data download via `_ensure_wordnet_data()`.
- In-memory relation cache keyed by synset name to avoid repeated NLTK lookups.
- POS normalisation: Serbian `'b'` → English `'r'` in `get_synset_by_offset`.

#### Relation extraction hierarchy

```
_extract_all_relations
  ├── _extract_hierarchical_relations  (hypernyms, hyponyms, instances)
  ├── _extract_meronymy_relations      (part/member/substance)
  ├── _extract_semantic_relations      (similar_tos, also)
  ├── _extract_pos_specific_relations  (verb: entailments/causes/verb_groups;
  │                                    adj: attributes)
  └── _extract_lemma_relations         (antonyms, pertainyms, derivationally_related)
```

#### Main public methods

| Method | Purpose |
|---|---|
| `get_synsets(word)` | All synsets for a word |
| `get_all_synsets(pos=None)` | Full WordNet iteration (expensive) |
| `search_synsets(query, limit)` | Synonym of `get_synsets` with a result limit |
| `get_synset_by_offset(offset, pos)` | Lookup by numeric offset + POS |
| `get_synsets_by_relation(synset_name, relation_type)` | Follow one relation type |
| `get_relation_comparison_data(synset_name)` | Structured dict for comparison with Serbian WN |
| `get_relation_summary(synset_name)` | Counts + samples of all relations |
| `get_relation_types()` | List of all recognised relation names |

---

### 3.6 XmlSynsetParser & Synset dataclass

**File:** `src/wordnet_autotranslate/models/xml_synset_parser.py`

Parses Serbian WordNet XML files (and in-memory XML strings) into `Synset`
dataclass instances.

#### `Synset` dataclass fields

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Synset ID, often an ENG30 form (`ENG30-OFFSET-POS`) |
| `pos` | `str` | Part of speech (`n`, `v`, `a`, `b` for adverbs) |
| `synonyms` | `List[Dict]` | List of `{literal, sense?, lnote?}` dicts |
| `definition` | `str` | Serbian gloss |
| `bcs` | `str` | Base Concept Set level (1–3) |
| `ilr` | `List[Dict]` | Inter-lingual relations `{target, type}` |
| `nl` | `str` | Native language flag |
| `stamp` | `str` | Timestamp / editor attribution |
| `sumo` | `Optional[Dict]` | SUMO ontology mapping `{concept, type}` |
| `sentiment` | `Optional[Dict]` | `{positive: float, negative: float}` |
| `domain` | `Optional[str]` | Semantic domain label |
| `usage` | `Optional[str]` | Usage example string |

#### `XmlSynsetParser` internals

- Maintains three dicts: `synsets` (id→Synset), `english_links`
  (ENG30-id→\[Synset\]), `_search_cache` (query→results).
- English ID normalization: adverb suffix `-b` → `-r` for consistent cross-
  language lookup.
- Parsing decomposes into small private methods (`_parse_required_fields`,
  `_parse_synonyms`, `_parse_ilr_relations`, `_parse_sumo`,
  `_parse_sentiment`) for testability.
- Comma decimal separator handled in `_parse_float_with_comma` (sentiment
  values in Serbian XML use `0,00000` format).

---

### 3.7 LanguageUtils

**File:** `src/wordnet_autotranslate/utils/language_utils.py`

A collection of **static utility methods** for language processing.

| Method | Description |
|---|---|
| `is_supported_language(lang_code)` | Checks against a hard-coded dict of 10 languages |
| `get_language_name(lang_code)` | Returns full name (e.g. `'en'` → `'English'`) |
| `clean_text(text)` | Collapses whitespace, strips special chars |
| `extract_words(text)` | Simple word tokenisation via regex |
| `normalize_pos_for_english(pos)` | Maps Serbian POS to NLTK: `'b'` → `'r'` |
| `normalize_pos_for_serbian(pos)` | Maps NLTK POS to Serbian: `'r'` → `'b'` |
| `load_stopwords(lang_code)` | Returns hard-coded stopword sets for `en`, `es`, `fr` |
| `validate_examples_directory(path, lang)` | Checks presence/content of examples files |
| `get_available_languages(examples_path)` | Lists language sub-directories |

---

### 3.8 log_utils

**File:** `src/wordnet_autotranslate/utils/log_utils.py`

Helper functions for **persisting and inspecting full LLM call logs** produced
by `LangGraphTranslationPipeline`.

| Function | Description |
|---|---|
| `save_full_logs(result, output_path)` | Saves a single synset's complete LLM logs to a JSON file |
| `save_batch_logs(results, output_dir)` | Saves logs for a batch of synsets, plus an `_index.json` |
| `analyze_stage_lengths(result)` | Returns character counts per pipeline stage |
| `extract_validation_errors(result)` | Extracts error entries from stage payloads |

---

### 3.9 Streamlit GUI (`synset_browser.py`)

**File:** `src/wordnet_autotranslate/gui/synset_browser.py`

An interactive **Streamlit** web application for:

- Loading Serbian synsets from uploaded XML files.
- Browsing synsets page-by-page with a configurable page size.
- Full-text searching across definitions, synonyms, and usage examples.
- Filtering by part of speech.
- Viewing detailed synset cards including ILR relations, SUMO annotations,
  sentiment scores, and computed quality score.
- Pairing Serbian synsets with English synsets (manual + auto via
  `SynsetHandler`).
- Exporting selected pairs as a JSON training dataset.

#### Design highlights

- Optional imports of `streamlit` and `pandas`; falls back to a
  `_StreamlitStub` when running headless (e.g., in CI).
- All Streamlit session state keys are string constants (e.g.,
  `SESSION_CURRENT_SYNSET`).
- Display-level constants for page size, score thresholds, and text truncation
  lengths.

---

### 3.10 Jupyter Notebooks

| Notebook | Purpose |
|---|---|
| `01_introduction.ipynb` | Getting-started walkthrough: installation, basic synset queries |
| `02_langgraph_pipeline_demo.ipynb` | Hands-on demo of the 6-stage LangGraph pipeline with example output |

---

### 3.11 Helper Scripts

| Script | Purpose |
|---|---|
| `launch_gui.py` | Calls `streamlit run …` programmatically; handles path setup |
| `examine_wordnet_synsets.py` | CLI script to dump all features (relations, lemmas, etc.) for a given NLTK synset; useful for prompt engineering |
| `visualize_translation_graph.py` | Generates a Mermaid diagram (`translation_graph.mmd`), plain text (`translation_graph.txt`), and PNG image showing the LangGraph pipeline DAG |
| `demo_functionality.py` | End-to-end smoke test / demo that exercises each component in sequence |

---

### 3.12 Tests

The `tests/` directory uses **pytest**. Each file is focused on one module:

| File | Covers |
|---|---|
| `test_basic.py` | Package imports, `TranslationPipeline` init, `LanguageUtils`, example loading |
| `test_xml_parser.py` | `XmlSynsetParser`: parsing, searching, POS filtering, clearing, English-ID extraction |
| `test_synset_handler.py` | `SynsetHandler`: offset lookup, relation traversal, error on missing NLTK |
| `test_langgraph_pipeline.py` | `LangGraphTranslationPipeline` with a `_DummyLLM`; covers batch, stream, JSON decoding, schema validation, curator summary |
| `test_import_export.py` | `SerbianWordnetPipeline`: XML export round-trip |
| `test_gui_optional_deps.py` | GUI module imports when `streamlit`/`pandas` are absent |

---

### 3.13 Configuration (`pyproject.toml`)

- **Build system:** `setuptools` ≥ 61 with `src` layout.
- **Core dependencies:** `dspy-ai`, `nltk`, `transformers`, `torch`, `wn`,
  `numpy`, `pandas`, `scipy`, `pyyaml`, `python-dotenv`, `loguru`.
- **Optional extras:**
  - `[notebooks]` — Jupyter, matplotlib, seaborn
  - `[gui]` — streamlit, gradio
  - `[langgraph]` — langgraph, langchain-core, langchain-ollama
  - `[dev]` — pytest, black, flake8, mypy
- **Tool configs:** black (line length 88), mypy (strict, Python 3.8), pytest
  (discover `tests/`).

---

## 4. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     User / Researcher                           │
└──────────┬──────────────────────────────────┬───────────────────┘
           │ Python API                        │ Streamlit GUI
           ▼                                   ▼
┌─────────────────────┐            ┌─────────────────────────────┐
│ SerbianWordnetPipe  │            │      synset_browser.py      │
│ line or LangGraph   │            │  (load XML → browse → pair  │
│ TranslationPipeline │            │   → export JSON pairs)      │
└──────────┬──────────┘            └──────────┬──────────────────┘
           │                                   │
    ┌──────┴──────┐                     ┌──────┴──────┐
    │             │                     │             │
    ▼             ▼                     ▼             ▼
SynsetHandler  LLM (Ollama /     XmlSynsetParser  SynsetHandler
(NLTK WordNet)  DSPy / other)    (Serbian XML)    (NLTK lookups)
    │
    ▼
NLTK WordNet
(local corpus)
           │
           ▼
   XML export (SRPWN)  or  JSON training pairs
```

---

## 5. Suggestions for Improvement

### 5.1 Critical Bugs & Code Correctness

#### 5.1.1 Dead code after `return` in `_get_wordnet_domain_info`

**Location:** `langgraph_translation_pipeline.py`, lines 888–894

After a `return` statement there are two unreachable lines:

```python
        # Return the lexname (domain)
        return synset.lexname()       # ← dead
    except (ValueError, LookupError, AttributeError):
        return None                   # ← dead (duplicate except block)
```

These lines were left behind during refactoring and should be removed.

#### 5.1.2 `print()` used instead of `logging` in production code

**Location:** `langgraph_translation_pipeline.py`, lines 703 and 706 inside
`_call_llm`.

`validate_stage_payload` (line 151) also uses `print` for warnings.
All user-facing diagnostic output should go through Python's `logging` module
(or `loguru`, which is already a declared dependency) so callers can control
verbosity.

#### 5.1.3 Python 3.10+ union type hint (`str | Path`) breaks Python 3.8 support

**Location:** `log_utils.py`, function signatures `save_full_logs` and
`save_batch_logs`.

```python
def save_full_logs(result, output_path: str | Path = None, ...):
```

The `X | Y` union syntax was introduced in Python 3.10. The project declares
`requires-python = ">=3.8"` in `pyproject.toml`. Use `Optional[Union[str,
Path]]` or `from __future__ import annotations` to support Python 3.8/3.9.

#### 5.1.4 Hardcoded debug synset ID in production parser

**Location:** `xml_synset_parser.py`, constant `DEBUG_SYNSET_ID =
"ENG30-08621598-n"` and its uses in `_parse_synsets_from_root`,
`_parse_synset_element`, and `get_synset_by_id`.

Debug logging that is tied to a single hard-coded synset ID should be removed
from production code. If needed for development, use a dedicated test fixture
or a CLI flag.

#### 5.1.5 Missing blank line before `load_stopwords` method

**Location:** `language_utils.py`, around line 99.

There is no blank line between the end of `normalize_pos_for_serbian` and the
`@staticmethod` decorator for `load_stopwords`, which violates PEP 8 and will
be flagged by `flake8`.

---

### 5.2 Incomplete Implementations (TODOs)

#### 5.2.1 `TranslationPipeline` is a stub

`load_english_synsets()`, `load_target_synsets()`, and `translate()` all
return empty lists. While `LangGraphTranslationPipeline` is the active
implementation, `TranslationPipeline` is exported from the public API and
will confuse users. Either:

- Implement the DSPy-based logic, or
- Mark the class as `NotImplemented` / `DeprecationWarning` in the docstring
  and README, or
- Remove it from `__all__` until the implementation is ready.

#### 5.2.2 `SerbianWordnetPipeline.generate_serbian_synset()` is a placeholder

The function currently returns `srp_<lemma>` strings. The DSPy integration
hook (`_placeholder_dspy_usage()`) is present but does nothing. Connecting
this to either the DSPy or LangGraph pipeline would make the end-to-end
`SerbianWordnetPipeline.run()` actually useful.

#### 5.2.3 `SerbianWordnetPipeline.judge_synset()` always returns `True`

A real quality gate (e.g., a second LLM-as-judge call, a dictionary
cross-check, or a rule-based scorer) is needed before this pipeline is
suitable for production use.

#### 5.2.4 `LanguageUtils.load_stopwords()` only covers `en`, `es`, `fr`

The comment says "TODO: Add language-specific stopwords". Serbian (`sr`) in
particular is missing, even though the project is primarily targeting Serbian.

#### 5.2.5 `examples/` directory structure is underpopulated

The README documents a structure `examples/<lang>/words.txt` and
`examples/<lang>/sentences.txt`, but the actual `examples/` folder only
contains `serbian_english_synset_pairs_enhanced.json`. Providing at least a
minimal Serbian example set would make the package demo self-contained.

---

### 5.3 Code Quality & Style

#### 5.3.1 Inconsistent logging strategy

Some modules use `logging.getLogger(__name__)` (standard library), while
`pyproject.toml` declares `loguru` as a core dependency. The project should
standardise on one approach. `loguru` is convenient but adds a dependency;
`logging` is part of the standard library and is what `SynsetHandler` and
`XmlSynsetParser` already use.

#### 5.3.2 `get_all_synsets()` in `SynsetHandler` loads the entire WordNet into memory

```python
return [self._create_synset_data(synset) for synset in wn.all_synsets()]
```

WordNet has ~117 000 synsets. Building relation dicts for all of them
(including cache population) is extremely expensive. Consider returning a
generator or allowing the caller to pass a `batch_size` / limit parameter.

#### 5.3.3 `search_synsets` in `SynsetHandler` duplicates `get_synsets`

Both methods call `wn.synsets(query)` and differ only by the result limit.
One should call the other to avoid duplication.

#### 5.3.4 `TranslationResult` should be a Pydantic model, not a dataclass

`LangGraphTranslationPipeline` already uses Pydantic heavily for stage
schemas. Using `pydantic.BaseModel` for `TranslationResult` would give
automatic validation, serialization, and a JSON schema for free.

#### 5.3.5 `validate_stage_payload` falls back silently on required fields

When Pydantic validation fails, the function fills required string fields
with `""`. Downstream code may not distinguish an LLM failure from a valid
empty-string response. Consider using a sentinel value or raising a structured
exception that callers can catch and log properly.

#### 5.3.6 `_call_llm` unreachable `return call_log`

**Location:** `langgraph_translation_pipeline.py`, line 719.

After the `return` that exits the fallback branch (line 717), there is a
second `return call_log` statement that can never be reached. This is a
copy-paste artefact.

---

### 5.4 Architecture & Design

#### 5.4.1 `pandas` is a core dependency but used only in the GUI

`pandas` is listed under `[project.dependencies]` but is only imported in
`synset_browser.py`. It should be moved to the `[gui]` optional extra,
as it is a large dependency (~30 MB) that headless users do not need.

#### 5.4.2 The DSPy pipeline and the LangGraph pipeline share no abstract base class

Having an abstract `BaseTranslationPipeline` with `translate(synsets)` and
`translate_synset(synset)` methods would allow code that uses any backend
to be written against a stable interface and make backend-swapping trivial.

#### 5.4.3 No retry / back-off strategy for rate limits

`_call_llm` retries on empty/malformed JSON but not on HTTP errors from
the Ollama endpoint (e.g., 429 Too Many Requests, 503 Service Unavailable).
Wrapping the `llm.invoke` call with `tenacity` or a simple exponential
back-off loop would make the pipeline production-ready.

#### 5.4.4 No async support

All pipelines are synchronous. For batch processing of large WordNets (tens of
thousands of synsets), async I/O with `asyncio` + an async LLM client (e.g.,
`langchain`'s `ainvoke`) would deliver a significant throughput improvement.

#### 5.4.5 XML export in `SerbianWordnetPipeline` is not round-trippable with the parser

The exporter writes `<EXAMPLES>/<EXAMPLE>` and `<ILR>/<HYPERNYM>` structures
that do not match the `<USAGE>` and flat `<ILR>` elements expected by
`XmlSynsetParser`. A single canonical XML schema should be used for both
import and export.

#### 5.4.6 Hard-coded Ollama base URL

`base_url = "http://localhost:11434"` is baked into the default constructor.
This should be configurable via an environment variable
(e.g., `OLLAMA_BASE_URL`) or a config file to make the pipeline
container-friendly.

---

### 5.5 Testing

#### 5.5.1 No test for `SerbianWordnetPipeline.generate_serbian_synset` with real DSPy

The pipeline's core generation step is untested beyond the placeholder
behaviour. Adding a test that injects a mock DSPy `LM` would guard against
regressions when the real implementation is added.

#### 5.5.2 `test_synset_handler.py` requires a live NLTK download

Tests like `test_get_synset_by_offset_returns_expected` will fail in a clean
CI environment without a pre-downloaded WordNet corpus. Either:

- Add a `conftest.py` that downloads WordNet once per session using
  `nltk.download('wordnet', quiet=True)`, or
- Mock the NLTK calls in tests that do not intend to exercise the actual
  corpus.

#### 5.5.3 No integration test for the full `SerbianWordnetPipeline.run()` with a mock LLM

The end-to-end XML generation path (`load → generate → judge → export`) is
only tested via `test_import_export.py` at the export level. An integration
test that uses a mock LLM would catch interface mismatches between pipeline
stages.

#### 5.5.4 Test files at repository root should be moved to `tests/`

`test_refactor.py` and `test_schema_validation.py` live in the repository root
rather than in `tests/`. pytest's `testpaths = ["tests"]` setting in
`pyproject.toml` means they are not discovered automatically. Move them to
`tests/` or remove them if they are superseded.

---

### 5.6 Documentation

#### 5.6.1 There are too many top-level markdown files

The repository root contains 12 markdown files (`REFACTORING_SUMMARY.md`,
`GRAPH_VISUALIZATION_README.md`, `GRAPH_VISUALIZATION_SUMMARY.md`,
`GUI_README.md`, `LOG_MANAGEMENT_SUMMARY.md`, `QUICK_REF_LOGS.md`,
`SCHEMA_VALIDATION_INTEGRATION.md`, `TEST_COVERAGE_REPORT.md`,
`WORDNET_SYNSET_ANALYSIS.md`, `XML_FILE_SETUP.md`, `FULL_LOG_ACCESS_GUIDE.md`,
`README.md`). This fragments documentation and makes the repo hard to navigate.
Consolidate related guides under a `docs/` folder or into the main `README.md`
with internal links.

#### 5.6.2 `README.md` project structure table is out of date

The README shows `src/pipelines/`, `src/models/`, etc., without the
`wordnet_autotranslate/` package subdirectory path. The actual layout is
`src/wordnet_autotranslate/pipelines/`, etc.

#### 5.6.3 API reference (Sphinx / MkDocs)

None of the existing markdown documents constitute a formal API reference.
Adding Sphinx with `autodoc` (or `mkdocs` + `mkdocstrings`) would generate
searchable HTML docs from the existing docstrings at no extra authoring cost.

---

### 5.7 Performance

#### 5.7.1 `SynsetHandler._relation_cache` grows unboundedly

The cache dict `_relation_cache` is never evicted. For long-running processes
that call `get_synsets_by_relation` across many different synsets, memory
consumption will grow without bound. Replace with `functools.lru_cache` on
a standalone function, or add a max-size bound.

#### 5.7.2 `XmlSynsetParser._search_cache` has no eviction

Same issue: the search cache `_search_cache` is populated but never pruned.
For interactive use this is fine, but long-running batch jobs that search
with many unique queries will accumulate stale entries.

#### 5.7.3 `get_all_synsets` in `XmlSynsetParser` materialises the full list

```python
return list(self.synsets.values())
```

For very large XML files, returning an iterator (`self.synsets.values()`)
instead of a copy would reduce peak memory use.

---

### 5.8 Security & Dependency Management

#### 5.8.1 `torch` and `transformers` are core dependencies but appear unused

`torch>=2.0.0` and `transformers>=4.30.0` are listed as core dependencies but
are not imported anywhere in the package source. These are extremely large
packages (multi-GB with CUDA). Move them to an optional extra
(e.g., `[models]` or `[dspy]`) or remove them if they are genuinely unused.

#### 5.8.2 No `requirements.txt` / lock file

Users who install from source get unpinned transitive dependencies. Adding a
`requirements.txt` (generated by `pip freeze`) or using `pip-tools` /
`poetry.lock` would make builds reproducible.

#### 5.8.3 LLM prompt injection is not sanitised

User-supplied text (synset definitions, lemmas from the XML) is embedded
directly into prompts. Maliciously crafted content in the XML could alter the
LLM's instructions. Consider wrapping variable content in explicit delimiters
(e.g., triple-backtick fences or XML-style content tags) to reduce
prompt-injection risk.

---

## 6. Priority Roadmap

The improvements above, grouped by effort and impact:

| Priority | Item | Effort | Impact |
|---|---|---|---|
| 🔴 Critical | Fix dead code in `_get_wordnet_domain_info` (§5.1.1) | Low | Medium |
| 🔴 Critical | Replace `print()` with `logging` (§5.1.2, §5.3.1) | Low | Medium |
| 🔴 Critical | Fix `str | Path` type hint for Python 3.8 compat (§5.1.3) | Low | High |
| 🔴 Critical | Move `pandas` / `torch` / `transformers` to optional extras (§5.4.1, §5.8.1) | Low | High |
| 🟠 High | Remove hardcoded `DEBUG_SYNSET_ID` from parser (§5.1.4) | Low | Medium |
| 🟠 High | Implement `generate_serbian_synset` with real LLM (§5.2.2) | High | High |
| 🟠 High | Add `conftest.py` for NLTK data in CI (§5.5.2) | Low | High |
| 🟠 High | Move `test_refactor.py` and `test_schema_validation.py` to `tests/` (§5.5.4) | Low | Medium |
| 🟡 Medium | Abstract base class for pipelines (§5.4.2) | Medium | Medium |
| 🟡 Medium | Retry / back-off for LLM HTTP errors (§5.4.3) | Medium | High |
| 🟡 Medium | Make Ollama URL configurable via env var (§5.4.6) | Low | Medium |
| 🟡 Medium | Consolidate top-level markdown files into `docs/` (§5.6.1) | Medium | Medium |
| 🟡 Medium | Fix XML round-trip incompatibility in `SerbianWordnetPipeline` (§5.4.5) | Medium | High |
| 🟢 Low | Add async support for batch translation (§5.4.4) | High | High |
| 🟢 Low | Add `lru_cache` / bounded cache to `_relation_cache` (§5.7.1) | Low | Low |
| 🟢 Low | Add Sphinx / MkDocs API reference (§5.6.3) | Medium | Medium |
| 🟢 Low | Prompt injection hardening (§5.8.3) | Medium | High |
