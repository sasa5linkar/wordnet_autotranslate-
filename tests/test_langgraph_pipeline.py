import json
from typing import List, Optional

import pytest

pytest.importorskip("langgraph")
pytest.importorskip("langchain_core.messages")

from wordnet_autotranslate.pipelines.langgraph_translation_pipeline import (
    LangGraphTranslationPipeline,
)


class _DummyLLM:
    """Minimal stand-in for ChatOllama used in tests."""

    def __init__(
        self,
        translation: str = "entitet",
        examples: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> None:
        self.calls = 0
        self.translation = translation
        self.examples = examples if examples is not None else ["Ovo je entitet."]
        self.notes = notes

    def invoke(self, messages):  # pragma: no cover - verified with assertions
        self.calls += 1
        system_message = messages[0]
        human_message = messages[-1]
        system_content = getattr(system_message, "content", str(system_message))
        human_content = getattr(human_message, "content", str(human_message))
        assert "Synset ID" in human_content

        if "sense_analysis" in system_content:
            payload = {
                "sense_summary": "A general concept or individual thing that exists.",
                "key_features": ["distinct existence", "identifiable"],
                "domain_tags": ["ontology"],
                "confidence": "high",
                "recommended_translation": self.translation,
            }
        elif "definition_translation" in system_content:
            payload = {
                "definition_translation": f"{self.translation} je entitet sa sopstvenim postojanjem.",
                "notes": self.notes,
                "examples": self.examples,
            }
        elif "synonym_translation" in system_content:
            payload = {
                "preferred_headword": self.translation,
                "synonyms": [
                    {
                        "original": "entity",
                        "translation": self.translation,
                        "confidence": "high",
                        "example": self.examples[0] if self.examples else None,
                    }
                ],
                "examples": self.examples,
                "notes": self.notes,
            }
        else:  # fallback for unexpected prompts
            payload = {
                "translation": self.translation,
                "examples": self.examples,
                "notes": self.notes,
            }

        class _Response:
            content = json.dumps(payload)

        return _Response()


def test_langgraph_pipeline_returns_structured_dict():
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(),
    )

    synset = {
        "id": "ENG30-00001740-r",
        "lemmas": ["entity"],
        "definition": "that which is perceived or known to have its own distinct existence",
        "examples": ["The entity known as Bigfoot has not been captured."],
        "pos": "r",
    }

    result = pipeline.translate_synset(synset)

    assert result["translation"] == "entitet"
    assert result["definition_translation"].startswith("entitet je")
    assert result["translated_synonyms"] == ["entitet"]
    assert result["target_lang"] == "sr"
    assert result["source"]["id"] == synset["id"]
    assert result["examples"] == ["Ovo je entitet."]
    assert result["payload"]["definition"]["definition_translation"].startswith("entitet je")
    assert result["payload"]["synonyms"]["preferred_headword"] == "entitet"
    assert "Headword" in result["curator_summary"]
    assert "Synonym candidates" in result["curator_summary"]


def test_langgraph_pipeline_batch_processing():
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(translation="entitet-2"),
    )

    synsets = [
        {
            "id": "ENG30-00001740-r",
            "lemmas": ["entity"],
            "definition": "something that exists",
            "examples": [],
            "pos": "b",  # Serbian tag should still be handled
        }
    ]

    translated = pipeline.translate(synsets)

    assert len(translated) == 1
    assert translated[0]["translation"] == "entitet-2"
    assert pipeline.llm.calls == 3


def test_langgraph_pipeline_african_synset_example():
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="yo",
        llm=_DummyLLM(
            translation="Àfíríkà",
            examples=["Àfíríkà ní ọ̀pọ̀ àṣà àti akọ́le ilẹ̀."],
            notes="Transliteration with tonal marks.",
        ),
    )

    synset = {
        "id": "ENG30-08412345-n",
        "lemmas": ["Africa"],
        "definition": "the second largest continent",
        "examples": ["Africa spans diverse cultures."],
        "pos": "n",
    }

    result = pipeline.translate_synset(synset)

    assert result["translation"] == "Àfíríkà"
    assert result["target_lang"] == "yo"
    assert result["examples"] == ["Àfíríkà ní ọ̀pọ̀ àṣà àti akọ́le ilẹ̀."]
    assert result["notes"] == "Transliteration with tonal marks."
    assert result["definition_translation"].startswith("Àfíríkà")
    assert result["translated_synonyms"] == ["Àfíríkà"]
    assert result["payload"]["synonyms"]["preferred_headword"] == "Àfíríkà"
    assert "Àfíríkà" in result["curator_summary"]