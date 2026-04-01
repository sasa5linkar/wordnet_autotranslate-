import pytest

from wordnet_autotranslate.workflows import synset_translation_workflow as workflow_mod
from wordnet_autotranslate.workflows.synset_translation_workflow import (
    WorkflowConfig,
    parse_eng30_id,
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


def test_parse_eng30_id_rejects_malformed_selector():
    with pytest.raises(ValueError, match="parse_eng30_id"):
        parse_eng30_id("BROKEN-1740-x")


def test_parse_eng30_id_rejects_invalid_pos_with_clear_message():
    with pytest.raises(ValueError, match="expected one of n,v,a,s,r"):
        parse_eng30_id("ENG30-00001740-x")


def test_synset_to_payload_builds_expected_shape():
    payload = synset_to_payload(_FakeSynset())

    assert payload["id"] == "ENG30-00001740-n"
    assert payload["name"] == "entity.n.01"
    assert payload["lemmas"] == ["entity", "physical entity"]
    assert payload["pos"] == "n"


def test_run_translation_workflow_dspy_reports_not_implemented():
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

    assert "dspy" in result["pipelines"]
    assert result["pipelines"]["dspy"]["status"] == "not_implemented"


def test_run_translation_workflow_rejects_unknown_pipeline():
    with pytest.raises(ValueError, match="Unsupported pipeline"):
        run_translation_workflow({"id": "ENG30-00001740-n"}, pipeline="unknown")


def test_resolve_sense_index_requires_positive_integer():
    with pytest.raises(ValueError, match="sense-index resolution routine"):
        _resolve_sense_index(0, 3)


def test_run_translation_workflow_all_includes_dspy(monkeypatch):
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

    monkeypatch.setattr(workflow_mod, "LangGraphTranslationPipeline", _FakeLangGraph)
    monkeypatch.setattr(
        workflow_mod, "ConceptualLangGraphTranslationPipeline", _FakeConceptual
    )

    result = run_translation_workflow({"id": "ENG30-00001740-n"}, pipeline="all")
    assert set(result["pipelines"]) == {"langgraph", "conceptual", "dspy"}


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
