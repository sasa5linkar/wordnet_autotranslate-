import json
from typing import Any, Dict, List

import pytest

from wordnet_autotranslate.pipelines.langchain_base_pipeline import (
    LangChainBasePipeline,
)


class _MemoryLLM:
    """Simple stand-in chat model that records the last prompt."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload
        self.messages: List[Any] = []
        self.calls = 0

    def invoke(self, messages: List[Any]) -> Any:  # pragma: no cover - behaviour tested via assertions
        self.messages = messages
        self.calls += 1

        class _Response:
            content = json.dumps(self.payload)

        return _Response()


class _PlainTextLLM:
    """Returns a non-JSON payload to exercise fallback parsing."""

    def __init__(self, text: str) -> None:
        self.text = text

    def invoke(self, messages: List[Any]) -> str:  # pragma: no cover - direct behaviour
        return self.text


@pytest.fixture
def demo_synset() -> Dict[str, Any]:
    return {
        "id": "ENG30-00001740-n",
        "lemmas": ["entity"],
        "definition": "that which is perceived or known to have its own distinct existence",
        "examples": ["The entity known as Bigfoot has not been captured."],
        "pos": "n",
    }


def test_langchain_base_pipeline_structured_json(demo_synset: Dict[str, Any]) -> None:
    llm = _MemoryLLM(
        payload={
            "translation": "entitet",
            "synonyms": ["entitet", "biće"],
            "definition_translation": "Nešto što ima svoje sopstveno postojanje.",
            "examples": ["Ovo je entitet."],
            "notes": "Direct mapping from English sense.",
        }
    )
    pipeline = LangChainBasePipeline(
        source_lang="en",
        target_lang="sr",
        llm=llm,
        model="gpt-test",
        model_metadata={"resolved": "gpt-test"},
    )

    result = pipeline.translate_synset(demo_synset)

    assert result["translation"] == "entitet"
    assert result["translated_synonyms"] == ["entitet", "biće"]
    assert result["definition_translation"].startswith("Nešto")
    assert result["target_lang"] == "sr"
    assert result["source_lang"] == "en"
    assert result["notes"] == "Direct mapping from English sense."
    assert result["examples"] == ["Ovo je entitet."]
    assert "Primary literal" in result["curator_summary"]
    assert result["model"]["resolved_safe"] == "gpt-test"
    assert llm.calls == 1
    assert any("translation" in str(message) for message in llm.messages[-1:])


def test_langchain_base_pipeline_plain_text_fallback(demo_synset: Dict[str, Any]) -> None:
    llm = _PlainTextLLM("samo tekst")
    pipeline = LangChainBasePipeline(source_lang="en", target_lang="sr", llm=llm)

    result = pipeline.translate_synset(demo_synset)

    assert result["translation"] == "samo tekst"
    assert result["translated_synonyms"] == ["samo tekst"]
    assert result["definition_translation"] == ""
    assert result["examples"] == []
    assert "error" in result["payload"]["parsed"]
    # model key must be absent when no model info is provided
    assert "model" not in result


def test_langchain_base_pipeline_normalise_none_fields(demo_synset: Dict[str, Any]) -> None:
    """_normalise_synset should overwrite None/wrong-type fields unconditionally."""
    llm = _MemoryLLM(
        payload={
            "translation": "entitet",
            "synonyms": [],
            "definition_translation": "",
            "examples": [],
            "notes": None,
        }
    )
    pipeline = LangChainBasePipeline(source_lang="en", target_lang="sr", llm=llm)

    synset_with_nones = {
        "id": "test-id",
        "lemmas": None,        # should be corrected to []
        "definition": None,    # should be corrected to ""
        "examples": None,      # should be corrected to []
        "pos": None,           # should be corrected to ""
    }

    result = pipeline.translate_synset(synset_with_nones)

    # Pipeline must not raise; the normalised source is returned in result["source"]
    assert isinstance(result["source"]["lemmas"], list)
    assert isinstance(result["source"]["definition"], str)
    assert isinstance(result["source"]["examples"], list)
    assert isinstance(result["source"]["pos"], str)


def test_langchain_base_pipeline_unknown_lang_code(demo_synset: Dict[str, Any]) -> None:
    """Prompts for unknown language codes should use the raw code, not 'Unknown (...)'."""
    llm = _MemoryLLM(
        payload={
            "translation": "test",
            "synonyms": [],
            "definition_translation": "",
            "examples": [],
            "notes": None,
        }
    )
    pipeline = LangChainBasePipeline(source_lang="en", target_lang="xx", llm=llm)
    pipeline.translate_synset(demo_synset)

    last_human = llm.messages[-1]
    prompt_text = getattr(last_human, "content", str(last_human))
    # Must not contain "Unknown" in the generated prompt
    assert "Unknown" not in prompt_text
    # Must contain the raw code instead
    assert "xx" in prompt_text


def test_langchain_base_pipeline_batch_and_stream(demo_synset: Dict[str, Any]) -> None:
    llm = _MemoryLLM(
        payload={
            "translation": "entitet",
            "synonyms": ["entitet"],
            "definition_translation": "Nešto što postoji.",
            "examples": [],
            "notes": None,
        }
    )
    pipeline = LangChainBasePipeline(source_lang="en", target_lang="sr", llm=llm)

    batch = pipeline.translate([demo_synset, demo_synset])
    assert len(batch) == 2
    assert llm.calls == 2

    stream_results = list(pipeline.translate_stream([demo_synset, demo_synset]))
    assert len(stream_results) == 2
    assert all(result["translation"] == "entitet" for result in stream_results)