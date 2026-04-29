from types import SimpleNamespace

import pytest

from wordnet_autotranslate.utils.llm_factory import (
    DEFAULT_OPENAI_MODEL,
    OpenAIChatModel,
    normalize_provider,
    resolve_base_url_for_provider,
    resolve_model_for_provider,
)


def test_normalize_provider_aliases():
    assert normalize_provider("openai") == "openai"
    assert normalize_provider("chatopenai") == "openai"
    assert normalize_provider("ollama") == "ollama"
    assert normalize_provider("local") == "ollama"

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        normalize_provider("unknown")


def test_resolve_openai_defaults_from_environment(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    assert resolve_model_for_provider("openai", None) == DEFAULT_OPENAI_MODEL
    assert resolve_base_url_for_provider("openai", "http://localhost:11434") is None

    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")

    assert resolve_model_for_provider("openai", None) == "gpt-test"
    assert resolve_base_url_for_provider("openai", None) == "https://example.test/v1"


def test_openai_message_conversion_handles_langchain_like_messages():
    messages = [
        SimpleNamespace(type="system", content="system text"),
        SimpleNamespace(type="human", content="user text"),
        SimpleNamespace(type="ai", content="assistant text"),
    ]

    assert OpenAIChatModel._convert_messages(messages) == [
        {"role": "system", "content": "system text"},
        {"role": "user", "content": "user text"},
        {"role": "assistant", "content": "assistant text"},
    ]


def test_openai_token_parameter_for_newer_models():
    assert OpenAIChatModel._token_parameter_for_model("gpt-5.4-nano") == "max_completion_tokens"
    assert OpenAIChatModel._token_parameter_for_model("o4-mini") == "max_completion_tokens"
    assert OpenAIChatModel._token_parameter_for_model("gpt-4o-mini") == "max_tokens"
