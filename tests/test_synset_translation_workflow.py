import pytest
import random
import string

from wordnet_autotranslate.workflows import synset_translation_workflow as workflow_mod
from wordnet_autotranslate.workflows.synset_translation_workflow import (
    WorkflowConfig,
    parse_eng30_id,
    parse_ili_id,
    run_translation_workflow,
    synset_to_payload,
    _resolve_sense_index,
)


class _FakeLemma:
    def __init__(self, name: str):
        self._name = name

    def name(self):
        return self._name


class _FakeSynset:
    def offset(self):
        return 1740

    def pos(self):
        return "n"

    def name(self):
        return "entity.n.01"

    def definition(self):
        return "that which is perceived or known to have its own distinct existence"

    def examples(self):
        return ["The entity is real."]

    def lemmas(self):
        return [_FakeLemma("entity"), _FakeLemma("physical_entity")]


def test_parse_eng30_id_normalizes_adverb_pos():
    offset, pos = parse_eng30_id("ENG30-00001740-b")

    assert offset == 1740
    assert pos == "r"


def test_parse_eng30_id_normalizes_satellite_adjective_pos():
    offset, pos = parse_eng30_id("ENG30-00001740-s")

    assert offset == 1740
    assert pos == "a"


def test_parse_eng30_id_passes_through_adjective_pos():
    offset, pos = parse_eng30_id("ENG30-00001740-a")

    assert offset == 1740
    assert pos == "a"


def test_parse_eng30_id_rejects_malformed_selector():
    with pytest.raises(ValueError, match="parse_eng30_id"):
        parse_eng30_id("BROKEN-1740-x")


def test_parse_ili_id_normalizes_uppercase_input():
    assert parse_ili_id("I35545") == "i35545"


def test_parse_ili_id_rejects_malformed_selector():
    with pytest.raises(ValueError, match="parse_ili_id"):
        parse_ili_id("ENG30-00001740-n")


def test_parse_eng30_id_rejects_invalid_pos_with_clear_message():
    with pytest.raises(ValueError, match="expected one of n,v,a,s,r"):
        parse_eng30_id("ENG30-00001740-x")


def test_parse_eng30_id_rejects_malformed_offset_length():
    with pytest.raises(ValueError, match="exactly 8 digits"):
        parse_eng30_id("ENG30-1740-n")


def test_parse_eng30_id_rejects_malformed_offset_characters():
    with pytest.raises(ValueError, match="exactly 8 digits"):
        parse_eng30_id("ENG30-00A01740-n")


def test_parse_eng30_id_seed_fuzz_corpus():
    valid_selectors = [
        "ENG30-00001740-n",
        "ENG30-00001740-v",
        "ENG30-00001740-a",
        "ENG30-00001740-s",
        "ENG30-00001740-r",
        "ENG30-00001740-b",
    ]
    invalid_selectors = [
        "ENG30-1740-n",
        "ENG30-00A01740-n",
        "BROKEN-00001740-n",
        "ENG30-00001740-x",
        "ENG30--n",
        "ENG30-00001740",
    ]

    for selector in valid_selectors:
        offset, pos = parse_eng30_id(selector)
        assert isinstance(offset, int)
        assert pos in {"n", "v", "a", "r"}

    for selector in invalid_selectors:
        with pytest.raises(ValueError):
            parse_eng30_id(selector)


@pytest.mark.parametrize(
    ("selector", "expected_pos"),
    [
        ("ENG30-00001740-N", "n"),
        ("ENG30-00001740-V", "v"),
        ("ENG30-00001740-A", "a"),
        ("ENG30-00001740-S", "a"),
        ("ENG30-00001740-R", "r"),
        ("ENG30-00001740-B", "r"),
    ],
)
def test_parse_eng30_id_uppercase_pos_inputs(selector, expected_pos):
    offset, pos = parse_eng30_id(selector)
    assert offset == 1740
    assert pos == expected_pos


@pytest.mark.parametrize(
    ("selector", "expected_pos"),
    [
        ("ENG30-00001740-n", "n"),
        ("ENG30-00001740-v", "v"),
        ("ENG30-00001740-a", "a"),
        ("ENG30-00001740-s", "a"),
        ("ENG30-00001740-r", "r"),
        ("ENG30-00001740-b", "r"),
    ],
)
def test_parse_eng30_id_allowed_pos_table(selector, expected_pos):
    offset, pos = parse_eng30_id(selector)
    assert offset == 1740
    assert pos == expected_pos


def test_parse_eng30_id_generated_fuzz_cases():
    rng = random.Random(1337)
    delimiters = ["_", "/", "—", " "]

    invalid_selectors = []
    # Random wrong delimiters, malformed offsets, and invalid POS tokens.
    for _ in range(40):
        delim = rng.choice(delimiters)
        offset_len = rng.choice([1, 2, 3, 4, 5, 6, 7, 9, 10])
        offset = "".join(rng.choice(string.digits) for _ in range(offset_len))
        pos = rng.choice([ch for ch in (string.ascii_letters + "!?") if ch.lower() not in "nvasrb"])
        parts = ["ENG30", offset, pos]
        if rng.random() < 0.5:
            parts.append("extra")
        invalid_selectors.append(delim.join(parts))

    # Unicode/punctuation noise and partial tokens.
    invalid_selectors.extend(
        [
            "ENG30-00001740-ñ",
            "ENG30-００００１７４０-n",  # full-width digits
            "ENG30-00001740-",
            "ENG30-0000174-n",  # short offset
            "ENG30-000017400-n",  # long offset
            "ENG30-0000A740-n",
            "ENG30-💥-n",
            "ENG30-n",
            "ENG30--",
            "ENG3O-00001740-n",  # letter O in prefix
        ]
    )

    for selector in invalid_selectors:
        with pytest.raises(ValueError):
            parse_eng30_id(selector)


def test_synset_to_payload_builds_expected_shape():
    payload = synset_to_payload(_FakeSynset())

    assert payload["id"] == "ENG30-00001740-n"
    assert payload["name"] == "entity.n.01"
    assert payload["lemmas"] == ["entity", "physical entity"]
    assert payload["pos"] == "n"


def test_resolve_wordnet_synset_ili_uses_shared_payload_resolver(monkeypatch):
    monkeypatch.setattr(
        workflow_mod,
        "resolve_ili_to_payload",
        lambda ili: {
            "id": "ENG30-00001740-n",
            "english_id": "ENG30-00001740-n",
            "ili_id": ili,
            "name": "entity.n.01",
            "lemmas": ["entity"],
            "definition": "something that exists",
            "examples": [],
            "pos": "n",
        },
    )

    payload = workflow_mod.resolve_wordnet_synset(ili="i35545")

    assert payload["english_id"] == "ENG30-00001740-n"
    assert payload["ili_id"] == "i35545"


def test_resolve_wordnet_synset_include_relations_enriches_ili_payload(monkeypatch):
    monkeypatch.setattr(
        workflow_mod,
        "resolve_ili_to_payload",
        lambda ili: {"english_id": "ENG30-00001740-n", "ili_id": ili},
    )
    monkeypatch.setattr(
        workflow_mod,
        "enrich_synset_payload",
        lambda payload: {**payload, "hypernyms": [{"name": "thing.n.01"}]},
    )

    payload = workflow_mod.resolve_wordnet_synset(
        ili="i35545",
        include_relations=True,
    )

    assert payload["hypernyms"] == [{"name": "thing.n.01"}]


def test_run_translation_workflow_baseline_runs_for_legacy_dspy_alias(monkeypatch):
    class _FakeBaseline:
        def __init__(self, **kwargs):
            self.source_lang = kwargs["source_lang"]
            self.target_lang = kwargs["target_lang"]

        def translate_synset(self, synset):
            return {
                "translation": "baseline-alias",
                "source_lang": self.source_lang,
                "target_lang": self.target_lang,
            }

    monkeypatch.setattr(workflow_mod, "BaselineTranslationPipeline", _FakeBaseline)

    result = run_translation_workflow(
        {
            "id": "ENG30-00001740-n",
            "lemmas": ["entity"],
            "definition": "something that exists",
            "examples": [],
            "pos": "n",
        },
        pipeline="dspy",
    )

    assert "baseline" in result["pipelines"]
    assert "dspy" in result["pipelines"]
    assert result["pipelines"]["baseline"]["source_lang"] == "en"
    assert result["pipelines"]["baseline"]["target_lang"] == "sr"


def test_run_translation_workflow_baseline_selector(monkeypatch):
    class _FakeBaseline:
        def __init__(self, **kwargs):
            pass

        def translate_synset(self, synset):
            return {"translation": "baseline-only"}

    monkeypatch.setattr(workflow_mod, "BaselineTranslationPipeline", _FakeBaseline)
    result = run_translation_workflow({"id": "ENG30-00001740-n"}, pipeline="baseline")

    assert result["pipelines"]["baseline"]["translation"] == "baseline-only"

def test_run_translation_workflow_rejects_unknown_pipeline():
    with pytest.raises(ValueError, match="Unsupported pipeline"):
        run_translation_workflow({"id": "ENG30-00001740-n"}, pipeline="unknown")


def test_resolve_sense_index_requires_positive_integer():
    with pytest.raises(ValueError, match="sense-index resolution routine"):
        _resolve_sense_index(0, 3)


def test_run_translation_workflow_all_includes_baseline(monkeypatch):
    class _FakeLangGraph:
        def __init__(self, **kwargs):
            pass

        def translate_synset(self, synset):
            return {"translation": "lg"}

    class _FakeConceptual:
        def __init__(self, **kwargs):
            pass

        def translate_synset(self, synset):
            return {"translation": "cg"}

    class _FakeBaseline:
        def __init__(self, **kwargs):
            pass

        def translate_synset(self, synset):
            return {"translation": "base"}

    monkeypatch.setattr(workflow_mod, "BaselineTranslationPipeline", _FakeBaseline)
    monkeypatch.setattr(workflow_mod, "LangGraphTranslationPipeline", _FakeLangGraph)
    monkeypatch.setattr(
        workflow_mod, "ConceptualLangGraphTranslationPipeline", _FakeConceptual
    )

    result = run_translation_workflow({"id": "ENG30-00001740-n"}, pipeline="all")
    assert set(result["pipelines"]) == {"baseline", "langgraph", "conceptual"}


def test_run_translation_workflow_enriches_non_baseline_payload(monkeypatch):
    def _fake_enrich(payload):
        enriched = dict(payload)
        enriched["hypernyms"] = [
            {"id": "ENG30-00001930-n", "lemmas": ["physical entity"]}
        ]
        enriched["meronyms"] = [
            {"id": "ENG30-00002684-n", "lemmas": ["part"]}
        ]
        return enriched

    class _FakeConceptual:
        def __init__(self, **kwargs):
            pass

        def translate_synset(self, synset):
            return {
                "has_hypernyms": bool(synset.get("hypernyms")),
                "has_meronyms": bool(synset.get("meronyms")),
            }

    monkeypatch.setattr(workflow_mod, "enrich_synset_payload", _fake_enrich)
    monkeypatch.setattr(
        workflow_mod, "ConceptualLangGraphTranslationPipeline", _FakeConceptual
    )

    result = run_translation_workflow(
        {"id": "ENG30-00001740-n"}, pipeline="conceptual"
    )

    assert result["source_synset"]["hypernyms"]
    assert result["pipelines"]["conceptual"] == {
        "has_hypernyms": True,
        "has_meronyms": True,
    }


def test_run_translation_workflow_capture_errors_when_non_strict(monkeypatch):
    class _FailingLangGraph:
        def __init__(self, **kwargs):
            pass

        def translate_synset(self, synset):
            raise RuntimeError("llm unavailable")

    monkeypatch.setattr(
        workflow_mod, "LangGraphTranslationPipeline", _FailingLangGraph
    )
    result = run_translation_workflow(
        {"id": "ENG30-00001740-n"},
        pipeline="langgraph",
        config=WorkflowConfig(strict=False),
    )
    assert result["pipelines"]["langgraph"]["status"] == "error"


def test_run_translation_workflow_raises_when_strict(monkeypatch):
    class _FailingLangGraph:
        def __init__(self, **kwargs):
            pass

        def translate_synset(self, synset):
            raise RuntimeError("llm unavailable")

    monkeypatch.setattr(
        workflow_mod, "LangGraphTranslationPipeline", _FailingLangGraph
    )
    with pytest.raises(RuntimeError, match="llm unavailable"):
        run_translation_workflow(
            {"id": "ENG30-00001740-n"},
            pipeline="langgraph",
            config=WorkflowConfig(strict=True),
        )
