import pytest

from wordnet_autotranslate.workflows.synset_translation_workflow import (
    parse_eng30_id,
    run_translation_workflow,
    synset_to_payload,
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
