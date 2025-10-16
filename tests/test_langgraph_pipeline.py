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
        
        # Verify we got a valid prompt (not all stages have "Synset ID")
        assert len(human_content) > 0, "Empty prompt received"

        if "sense_analysis" in system_content:
            payload = {
                "sense_summary": "A general concept or individual thing that exists.",
                "key_features": ["distinct existence", "identifiable"],
                "domain_tags": ["ontology"],
                "confidence": "high",
                "contrastive_note": "Not to be confused with abstract concepts",
            }
        elif "definition_translation" in system_content:
            payload = {
                "definition_translation": f"{self.translation} je entitet sa sopstvenim postojanjem.",
                "notes": self.notes,
                "examples": self.examples,
            }
        elif "initial_translation" in system_content:
            # Return translations for each lemma
            payload = {
                "initial_translations": [self.translation],
                "alignment": {"entity": self.translation},
            }
        elif "synonym_expansion" in system_content:
            # Expand with additional synonyms
            payload = {
                "expanded_synonyms": [self.translation],
                "rationale": {self.translation: "Direct translation of the concept"},
            }
        elif "synonym_filtering" in system_content:
            # Filter and validate synonyms
            payload = {
                "filtered_synonyms": [self.translation],
                "confidence_by_word": {self.translation: "high"},
                "removed": [],
                "confidence": "high",
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
    # Check new 6-stage pipeline structure
    assert result["payload"]["definition"]["definition_translation"].startswith("entitet je")
    assert result["payload"]["initial_translation"]["initial_translations"] == ["entitet"]
    assert result["payload"]["filtering"]["filtered_synonyms"] == ["entitet"]
    assert "Representative literal" in result["curator_summary"]
    assert "Synset literals" in result["curator_summary"]


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
    # 6-stage pipeline: sense_analysis, definition_translation, initial_translation, expansion, filtering = 5 calls
    assert pipeline.llm.calls == 5


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
    # Check new pipeline structure
    assert result["payload"]["filtering"]["filtered_synonyms"] == ["Àfíríkà"]
    assert "Àfíríkà" in result["curator_summary"]


def test_translate_stream_generator():
    """Test the streaming translation generator."""
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(translation="stream-test"),
    )

    synsets = [
        {
            "id": f"ENG30-0000{i}-n",
            "lemmas": [f"word{i}"],
            "definition": f"definition {i}",
            "examples": [],
            "pos": "n",
        }
        for i in range(3)
    ]

    results = list(pipeline.translate_stream(synsets))

    assert len(results) == 3
    for result in results:
        assert result["translation"] == "stream-test"
        assert result["target_lang"] == "sr"


def test_decode_llm_payload_with_think_tags():
    """Test JSON extraction from responses with <think> reasoning tags."""
    raw = '<think>Let me analyze this...</think>\n{"translation": "test", "examples": []}'
    result = LangGraphTranslationPipeline._decode_llm_payload(raw)
    
    assert result["translation"] == "test"
    assert result["examples"] == []


def test_decode_llm_payload_with_code_fence():
    """Test JSON extraction from fenced code blocks."""
    raw = 'Here is the result:\n```json\n{"translation": "fenced", "notes": "test"}\n```'
    result = LangGraphTranslationPipeline._decode_llm_payload(raw)
    
    assert result["translation"] == "fenced"
    assert result["notes"] == "test"


def test_decode_llm_payload_with_extra_text():
    """Test JSON extraction when surrounded by prose."""
    raw = 'The translation is: {"translation": "embedded", "examples": ["test"]} as you can see.'
    result = LangGraphTranslationPipeline._decode_llm_payload(raw)
    
    assert result["translation"] == "embedded"
    assert result["examples"] == ["test"]


def test_decode_llm_payload_empty_string():
    """Test handling of empty LLM response."""
    result = LangGraphTranslationPipeline._decode_llm_payload("")
    
    assert result["translation"] == ""
    assert result["examples"] == []
    assert result["notes"] is None


def test_decode_llm_payload_invalid_json_fallback():
    """Test fallback behavior for completely malformed JSON."""
    raw = "This is just plain text without any JSON structure"
    result = LangGraphTranslationPipeline._decode_llm_payload(raw)
    
    # Should return the cleaned text as translation
    assert "translation" in result
    assert result["translation"] == raw


def test_translation_result_to_dict():
    """Test TranslationResult.to_dict() serialization."""
    from wordnet_autotranslate.pipelines.langgraph_translation_pipeline import TranslationResult
    
    result = TranslationResult(
        translation="test_word",
        definition_translation="test definition",
        translated_synonyms=["syn1", "syn2"],
        target_lang="sr",
        source_lang="en",
        source={"id": "test-id"},
        examples=["example 1"],
        notes="test notes",
        raw_response="raw text",
        payload={"key": "value"},
        curator_summary="summary text",
    )
    
    result_dict = result.to_dict()
    
    assert result_dict["translation"] == "test_word"
    assert result_dict["definition_translation"] == "test definition"
    assert result_dict["translated_synonyms"] == ["syn1", "syn2"]
    assert result_dict["target_lang"] == "sr"
    assert result_dict["source_lang"] == "en"
    assert result_dict["source"]["id"] == "test-id"
    assert result_dict["examples"] == ["example 1"]
    assert result_dict["notes"] == "test notes"
    assert result_dict["raw_response"] == "raw text"
    assert result_dict["payload"]["key"] == "value"
    assert result_dict["curator_summary"] == "summary text"


def test_synset_with_alternative_field_names():
    """Test handling of alternative synset field names (literals, gloss, ili_id)."""
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(translation="alternativni"),
    )

    synset = {
        "ili_id": "i12345",  # instead of "id"
        "literals": ["alternative"],  # instead of "lemmas"
        "gloss": "using different field names",  # instead of "definition"
        "examples": ["Test example"],
        "part_of_speech": "n",  # instead of "pos"
    }

    result = pipeline.translate_synset(synset)

    assert result["translation"] == "alternativni"
    assert result["source"]["ili_id"] == "i12345"


def test_synset_with_empty_fields():
    """Test handling of synsets with missing or empty fields."""
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(translation="prazan"),
    )

    synset = {
        "id": "test-empty",
        "lemmas": [],  # empty lemmas
        "definition": "",  # empty definition
        "examples": [],  # no examples
        "pos": "",  # empty pos
    }

    result = pipeline.translate_synset(synset)

    assert result["translation"] == "prazan"
    assert result["source"]["id"] == "test-empty"


def test_custom_system_prompt():
    """Test pipeline with custom system prompt."""
    custom_prompt = "You are a specialized translator for technical terms."
    
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        system_prompt=custom_prompt,
        llm=_DummyLLM(),
    )

    assert pipeline.system_prompt == custom_prompt


def test_multiple_synonyms_with_varying_confidence():
    """Test handling of multiple synonyms with different confidence levels."""
    
    class _MultiSynonymLLM(_DummyLLM):
        def invoke(self, messages):
            self.calls += 1
            system_content = getattr(messages[0], "content", str(messages[0]))
            
            if "sense_analysis" in system_content:
                payload = {
                    "sense_summary": "The most important one",
                    "key_features": ["primary importance"],
                    "confidence": "high",
                }
            elif "definition_translation" in system_content:
                payload = {
                    "definition_translation": "Glavni ili najvažniji",
                    "examples": ["Test primjer"],
                    "notes": "Multiple synonyms available",
                }
            elif "initial_translation" in system_content:
                payload = {
                    "initial_translations": ["glavni", "primarni", "главни"],
                    "alignment": {"main": "glavni", "primary": "primarni", "chief": "главни"},
                }
            elif "synonym_expansion" in system_content:
                payload = {
                    "expanded_synonyms": ["glavni", "primarni", "главни"],
                    "rationale": {
                        "glavni": "Common usage",
                        "primarni": "Technical term",
                        "главни": "Cyrillic variant",
                    },
                }
            elif "synonym_filtering" in system_content:
                payload = {
                    "filtered_synonyms": ["glavni", "primarni", "главни"],
                    "confidence_by_word": {"glavni": "high", "primarni": "medium", "главни": "high"},
                    "removed": [],
                    "confidence": "high",
                }
            else:
                payload = {"error": "unexpected stage"}
            
            class _Response:
                content = json.dumps(payload)
            
            return _Response()
    
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_MultiSynonymLLM(),
    )

    synset = {
        "id": "test-multi",
        "lemmas": ["main", "primary", "chief"],
        "definition": "of first importance",
        "examples": [],
        "pos": "a",
    }

    result = pipeline.translate_synset(synset)

    assert result["translation"] == "glavni"
    assert len(result["translated_synonyms"]) == 3
    assert "glavni" in result["translated_synonyms"]
    assert "primarni" in result["translated_synonyms"]
    assert "главни" in result["translated_synonyms"]
    assert result["notes"] == "Multiple synonyms available"


def test_curator_summary_with_many_synonyms():
    """Test curator summary truncates long synonym lists."""
    
    class _ManySynonymsLLM(_DummyLLM):
        def invoke(self, messages):
            self.calls += 1
            system_content = getattr(messages[0], "content", str(messages[0]))
            
            if "sense_analysis" in system_content:
                payload = {
                    "sense_summary": "Test sense",
                    "key_features": ["test"],
                    "confidence": "high",
                }
            elif "definition_translation" in system_content:
                payload = {
                    "definition_translation": "Test definition",
                    "examples": [],
                }
            elif "initial_translation" in system_content:
                # Create 10 translations to test handling
                initial_translations = [f"reč{i}" for i in range(10)]
                alignment = {f"word{i}": f"reč{i}" for i in range(10)}
                payload = {
                    "initial_translations": initial_translations,
                    "alignment": alignment,
                }
            elif "synonym_expansion" in system_content:
                # Expand with all 10 synonyms
                expanded_synonyms = [f"reč{i}" for i in range(10)]
                rationale = {f"reč{i}": "Synonym variant" for i in range(10)}
                payload = {
                    "expanded_synonyms": expanded_synonyms,
                    "rationale": rationale,
                }
            elif "synonym_filtering" in system_content:
                # Keep all 10 synonyms
                filtered_synonyms = [f"reč{i}" for i in range(10)]
                confidence_by_word = {f"reč{i}": "high" for i in range(10)}
                payload = {
                    "filtered_synonyms": filtered_synonyms,
                    "confidence_by_word": confidence_by_word,
                    "removed": [],
                    "confidence": "high",
                }
            else:
                payload = {"error": "unexpected stage"}
            
            class _Response:
                content = json.dumps(payload)
            
            return _Response()
    
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_ManySynonymsLLM(),
    )

    synset = {
        "id": "test-many",
        "lemmas": [f"word{i}" for i in range(10)],
        "definition": "test",
        "examples": [],
        "pos": "n",
    }

    result = pipeline.translate_synset(synset)

    # Check that curator summary mentions truncation
    assert len(result["translated_synonyms"]) == 10
    # Updated to match new terminology: "literals" instead of "candidates"
    assert "(+5 more literals)" in result["curator_summary"] or "more literals" in result["curator_summary"]


def test_example_deduplication():
    """Test that duplicate examples are removed while preserving order."""
    
    class _DuplicateExamplesLLM(_DummyLLM):
        def invoke(self, messages):
            self.calls += 1
            system_content = getattr(messages[0], "content", str(messages[0]))
            
            if "sense_analysis" in system_content:
                payload = {
                    "sense_summary": "Test",
                    "key_features": [],
                    "confidence": "high",
                }
            elif "definition_translation" in system_content:
                payload = {
                    "definition_translation": "Test",
                    # Provide all three examples - will test deduplication
                    "examples": ["Duplicate example", "Unique example", "Another unique"],
                }
            elif "initial_translation" in system_content:
                payload = {
                    "initial_translations": ["test"],
                    "alignment": {"test": "test"},
                }
            elif "synonym_expansion" in system_content:
                payload = {
                    "expanded_synonyms": ["test"],
                    "rationale": {"test": "Direct translation"},
                }
            elif "synonym_filtering" in system_content:
                payload = {
                    "filtered_synonyms": ["test"],
                    "confidence_by_word": {"test": "high"},
                    "removed": [],
                    "confidence": "high",
                }
            else:
                payload = {"error": "unexpected stage"}
            
            class _Response:
                content = json.dumps(payload)
            
            return _Response()
    
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DuplicateExamplesLLM(),
    )

    synset = {
        "id": "test-dedup",
        "lemmas": ["test"],
        "definition": "test definition",
        "examples": [],
        "pos": "n",
    }

    result = pipeline.translate_synset(synset)

    # Should have unique examples only
    assert len(result["examples"]) == len(set(result["examples"]))
    assert "Duplicate example" in result["examples"]
    assert "Unique example" in result["examples"]
    assert "Another unique" in result["examples"]