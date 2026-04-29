"""Shared chat-model factory for repository translation workflows."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Mapping, Optional, Union

DEFAULT_OLLAMA_MODEL = "gpt-oss:120b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

_OPENAI_PROVIDERS = {"openai", "openai-chat", "chatopenai"}
_OLLAMA_PROVIDERS = {"ollama", "local"}


def load_project_env(dotenv_path: Optional[Union[str, Path]] = None) -> None:
    """Load local ``.env`` values without overriding already-set environment variables."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dependency is optional at runtime
        return

    candidates: List[Path] = []
    if dotenv_path:
        candidates.append(Path(dotenv_path))
    candidates.append(Path.cwd() / ".env")
    candidates.append(Path(__file__).resolve().parents[3] / ".env")

    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists():
            load_dotenv(resolved, override=False)


def normalize_provider(provider: Optional[str]) -> str:
    """Normalize provider aliases to ``ollama`` or ``openai``."""
    token = (provider or os.getenv("LLM_PROVIDER") or "ollama").strip().lower()
    if token in _OPENAI_PROVIDERS:
        return "openai"
    if token in _OLLAMA_PROVIDERS:
        return "ollama"
    raise ValueError("Unsupported LLM provider. Use: ollama | openai")


def resolve_model_for_provider(provider: str, model: Optional[str] = None) -> str:
    """Resolve the model name using provider-specific environment defaults."""
    provider = normalize_provider(provider)
    if model:
        return model
    if provider == "openai":
        return os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
    return os.getenv("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL


def resolve_base_url_for_provider(provider: str, base_url: Optional[str] = None) -> Optional[str]:
    """Resolve the base URL for local or hosted providers."""
    provider = normalize_provider(provider)
    if provider == "openai":
        if base_url and base_url != DEFAULT_OLLAMA_BASE_URL:
            return base_url
        return os.getenv("OPENAI_BASE_URL") or None
    return base_url or os.getenv("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL


class OpenAIChatModel:
    """Small LangChain-like wrapper around the OpenAI chat-completions API."""

    def __init__(
        self,
        *,
        model: str,
        temperature: Optional[float] = 0.2,
        timeout: Optional[int] = 600,
        base_url: Optional[str] = None,
        num_predict: Optional[int] = None,
        response_format: Optional[str] = None,
    ) -> None:
        load_project_env()
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - exercised in fresh envs
            raise ImportError(
                "OpenAI provider requires the 'openai' package. Install with "
                "pip install -e .[openai] or pip install openai."
            ) from exc

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to .env or export it in the shell."
            )

        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if timeout is not None:
            client_kwargs["timeout"] = timeout
        resolved_base_url = resolve_base_url_for_provider("openai", base_url)
        if resolved_base_url:
            client_kwargs["base_url"] = resolved_base_url

        self.client = OpenAI(**client_kwargs)
        self.model = model
        self.temperature = temperature
        self.num_predict = num_predict
        self.response_format = response_format

    def invoke(self, messages: Any) -> SimpleNamespace:
        """Invoke OpenAI and return an object exposing ``content`` like LangChain."""
        converted_messages = self._convert_messages(messages)
        token_parameter = self._token_parameter_for_model(self.model)
        include_temperature = True
        include_response_format = True

        while True:
            request = self._build_request(
                converted_messages,
                token_parameter=token_parameter,
                include_temperature=include_temperature,
                include_response_format=include_response_format,
            )
            try:
                response = self.client.chat.completions.create(**request)
                break
            except Exception as exc:
                message = str(exc).lower()
                if "max_tokens" in message and token_parameter == "max_tokens":
                    token_parameter = "max_completion_tokens"
                    continue
                if "max_completion_tokens" in message and token_parameter == "max_completion_tokens":
                    token_parameter = "max_tokens"
                    continue
                if "temperature" in message and include_temperature:
                    include_temperature = False
                    continue
                if "response_format" in message and include_response_format:
                    include_response_format = False
                    continue
                raise

        choice = response.choices[0]
        content = choice.message.content or ""
        return SimpleNamespace(
            content=content,
            response_metadata={
                "model": getattr(response, "model", self.model),
                "provider": "openai",
                "finish_reason": getattr(choice, "finish_reason", None),
                "id": getattr(response, "id", None),
            },
        )

    def _build_request(
        self,
        messages: List[Dict[str, str]],
        *,
        token_parameter: str,
        include_temperature: bool,
        include_response_format: bool,
    ) -> Dict[str, Any]:
        request: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if include_temperature and self.temperature is not None:
            request["temperature"] = self.temperature
        if self.num_predict is not None:
            request[token_parameter] = self.num_predict
        if include_response_format and self.response_format == "json":
            request["response_format"] = {"type": "json_object"}
        return request

    @staticmethod
    def _token_parameter_for_model(model: str) -> str:
        """Return the token-limit parameter expected by the chat-completions model."""
        normalized = model.lower()
        if normalized.startswith(("gpt-5", "o1", "o3", "o4")):
            return "max_completion_tokens"
        return "max_tokens"

    @staticmethod
    def _convert_messages(messages: Any) -> List[Dict[str, str]]:
        if isinstance(messages, str):
            return [{"role": "user", "content": messages}]
        if isinstance(messages, Mapping):
            return [OpenAIChatModel._convert_one_message(messages)]
        if isinstance(messages, Iterable):
            return [OpenAIChatModel._convert_one_message(message) for message in messages]
        return [{"role": "user", "content": str(messages)}]

    @staticmethod
    def _convert_one_message(message: Any) -> Dict[str, str]:
        if isinstance(message, Mapping):
            role = str(message.get("role") or "user")
            content = str(message.get("content") or "")
            return {"role": role, "content": content}

        content = str(getattr(message, "content", message))
        message_type = str(getattr(message, "type", "")).lower()
        class_name = message.__class__.__name__.lower()
        if message_type == "system" or "system" in class_name:
            role = "system"
        elif message_type == "ai" or "ai" in class_name:
            role = "assistant"
        else:
            role = "user"
        return {"role": role, "content": content}


def build_chat_model(
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = 0.2,
    timeout: Optional[int] = 600,
    base_url: Optional[str] = None,
    num_ctx: Optional[int] = None,
    num_predict: Optional[int] = None,
    reasoning: Optional[Union[bool, str]] = None,
    response_format: Optional[str] = None,
) -> Any:
    """Build a chat model for the selected provider."""
    load_project_env()
    resolved_provider = normalize_provider(provider)
    resolved_model = resolve_model_for_provider(resolved_provider, model)
    resolved_base_url = resolve_base_url_for_provider(resolved_provider, base_url)

    if resolved_provider == "openai":
        return OpenAIChatModel(
            model=resolved_model,
            temperature=temperature,
            timeout=timeout,
            base_url=resolved_base_url,
            num_predict=num_predict,
            response_format=response_format,
        )

    try:
        from langchain_ollama import ChatOllama  # type: ignore[import]
    except ImportError as exc:  # pragma: no cover - exercised in runtime
        raise ImportError(
            "Ollama provider requires 'langchain-ollama'. Install extras with "
            "pip install wordnet-autotranslate[langgraph]."
        ) from exc

    kwargs: Dict[str, Any] = {
        "model": resolved_model,
        "temperature": temperature,
        "timeout": timeout,
        "base_url": resolved_base_url,
    }
    if num_ctx is not None:
        kwargs["num_ctx"] = num_ctx
    if num_predict is not None:
        kwargs["num_predict"] = num_predict
    if reasoning is not None:
        kwargs["reasoning"] = reasoning
    if response_format:
        kwargs["format"] = response_format
    return ChatOllama(**kwargs)
