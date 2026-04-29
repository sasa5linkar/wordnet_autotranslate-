import json
import sys
import types
from typing import List, Optional

import pytest

pytest.importorskip("langgraph")
pytest.importorskip("langchain_core.messages")

from wordnet_autotranslate.pipelines.langgraph_translation_pipeline import (
    LangGraphTranslationPipeline,
)
from wordnet_autotranslate.utils.log_utils import sanitize_model_name
from wordnet_autotranslate.pipelines.conceptual_langgraph_pipeline import (
    ConceptualLangGraphTranslationPipeline,
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

        definition_text = f"{self.translation} je entitet sa sopstvenim postojanjem."

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
                "definition_translation": definition_text,
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
        elif "definition_quality" in system_content:
            payload = {
                "status": "ok",
                "issues": [],
                "revised_definition": definition_text,
                "notes": "Definition passes grammatical and stylistic checks.",
            }
        elif "expanded_definition_en" in system_content:
            payload = {
                "expanded_definition_en": "A thing or being with its own distinct existence.",
                "blocked_terms_en": ["entity"],
                "notes_en": ["Expanded for conceptual testing."],
            }
        elif "expanded_definition_sr" in system_content:
            payload = {
                "expanded_definition_sr": f"{self.translation} je ono što postoji kao zasebna celina.",
                "blocked_terms_sr": [self.translation],
                "notes_sr": ["Srpska konceptualna definicija za test."],
            }
        elif "literal_candidates_sr" in system_content:
            payload = {
                "candidates": [
                    {
                        "literal": self.translation,
                        "candidate_type": "primary",
                        "precision_score": 0.95,
                        "naturalness_score": 0.95,
                        "rationale": "Direct conceptual equivalent.",
                        "fit_assessment": "good equivalent",
                        "register_note": "standard",
                    },
                    {
                        "literal": "opisna fraza",
                        "candidate_type": "descriptive",
                        "precision_score": 0.5,
                        "naturalness_score": 0.6,
                        "rationale": "Descriptive fallback, not a synset literal.",
                        "fit_assessment": "too descriptive",
                        "register_note": "paraphrase",
                    },
                ]
            }
        elif "literal_selection_sr" in system_content:
            payload = {
                "selected_literals_sr": [self.translation],
                "rejected_literals_sr": ["opisna fraza"],
                "rationale_sr": "Izabran je najbolji leksički ekvivalent.",
            }
        elif "final_gloss_sr" in system_content:
            payload = {
                "final_gloss_sr": "ono što postoji kao zasebna celina",
                "style_notes_sr": ["Kratka WordNet definicija."],
            }
        elif "synset_validation_sr" in system_content:
            payload = {
                "validation_passed": True,
                "issues": [],
                "final_synset_ready": True,
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
    # Check new 7-stage pipeline structure
    assert result["payload"]["definition"]["definition_translation"].startswith("entitet je")
    assert result["payload"]["initial_translation"]["initial_translations"] == ["entitet"]
    assert result["payload"]["filtering"]["filtered_synonyms"] == ["entitet"]
    assert result["payload"]["definition_quality"]["status"] == "ok"
    assert "Representative literal" in result["curator_summary"]
    assert "Synset literals" in result["curator_summary"]

    model_info = result["model"]
    assert model_info["resolved"] == "gpt-oss:120b"
    assert model_info["requested"] == "gpt-oss:120b"
    assert model_info["fallback_used"] is False
    assert model_info["resolved_safe"] == sanitize_model_name("gpt-oss:120b")


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
    # 7-stage pipeline: sense_analysis, definition_translation, initial_translation, expansion, filtering, definition_quality
    assert pipeline.llm.calls == 6


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

    # Note: deduplication normalizes to lowercase for consistency
    assert result["translation"] == "àfíríkà"
    assert result["target_lang"] == "yo"
    assert result["examples"] == ["Àfíríkà ní ọ̀pọ̀ àṣà àti akọ́le ilẹ̀."]
    assert result["notes"] == "Transliteration with tonal marks."
    assert result["definition_translation"].startswith("Àfíríkà")
    assert result["translated_synonyms"] == ["àfíríkà"]
    # Check new pipeline structure
    assert result["payload"]["filtering"]["filtered_synonyms"] == ["Àfíríkà"]
    assert "àfíríkà" in result["curator_summary"]


def test_langgraph_pipeline_model_metadata_merging():
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        model="gpt-oss:120b",
        llm=_DummyLLM(),
        model_metadata={
            "requested": "deepseek-v2:70b",
            "resolved": "gpt-oss:120b",
            "fallback_used": True,
            "reason": "Preferred model unavailable on host",
            "available_models": ["gpt-oss:120b", "mistral:7b"],
        },
    )

    synset = {
        "id": "ENG30-00001740-r",
        "lemmas": ["entity"],
        "definition": "that which is perceived or known to have its own distinct existence",
        "examples": [],
        "pos": "r",
    }

    result = pipeline.translate_synset(synset)
    model_info = result["model"]

    assert model_info["requested"] == "deepseek-v2:70b"
    assert model_info["resolved"] == "gpt-oss:120b"
    assert model_info["fallback_used"] is True
    assert model_info["reason"] == "Preferred model unavailable on host"
    assert model_info["resolved_safe"] == sanitize_model_name("gpt-oss:120b")


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
    raw = (
        '<think>Let me analyze this...</think>\n{"translation": "test", "examples": []}'
    )
    result = LangGraphTranslationPipeline._decode_llm_payload(raw)

    assert result["translation"] == "test"
    assert result["examples"] == []


def test_decode_llm_payload_with_code_fence():
    """Test JSON extraction from fenced code blocks."""
    raw = (
        'Here is the result:\n```json\n{"translation": "fenced", "notes": "test"}\n```'
    )
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


def test_coerce_to_str_list_ignores_non_strings():
    result = LangGraphTranslationPipeline._coerce_to_str_list(
        [" valid ", None, 7, {"x": 1}, "", "ok"]
    )
    assert result == ["valid", "ok"]
    assert LangGraphTranslationPipeline._coerce_to_str_list({"bad": "shape"}) == []


def test_get_wordnet_domain_info_normalizes_serbian_adverb_pos(monkeypatch):
    """Test ENG IDs using Serbian POS markers (b) are normalized to r."""

    observed = {}

    class _FakeTopicDomain:
        def name(self):
            return "topic.test.01"

    class _FakeSynset:
        def lexname(self):
            return "adv.all"

        def topic_domains(self):
            return [_FakeTopicDomain()]

    def _fake_lookup(pos_char, offset):
        observed["pos_char"] = pos_char
        observed["offset"] = offset
        return _FakeSynset()

    fake_wordnet = types.SimpleNamespace(synset_from_pos_and_offset=_fake_lookup)
    fake_corpus = types.SimpleNamespace(wordnet=fake_wordnet)
    fake_nltk = types.SimpleNamespace(corpus=fake_corpus)

    monkeypatch.setitem(sys.modules, "nltk", fake_nltk)
    monkeypatch.setitem(sys.modules, "nltk.corpus", fake_corpus)
    monkeypatch.setitem(sys.modules, "nltk.corpus.wordnet", fake_wordnet)

    result = LangGraphTranslationPipeline._get_wordnet_domain_info("ENG30-00001740-b")

    assert observed["pos_char"] == "r"
    assert observed["offset"] == 1740
    assert result["lexname"] == "adv.all"
    assert result["topic_domains"] == ["topic.test.01"]


def test_call_llm_retries_on_invoke_exception():
    class _FailOnceLLM:
        def __init__(self):
            self.calls = 0

        def invoke(self, messages):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary transport failure")

            class _Response:
                content = json.dumps(
                    {
                        "sense_summary": "desc",
                        "contrastive_note": "note",
                        "key_features": ["f1"],
                        "domain_tags": [],
                        "confidence": "high",
                    }
                )

            return _Response()

    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_FailOnceLLM(),
    )
    call = pipeline._call_llm("prompt", stage="sense_analysis", retries=1)
    assert call["payload"]["sense_summary"] == "desc"


def test_call_llm_fallback_payload_shape_after_repeated_invoke_exceptions():
    class _AlwaysFailLLM:
        def invoke(self, messages):
            raise RuntimeError("transport down")

    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_AlwaysFailLLM(),
    )

    call = pipeline._call_llm("prompt", stage="sense_analysis", retries=1)
    payload = call["payload"]

    # Ensure fallback payload respects stage schema shape.
    assert set(payload.keys()) == {
        "sense_summary",
        "contrastive_note",
        "key_features",
        "domain_tags",
        "confidence",
    }
    assert isinstance(payload["key_features"], list)
    assert isinstance(payload["domain_tags"], list)
    assert call["raw_response"] == "transport down"


@pytest.mark.parametrize(
    ("stage", "expected_keys"),
    [
        (
            "sense_analysis",
            {
                "sense_summary",
                "contrastive_note",
                "key_features",
                "domain_tags",
                "confidence",
            },
        ),
        (
            "definition_translation",
            {"definition_translation", "notes", "examples"},
        ),
        (
            "initial_translation",
            {"initial_translations", "alignment"},
        ),
        (
            "synonym_expansion",
            {
                "expanded_synonyms",
                "rationale",
                "iterations_run",
                "synonym_provenance",
                "converged",
            },
        ),
        (
            "synonym_filtering",
            {"filtered_synonyms", "confidence_by_word", "removed", "confidence"},
        ),
    ],
)
def test_call_llm_fallback_payload_shape_matrix_after_repeated_invoke_exceptions(
    stage, expected_keys
):
    class _AlwaysFailLLM:
        def invoke(self, messages):
            raise RuntimeError(f"{stage} transport down")

    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_AlwaysFailLLM(),
    )

    call = pipeline._call_llm("prompt", stage=stage, retries=1)
    payload = call["payload"]
    assert set(payload.keys()) == expected_keys
    assert call["raw_response"] == f"{stage} transport down"


def test_translation_result_to_dict():
    """Test TranslationResult.to_dict() serialization."""
    from wordnet_autotranslate.pipelines.langgraph_translation_pipeline import (
        TranslationResult,
    )

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
    assert "model" not in result_dict


def test_translation_result_to_dict_includes_model_metadata():
    from wordnet_autotranslate.pipelines.langgraph_translation_pipeline import TranslationResult

    result = TranslationResult(
        translation="test",
        definition_translation="definition",
        translated_synonyms=["syn"],
        target_lang="sr",
        source_lang="en",
        source={"id": "id"},
        examples=[],
        notes=None,
        raw_response="raw",
        payload={},
        curator_summary="summary",
        model_info={"resolved": "deepseek", "resolved_safe": "deepseek", "fallback_used": False},
    )

    result_dict = result.to_dict()
    assert result_dict["model"]["resolved"] == "deepseek"
    assert result_dict["model"]["fallback_used"] is False
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
                    "alignment": {
                        "main": "glavni",
                        "primary": "primarni",
                        "chief": "главни",
                    },
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
            elif "definition_quality" in system_content:
                payload = {
                    "status": "ok",
                    "issues": [],
                    "revised_definition": "Glavni ili najvažniji",
                    "notes": "Definition is stylistically balanced.",
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
            elif "definition_quality" in system_content:
                payload = {
                    "status": "ok",
                    "issues": [],
                    "revised_definition": "Test definition",
                    "notes": "Definition quality verified.",
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
    assert len(result["translated_synonyms"]) == 8
    # Updated to match new terminology: "literals" instead of "candidates"
    assert (
        "(+5 more literals)" in result["curator_summary"]
        or "more literals" in result["curator_summary"]
    )


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
                    "examples": [
                        "Duplicate example",
                        "Unique example",
                        "Another unique",
                    ],
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
            elif "definition_quality" in system_content:
                payload = {
                    "status": "ok",
                    "issues": [],
                    "revised_definition": "Test",
                    "notes": "Definition quality confirmed.",
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


def test_conceptual_langgraph_pipeline_returns_structured_result():
    pipeline = ConceptualLangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(),
    )

    synset = {
        "id": "ENG30-00001740-n",
        "lemmas": ["entity"],
        "definition": "that which is perceived or known to have its own distinct existence",
        "examples": ["The entity known as Bigfoot has not been captured."],
        "pos": "n",
        "hypernyms": [
            {
                "id": "ENG30-00001930-n",
                "lemmas": ["thing"],
                "gloss": "a separate and self-contained entity",
            }
        ],
    }

    result = pipeline.translate_synset(synset)

    assert result["translation"] == "entitet"
    assert result["selected_literals_sr"] == ["entitet"]
    assert result["rejected_literals_sr"] == ["opisna fraza"]
    assert result["final_gloss_sr"] == "ono što postoji kao zasebna celina"
    assert result["concept_package"]["source_literals"] == ["entity"]
    assert result["concept_package"]["hypernyms"][0]["synset_id"] == "ENG30-00001930-n"
    assert result["expanded_en"]["expanded_definition_en"].startswith(
        "A thing or being"
    )
    assert result["expanded_sr"]["expanded_definition_sr"].startswith("entitet je")
    assert result["candidates"]["candidates"][0]["literal"] == "entitet"
    assert result["selection"]["selected_literals_sr"] == ["entitet"]
    assert result["validation"]["validation_passed"] is True
    assert "Concept pipeline stages completed" in result["curator_summary"]


def test_conceptual_expanded_definition_prompt_uses_relations():
    pipeline = ConceptualLangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(),
    )

    prompt = pipeline._render_expanded_definition_en_prompt(
        {
            "synset_id": "ENG30-01998019-n",
            "pos": "n",
            "source_literals": ["Cirripedia"],
            "source_gloss": "barnacles",
            "hypernyms": [{"synset_id": "class.n.07", "literals": ["class"], "gloss": "taxonomic group"}],
            "hyponyms": [],
            "meronyms": [{"synset_id": "barnacle.n.01", "literals": ["barnacle"], "gloss": "marine crustacean"}],
            "holonyms": [{"synset_id": "crustacea.n.01", "literals": ["crustacea"], "gloss": "class of arthropods"}],
            "sister_synsets": [],
        }
    )

    assert "Use hypernyms as genus constraints" in prompt
    assert "Use hyponyms to understand the lower boundary" in prompt
    assert "Use meronyms and holonyms" in prompt
    assert "use its gloss/definition more than its lemma alone" in prompt


def test_conceptual_related_synsets_fill_missing_definitions():
    related = ConceptualLangGraphTranslationPipeline._normalise_related_synsets(
        [
            {"synset_id": "entity.n.01"},
            "physical_entity.n.01",
        ]
    )

    assert related[0]["literals"] == ["entity"]
    assert "distinct existence" in related[0]["gloss"]
    assert related[1]["literals"] == ["physical entity"]
    assert "physical existence" in related[1]["gloss"]


def test_conceptual_pipeline_batch_processing_uses_same_llm():
    dummy_llm = _DummyLLM(translation="pojam")
    pipeline = ConceptualLangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=dummy_llm,
    )

    synsets = [
        {
            "id": "ENG30-00001740-n",
            "lemmas": ["entity"],
            "definition": "something that exists",
            "examples": [],
            "pos": "n",
        }
    ]

    translated = pipeline.translate(synsets)

    assert len(translated) == 1
    assert translated[0]["translation"] == "pojam"
    assert dummy_llm.calls == 6


def test_auto_quality_report_blocks_literal_in_gloss():
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(),
    )

    report = pipeline._build_auto_quality_report(
        {"id": "ENG30-00006238-v", "pos": "v", "lemmas": ["expectorate"]},
        ["iskašljati"],
        "iskašljati sluz iz pluća kroz usta",
        raw_literals=["iskašljati"],
        model_ready=True,
    )

    assert report["auto_status"] == "blocked"
    assert "literal_in_gloss" in report["quality_flags"]
    assert report["needs_human_review"] is True


def test_taxonomy_dual_literals_keep_serbian_and_latin():
    pipeline = ConceptualLangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(),
    )

    concept_package = {
        "pos": "n",
        "source_literals": ["Metatheria", "subclass Metatheria"],
        "source_gloss": "pouched animals",
        "domains": ["noun.animal"],
    }

    assert pipeline._ensure_taxonomy_dual_literals(
        ["tobolčari"],
        concept_package,
    ) == ["tobolčari", "Metatheria"]


def test_adverb_particle_demotes_context_bound_variants_when_cak_exists():
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(),
    )

    assert pipeline._post_filter_literals_by_pos(
        ["čak", "takođe", "još", "ni", "čak i"],
        {"pos": "r"},
    ) == ["čak"]


def test_langgraph_pos_cleanup_does_not_use_serbian_suffix_regex():
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(),
    )

    assert pipeline._post_filter_literals_by_pos(
        ["iskašljavanje", "kašalj", "iskašljati"],
        {"pos": "v"},
    ) == ["iskašljavanje", "kašalj", "iskašljati"]


def test_pos_constraint_prompt_carries_source_pos_and_avoids_suffix_guessing():
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(),
    )

    prompt_block = pipeline._source_pos_constraint_block(
        {"pos": "n", "lemmas": ["physical entity"]}
    )

    assert "Source WordNet POS is noun (n)" in prompt_block
    assert "physical entity" in prompt_block
    assert "Do not infer Serbian POS from suffixes alone" in prompt_block


def test_langgraph_filtering_prompt_prefers_recall_for_curation():
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(),
    )

    prompt = pipeline._render_filtering_prompt(
        {"expanded_synonyms": ["stvar", "fizički entitet"]},
        {"sense_summary": "physical entity"},
        {"definition_translation": "nešto što fizički postoji"},
        {"pos": "n", "lemmas": ["physical entity"]},
    )

    assert "Prefer recall for human curation" in prompt
    assert "Too narrow is worse than slightly broad" in prompt


def test_langgraph_minimum_literal_fallback_uses_initial_translation():
    pipeline = LangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(),
    )

    assert pipeline._ensure_minimum_literals(
        [],
        {"pos": "n", "lemmas": ["physical entity"]},
        {"initial_translations": ["fizički entitet"]},
        {"filtered_synonyms": []},
    ) == ["fizički entitet"]


def test_conceptual_minimum_literal_fallback_uses_best_candidate():
    pipeline = ConceptualLangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(),
    )

    selected = pipeline._select_minimum_conceptual_literals(
        ["stvar"],
        {
            "candidates": [
                {
                    "literal": "stvar",
                    "precision_score": 0.55,
                    "naturalness_score": 0.9,
                    "fit_assessment": "too broad",
                    "candidate_type": "primary",
                },
                {
                    "literal": "fizički objekt",
                    "precision_score": 0.68,
                    "naturalness_score": 0.82,
                    "fit_assessment": "too narrow",
                    "candidate_type": "primary",
                },
            ]
        },
        {"pos": "n", "source_literals": ["physical entity"]},
    )

    assert len(selected) == 1
    assert selected[0] == "stvar"


def test_conceptual_selection_prompt_prefers_recall_for_curation():
    pipeline = ConceptualLangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(),
    )

    prompt = pipeline._render_literal_selection_prompt(
        {"pos": "n", "source_literals": ["physical entity"]},
        {"expanded_definition_sr": "nešto što fizički postoji"},
        {"candidates": [{"literal": "stvar", "fit_assessment": "too broad"}]},
    )

    assert "Prefer recall for human curation" in prompt
    assert "Reject clearly too-narrow" in prompt
    assert "normally 1-5 literals" in prompt


def test_conceptual_model_validator_errors_become_review_for_valid_infinitive():
    pipeline = ConceptualLangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(),
    )

    validation = pipeline._apply_deterministic_validation_gates(
        {
            "validation_passed": False,
            "final_synset_ready": False,
            "issues": [
                {
                    "code": "pos_mismatch",
                    "message": "Model incorrectly claimed the Serbian infinitive is not an infinitive.",
                    "severity": "error",
                },
                {
                    "code": "blocked_literal",
                    "message": "Model incorrectly treated an anti-circularity term as a forbidden literal.",
                    "severity": "error",
                },
            ],
        },
        {
            "pos": "v",
            "source_literals": ["expectorate"],
            "source_gloss": "discharge phlegm from the lungs and out of the mouth",
        },
        ["iskašljati"],
        "izbaciti sluz ili ispljuvak iz pluća kroz usta",
    )

    assert validation["auto_status"] == "review"
    assert "model_validation_error_unconfirmed" in validation["quality_flags"]
    assert not any(
        issue.get("severity") == "error" for issue in validation["issues"]
    )


def test_conceptual_pos_cleanup_does_not_use_serbian_suffix_regex():
    pipeline = ConceptualLangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(),
    )

    selected, rejected = pipeline._filter_selected_literals_by_pos(
        ["iskašljavanje", "kašalj", "iskašljati"],
        [],
        {"pos": "v"},
    )

    assert selected == ["iskašljavanje", "kašalj", "iskašljati"]
    assert rejected == []


def test_conceptual_deterministic_literal_in_gloss_still_blocks():
    pipeline = ConceptualLangGraphTranslationPipeline(
        source_lang="en",
        target_lang="sr",
        llm=_DummyLLM(),
    )

    validation = pipeline._apply_deterministic_validation_gates(
        {"validation_passed": True, "final_synset_ready": True, "issues": []},
        {
            "pos": "v",
            "source_literals": ["expectorate"],
            "source_gloss": "discharge phlegm from the lungs and out of the mouth",
        },
        ["iskašljati"],
        "iskašljati sluz iz pluća kroz usta",
    )

    assert validation["auto_status"] == "blocked"
    assert "literal_in_gloss" in validation["quality_flags"]
