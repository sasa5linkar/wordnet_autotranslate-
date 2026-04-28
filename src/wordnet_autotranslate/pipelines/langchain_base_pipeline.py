"""Minimal single-prompt translation pipeline for ablation studies.

This module provides a drastically simplified alternative to the multi-stage
LangGraph pipeline. It is intentionally lightweight so researchers can run
ablation experiments that isolate the benefits of structured prompting.

Unlike the primary pipeline, this class issues exactly one LLM call per synset.
The LLM receives the full synset payload and must return a compact JSON
structure describing the translation. No iterative refinement, validation, or
post-processing beyond basic deduplication is performed here.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
import textwrap
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence

from ..utils.language_utils import LanguageUtils
from ..utils.log_utils import sanitize_model_name

try:  # pragma: no cover - optional dependency
    from langchain_core.language_models import BaseLanguageModel
    from langchain_core.messages import HumanMessage, SystemMessage

    LANGCHAIN_CORE_AVAILABLE = True
except Exception:  # pragma: no cover - keep pipeline usable without langchain
    LANGCHAIN_CORE_AVAILABLE = False

    class BaseLanguageModel:  # type: ignore[override]
        """Runtime duck-type placeholder when LangChain is unavailable."""

        def invoke(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - stub
            raise NotImplementedError(
                "LangChain is not installed; provide a custom LLM client with an"
                " 'invoke(messages)' method."
            )

    @dataclass
    class SystemMessage:  # type: ignore[misc]
        content: str

    @dataclass
    class HumanMessage:  # type: ignore[misc]
        content: str


class _SupportsInvoke:
    """Protocol-like helper to satisfy static type checkers without Protocol."""

    def invoke(self, messages: Any, **kwargs: Any) -> Any:  # pragma: no cover - typing aide
        raise NotImplementedError


@dataclass
class SinglePromptCall:
    """Container for the data returned by a single LLM invocation."""

    prompt: str
    messages: List[Any]
    raw_response: str
    parsed_payload: Dict[str, Any]


class LangChainBasePipeline:
    """A minimal, single-prompt translation pipeline for ablation testing.

    The pipeline expects an LLM client compatible with the LangChain ChatModel
    interface. At runtime we only rely on the client exposing an ``invoke``
    method that accepts either LangChain ``BaseMessage`` objects or a
    list/dict-like fallback when LangChain is not installed.

    Output Structure
    ----------------
    The ``translate_synset`` method returns a dictionary with the following keys:

    - ``translation``: Representative literal for the synset in the target language
    - ``translated_synonyms``: Deduplicated synonym list (at least the translation)
    - ``definition_translation``: Translated gloss (may be empty string)
    - ``examples``: Usage examples in the target language (defaults to [])
    - ``notes``: Optional translator notes (``None`` when missing)
    - ``target_lang`` / ``source_lang``: ISO language codes
    - ``source``: The original synset dictionary (unchanged)
    - ``raw_response``: Unparsed LLM output text
    - ``payload``: Debug information (prompt, parsed JSON, raw message traces)
    - ``curator_summary``: Tiny human-readable blurb for quick inspection
    - ``model``: Metadata describing the model used (if provided)
    """

    DEFAULT_SYSTEM_PROMPT = (
        "You are a concise lexicographer translating WordNet synsets into"
        " target languages. Return structured JSON and avoid extra prose."
    )

    def __init__(
        self,
        *,
        source_lang: str,
        target_lang: str,
        llm: Optional[BaseLanguageModel | _SupportsInvoke] = None,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        model_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.model = model
        self.model_metadata = dict(model_metadata) if model_metadata else {}
        self.llm = llm or self._auto_configure_llm()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def translate_synset(self, synset: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a single synset using one LLM call."""

        normalized_synset = self._normalise_synset(synset)
        prompt = self._render_prompt(normalized_synset)
        call = self._call_llm(prompt)
        return self._assemble_result(normalized_synset, call)

    def translate(self, synsets: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Translate a batch of synsets sequentially."""

        return [self.translate_synset(s) for s in synsets]

    def translate_stream(self, synsets: Iterable[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
        """Yield translations lazily for large collections."""

        for synset in synsets:
            yield self.translate_synset(synset)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _auto_configure_llm(self) -> BaseLanguageModel | _SupportsInvoke:
        raise RuntimeError(
            "LangChainBasePipeline requires an 'llm' argument when instantiated."\
            " Provide a ChatModel-like object exposing invoke(messages)."
        )

    def _normalise_synset(self, synset: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure the synset dictionary exposes expected keys without mutation."""

        lemmas = synset.get("lemmas") or synset.get("literals") or []
        if isinstance(lemmas, (str, bytes)):
            lemmas = [str(lemmas)]
        elif not isinstance(lemmas, (list, tuple)):
            lemmas = []
        lemmas = [str(lemma).strip() for lemma in lemmas if str(lemma).strip()]

        definition = synset.get("definition") or synset.get("gloss") or ""
        examples = synset.get("examples") or []
        if isinstance(examples, (str, bytes)):
            examples = [str(examples)]
        elif not isinstance(examples, (list, tuple)):
            examples = []
        examples = [str(example).strip() for example in examples if str(example).strip()]

        pos = synset.get("pos") or synset.get("part_of_speech") or ""

        normalised = dict(synset)
        normalised.setdefault("lemmas", lemmas)
        normalised.setdefault("definition", definition)
        normalised.setdefault("examples", examples)
        if pos and "pos" not in normalised:
            normalised["pos"] = str(pos)

        return normalised

    def _render_prompt(self, synset: Dict[str, Any]) -> str:
        target_name = LanguageUtils.get_language_name(self.target_lang)
        lemmas = synset.get("lemmas", [])
        lemmas_display = ", ".join(lemmas) if lemmas else "(none)"
        definition = synset.get("definition") or "(no definition provided)"
        examples = synset.get("examples", [])
        formatted_examples = "\n".join(f"- {ex}" for ex in examples) if examples else "(none)"
        synset_id = synset.get("id") or synset.get("ili_id") or "(unknown id)"
        pos = synset.get("pos") or synset.get("part_of_speech") or "unknown"

        schema = textwrap.dedent(
            """
            Return strict JSON with keys:
            {
              "translation": "single string literal in target language",
              "synonyms": ["list of unique synonyms"],
              "definition_translation": "gloss translated into target language",
              "examples": ["short example sentences"],
              "notes": "optional translator notes or null"
            }
            """
        ).strip()

        return textwrap.dedent(
            f"""
            Translate the following WordNet synset from {self.source_lang.upper()} to {target_name}.
            Keep lexical meaning precise and stay within dictionary tone.

            Synset ID: {synset_id}
            Part of speech: {pos}
            English lemmas: {lemmas_display}
            Definition: {definition}
            Usage examples:
            {formatted_examples}

            {schema}
            """
        ).strip()

    def _build_messages(self, prompt: str) -> List[Any]:
        if LANGCHAIN_CORE_AVAILABLE:
            return [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt),
            ]
        return [
            {"type": "system", "content": self.system_prompt},
            {"type": "human", "content": prompt},
        ]

    def _call_llm(self, prompt: str) -> SinglePromptCall:
        messages = self._build_messages(prompt)
        response = self.llm.invoke(messages)
        raw_text = self._extract_content(response)
        parsed = self._parse_payload(raw_text)
        return SinglePromptCall(
            prompt=prompt,
            messages=messages,
            raw_response=raw_text,
            parsed_payload=parsed,
        )

    def _extract_content(self, response: Any) -> str:
        if response is None:
            return ""
        if isinstance(response, str):
            return response
        content = getattr(response, "content", None)
        if isinstance(content, str):
            return content
        if isinstance(content, list):  # some models return list of chunks
            joined = "".join(str(item) for item in content)
            return joined
        if isinstance(response, list):
            return "\n".join(str(item) for item in response)
        return str(response)

    def _parse_payload(self, raw: str) -> Dict[str, Any]:
        cleaned = raw or ""
        if cleaned:
            cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL)
            fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
            if fenced:
                candidate = fenced.group(1)
            else:
                match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
                candidate = match.group(0) if match else cleaned
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
        return {
            "translation": cleaned.strip(),
            "synonyms": [],
            "definition_translation": "",
            "examples": [],
            "notes": None,
            "error": "LLM response was not valid JSON; raw text preserved in 'translation'.",
        }

    def _assemble_result(self, synset: Dict[str, Any], call: SinglePromptCall) -> Dict[str, Any]:
        payload = dict(call.parsed_payload)

        translation = str(payload.get("translation") or "").strip()
        synonyms = self._normalise_synonyms(payload.get("synonyms"), translation)
        if not translation and synonyms:
            translation = synonyms[0]
        elif translation and translation not in synonyms:
            synonyms.insert(0, translation)

        definition_translation = str(payload.get("definition_translation") or "").strip()
        examples = self._ensure_list_of_strings(payload.get("examples"))
        notes = payload.get("notes")
        if notes is not None:
            notes = str(notes).strip() or None

        model_info = self._build_model_info()
        summary = self._render_summary(translation, synonyms, definition_translation)

        return {
            "translation": translation,
            "definition_translation": definition_translation,
            "translated_synonyms": synonyms,
            "target_lang": self.target_lang,
            "source_lang": self.source_lang,
            "source": synset,
            "examples": examples,
            "notes": notes,
            "raw_response": call.raw_response,
            "payload": {
                "prompt": call.prompt,
                "messages": call.messages,
                "parsed": payload,
            },
            "curator_summary": summary,
            "model": model_info,
        }

    def _normalise_synonyms(
        self, value: Any, translation: str
    ) -> List[str]:  # pragma: no cover - simple helper
        words: List[str] = []
        seen = set()

        def _push(text: Optional[str]) -> None:
            if not text:
                return
            cleaned = text.strip()
            if not cleaned:
                return
            key = cleaned.lower()
            if key in seen:
                return
            seen.add(key)
            words.append(cleaned)

        if isinstance(value, (list, tuple)):
            for candidate in value:
                if isinstance(candidate, (list, tuple)):
                    candidate = " ".join(str(part).strip() for part in candidate if str(part).strip())
                _push(str(candidate) if candidate is not None else None)
        elif isinstance(value, str):
            _push(value)

        _push(translation)
        return words

    def _ensure_list_of_strings(self, value: Any) -> List[str]:
        if not value:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple)):
            return []
        result = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                result.append(text)
        return result

    def _build_model_info(self) -> Dict[str, Any]:
        info = dict(self.model_metadata)
        requested = info.get("requested") or self.model
        resolved = info.get("resolved") or requested
        if requested is None and resolved is None:
            return {}
        info.setdefault("requested", requested)
        info.setdefault("resolved", resolved)
        info.setdefault("fallback_used", info.get("fallback_used", False))
        info["resolved_safe"] = sanitize_model_name(info.get("resolved"))
        return info

    def _render_summary(self, translation: str, synonyms: List[str], definition: str) -> str:
        synonyms_display = ", ".join(synonyms[:5]) if synonyms else "(none)"
        definition_preview = (definition[:120] + "…") if len(definition) > 120 else definition
        translation_display = translation or "(missing)"
        return (
            f"Primary literal: {translation_display}\n"
            f"Synonyms: {synonyms_display}\n"
            f"Gloss: {definition_preview or '(no gloss produced)'}"
        )
