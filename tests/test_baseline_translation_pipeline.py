from wordnet_autotranslate.pipelines.translation_pipeline import BaselineTranslationPipeline


class _ExplodingLLM:
    def invoke(self, _prompt):
        raise ConnectionError("backend unavailable")


def test_baseline_pipeline_falls_back_when_llm_invoke_fails():
    pipeline = BaselineTranslationPipeline(llm=_ExplodingLLM())
    synset = {
        "id": "ENG30-00001740-n",
        "name": "entity.n.01",
        "pos": "n",
        "lemmas": ["entity"],
        "definition": "that which is perceived to exist",
    }

    result = pipeline.translate_synset(synset)

    assert result["translation"] == "entity"
    assert result["definition_translation"] == "that which is perceived to exist"
    assert result["translated_synonyms"] == ["entity"]
    notes = result["payload"]["baseline"]["notes"]
    assert "LLM invocation failed" in notes
