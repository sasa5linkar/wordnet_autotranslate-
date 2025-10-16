"""Translation pipeline powered by LangGraph and Ollama.

This module defines an alternative translation pipeline that orchestrates
LLM calls through LangGraph while relying on a local Ollama runtime. It keeps
Serbian WordNet conventions (for example, the adverb POS tag "b") compatible
with English WordNet conventions ("r") via LanguageUtils.

By default it targets the reasoning-oriented `gpt-oss:120b` model and allows up
to 10 minutes per request so heavier local models have time to respond.

The pipeline is intentionally lightweight: it composes a small graph with nodes
for prompt preparation, model invocation, response parsing, and result
assembly. This design makes it straightforward to extend with additional guard
rails (e.g., quality estimation, dictionary cross checks) following LangGraph
best practices.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
import textwrap
from typing import Any, Dict, Generator, Iterable, List, Optional, Sequence, TypedDict

from ..utils.language_utils import LanguageUtils


class TranslationGraphState(TypedDict, total=False):
    """State container passed between LangGraph nodes."""

    synset: Dict[str, Any]
    sense_analysis: Dict[str, Any]
    definition_translation: Dict[str, Any]
    synonym_translation: Dict[str, Any]
    result: Dict[str, Any]


@dataclass
class TranslationResult:
    """Structured output returned by the LangGraph translation pipeline."""

    translation: str
    definition_translation: str
    translated_synonyms: List[str]
    target_lang: str
    source_lang: str
    source: Dict[str, Any]
    examples: List[str]
    notes: Optional[str]
    raw_response: str
    payload: Dict[str, Any]
    curator_summary: str

    def to_dict(self) -> Dict[str, Any]:
        """Return a serialisable representation for downstream usage."""
        return {
            "translation": self.translation,
            "definition_translation": self.definition_translation,
            "translated_synonyms": self.translated_synonyms,
            "target_lang": self.target_lang,
            "source_lang": self.source_lang,
            "source": self.source,
            "examples": self.examples,
            "notes": self.notes,
            "raw_response": self.raw_response,
            "payload": self.payload,
            "curator_summary": self.curator_summary,
        }


class LangGraphTranslationPipeline:
    """Alternative translation pipeline that uses LangGraph + Ollama."""

    # Default configuration constants
    DEFAULT_SYSTEM_PROMPT: str = (
        "You are an expert lexicographer helping expand WordNet into less "
        "resourced languages. Produce faithful, idiomatic translations and "
        "keep subtle sense distinctions intact. Return well-structured JSON."
    )

    DEFAULT_PROMPT_TEMPLATE: str = (
        "Translate the WordNet synset below from {source_lang} into {target_lang}.\n"
        "Provide JSON with keys: translation (string), notes (optional string), "
        "examples (list of target sentences). If you must decline, explain why.\n\n"
        "Synset ID: {synset_id}\n"
        "POS: {pos}\n"
        "Lemmas: {lemmas}\n"
        "Definition: {definition}\n"
        "Examples: {examples}\n"
        "Linked English ID: {english_id}\n"
    )

    # Response preview limit for logging
    _PREVIEW_LIMIT: int = 600
    
    # Maximum number of synonyms to display in summary
    _MAX_SYNONYMS_DISPLAY: int = 5

    def __init__(
        self,
        source_lang: str = "en",
        target_lang: str = "sr",
        model: str = "gpt-oss:120b",
        temperature: float = 0.2,
        base_url: str = "http://localhost:11434",
        timeout: int = 600,
        system_prompt: Optional[str] = None,
        prompt_template: Optional[str] = None,
        llm: Optional[Any] = None,
    ) -> None:
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.model = model
        self.temperature = temperature
        self.base_url = base_url
        self.timeout = timeout
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.prompt_template = prompt_template or self.DEFAULT_PROMPT_TEMPLATE

        (
            self._StateGraph,
            self._START,
            self._END,
            self._SystemMessage,
            self._HumanMessage,
            chat_factory,
        ) = self._load_dependencies(llm)

        self.llm = llm if llm is not None else chat_factory(
            model=self.model,
            temperature=self.temperature,
            timeout=self.timeout,
            base_url=self.base_url,
        )

        self._graph = self._build_graph()

    @staticmethod
    def _load_dependencies(provided_llm: Optional[Any]):
        """Dynamically import LangGraph and Ollama bindings when needed."""

        try:
            from langgraph.graph import END, START, StateGraph
            from langchain_core.messages import HumanMessage, SystemMessage
        except ImportError as exc:  # pragma: no cover - exercised in runtime
            raise ImportError(
                "LangGraphTranslationPipeline requires 'langgraph' and "
                "'langchain-core'. Install extras with "
                "pip install wordnet-autotranslate[langgraph]."
            ) from exc

        chat_factory = None
        if provided_llm is None:
            try:
                from langchain_ollama import ChatOllama
            except ImportError as exc:  # pragma: no cover - exercised in runtime
                raise ImportError(
                    "LangGraphTranslationPipeline needs 'langchain-ollama' when an "
                    "LLM instance isn't provided. Install extras with "
                    "pip install wordnet-autotranslate[langgraph]."
                ) from exc
            chat_factory = ChatOllama

        return StateGraph, START, END, SystemMessage, HumanMessage, chat_factory

    def _build_graph(self) -> Any:
        """Build and compile the LangGraph state machine for translation.
        
        Returns:
            Compiled graph ready for invocation.
        """
        graph = self._StateGraph(TranslationGraphState)
        graph.add_node("analyse_sense", self._analyse_sense)
        graph.add_node("translate_definition", self._translate_definition)
        graph.add_node("translate_synonyms", self._translate_synonyms)
        graph.add_node("assemble_result", self._assemble_result)

        graph.add_edge(self._START, "analyse_sense")
        graph.add_edge("analyse_sense", "translate_definition")
        graph.add_edge("translate_definition", "translate_synonyms")
        graph.add_edge("translate_synonyms", "assemble_result")
        graph.add_edge("assemble_result", self._END)

        return graph.compile()

    def translate_synset(self, synset: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a single synset and return a structured dictionary."""

        state = self._graph.invoke({"synset": synset})
        result: TranslationResult = state["result"]  # type: ignore[index]
        return result.to_dict()

    def translate(self, synsets: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Translate a batch of synsets sequentially."""

        return [self.translate_synset(synset) for synset in synsets]

    def translate_stream(
        self, synsets: Iterable[Dict[str, Any]]
    ) -> Generator[Dict[str, Any], None, None]:
        """Generator variant that yields translations as they complete."""

        for synset in synsets:
            yield self.translate_synset(synset)

    # ------------------------------------------------------------------
    # LangGraph node implementations
    # ------------------------------------------------------------------

    def _analyse_sense(self, state: TranslationGraphState) -> TranslationGraphState:
        """LangGraph node: Analyse synset sense before translation.
        
        Args:
            state: Current graph state containing synset data.
            
        Returns:
            Updated state with sense_analysis results.
        """
        synset = state["synset"]
        prompt = self._render_sense_prompt(synset)
        call_result = self._call_llm(prompt, stage="sense_analysis")
        return {"sense_analysis": call_result}

    def _translate_definition(self, state: TranslationGraphState) -> TranslationGraphState:
        """LangGraph node: Translate synset definition.
        
        Args:
            state: Current graph state with sense analysis.
            
        Returns:
            Updated state with definition_translation results.
        """
        synset = state["synset"]
        sense_payload = state.get("sense_analysis", {}).get("payload", {})
        prompt = self._render_definition_prompt(synset, sense_payload)
        call_result = self._call_llm(prompt, stage="definition_translation")
        return {"definition_translation": call_result}

    def _translate_synonyms(self, state: TranslationGraphState) -> TranslationGraphState:
        """LangGraph node: Generate target language synonyms.
        
        Args:
            state: Current graph state with definition translation.
            
        Returns:
            Updated state with synonym_translation results.
        """
        synset = state["synset"]
        sense_payload = state.get("sense_analysis", {}).get("payload", {})
        definition_payload = state.get("definition_translation", {}).get("payload", {})
        prompt = self._render_synonym_prompt(synset, sense_payload, definition_payload)
        call_result = self._call_llm(prompt, stage="synonym_translation")
        return {"synonym_translation": call_result}

    def _render_sense_prompt(self, synset: Dict[str, Any]) -> str:
        """Generate prompt for sense analysis stage.
        
        Args:
            synset: Source synset with lemmas, definition, examples.
            
        Returns:
            Formatted prompt for LLM.
        """
        lemmas = synset.get("lemmas") or synset.get("literals") or []
        lemmas_str = ", ".join(lemmas) if isinstance(lemmas, (list, tuple)) else str(lemmas)

        definition = synset.get("definition") or synset.get("gloss") or ""
        examples = synset.get("examples") or []
        examples_str = "\n- ".join(str(ex) for ex in examples) if examples else "(no direct examples)"

        pos = synset.get("pos") or synset.get("part_of_speech") or ""
        normalized_pos = LanguageUtils.normalize_pos_for_english(str(pos)) if pos else ""
        english_id = synset.get("id") or synset.get("english_id") or synset.get("ili_id") or ""

        prompt = textwrap.dedent(
            f"""
            Analyse the following WordNet synset to understand the exact sense before translating.

            Synset ID: {english_id}
            Part of speech (English WordNet tag): {normalized_pos or pos or "unknown"}
            English lemmas: {lemmas_str}
            Definition: {definition or "(not provided)"}
            Usage examples:
            - {examples_str}

            Return a JSON object with:
            - "sense_summary": concise English description (1-2 sentences) capturing the nuance of this sense.
            - "key_features": list of 2-4 short bullet points highlighting distinguishing aspects.
            - "domain_tags": optional list of topical labels (or []).
            - "confidence": one of ["high", "medium", "low"].

            Keep the analysis in English and focus on the sense, not translation.
            """
        ).strip()

        return prompt

    def _render_definition_prompt(
        self,
        synset: Dict[str, Any],
        sense_payload: Dict[str, Any],
    ) -> str:
        """Generate prompt for definition translation stage.
        
        Args:
            synset: Source synset data.
            sense_payload: Output from sense analysis stage.
            
        Returns:
            Formatted prompt for LLM.
        """
        target_name = LanguageUtils.get_language_name(self.target_lang)
        definition = synset.get("definition") or synset.get("gloss") or ""

        sense_summary = sense_payload.get("sense_summary", "")
        key_features = sense_payload.get("key_features") or []
        key_features_str = "\n- ".join(str(item) for item in key_features) if key_features else "(not provided)"

        prompt = textwrap.dedent(
            f"""
            Translate the English definition into {target_name} while preserving the analysed sense.

            Original definition:
            "{definition}"

            Sense summary: {sense_summary or "(no summary provided)"}
            Key features:
            - {key_features_str}

            Produce JSON with:
            - "definition_translation": the definition rewritten in {target_name}.
            - "notes": optional clarifications for lexicographers (string or null).
            - "examples": optional list of example sentences in {target_name} (or []).
            """
        ).strip()

        return prompt

    def _render_synonym_prompt(
        self,
        synset: Dict[str, Any],
        sense_payload: Dict[str, Any],
        definition_payload: Dict[str, Any],
    ) -> str:
        """Generate prompt for synonym translation stage.
        
        Args:
            synset: Source synset data.
            sense_payload: Output from sense analysis stage.
            definition_payload: Output from definition translation stage.
            
        Returns:
            Formatted prompt for LLM.
        """
        target_name = LanguageUtils.get_language_name(self.target_lang)
        lemmas = synset.get("lemmas") or synset.get("literals") or []
        lemmas_str = ", ".join(lemmas) if isinstance(lemmas, (list, tuple)) else str(lemmas)

        sense_summary = sense_payload.get("sense_summary", "")
        definition_translation = definition_payload.get("definition_translation", "")

        prompt = textwrap.dedent(
            f"""
            Propose {target_name} synonyms that align with the analysed sense and translated definition.

            English lemmas: {lemmas_str}
            Sense summary: {sense_summary or "(no summary available)"}
            Translated definition: {definition_translation or "(definition not translated yet)"}

            Return JSON with:
            - "preferred_headword": best single-word translation or short phrase in {target_name}.
            - "synonyms": list of objects with keys "original" (English lemma), "translation" ({target_name} synonym),
              "confidence" (high/medium/low), optional "example" sentence in {target_name}, optional "notes".
            - "examples": optional list of additional example sentences in {target_name}.
            - "notes": optional string with commentary.
            """
        ).strip()

        return prompt

    def _call_llm(self, prompt: str, stage: str) -> Dict[str, Any]:
        """Invoke the LLM with given prompt and track the interaction.
        
        Args:
            prompt: User message to send to LLM.
            stage: Current pipeline stage (for logging).
            
        Returns:
            Dict containing prompt, response, parsed payload, and metadata.
        """
        system_content = self.system_prompt + f"\nCurrent stage: {stage}. Return valid JSON as instructed."
        messages = [
            self._SystemMessage(content=system_content),
            self._HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        content: Any = getattr(response, "content", response)

        if isinstance(content, list):
            combined = "".join(
                fragment.get("text", "") if isinstance(fragment, dict) else str(fragment)
                for fragment in content
            )
            content = combined

        raw = str(content).strip()
        payload = self._decode_llm_payload(raw)

        call_log = {
            "stage": stage,
            "prompt": prompt,
            "system_prompt": system_content,
            "raw_response": raw,
            "payload": payload,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ],
        }

        return call_log

    @staticmethod
    def _summarise_call(call: Dict[str, Any]) -> Dict[str, Any]:
        """Create a concise summary of an LLM call for logging.
        
        Args:
            call: Full LLM call record with prompt, response, etc.
            
        Returns:
            Summarised version with truncated response.
        """
        if not call:
            return {}

        raw = call.get("raw_response", "")
        raw_preview = (
            raw[:LangGraphTranslationPipeline._PREVIEW_LIMIT] + "… [truncated]" 
            if raw and len(raw) > LangGraphTranslationPipeline._PREVIEW_LIMIT 
            else raw
        )

        return {
            "stage": call.get("stage"),
            "prompt": call.get("prompt"),
            "system_prompt": call.get("system_prompt"),
            "raw_response_preview": raw_preview,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_llm_payload(raw: str) -> Dict[str, Any]:
        """Best-effort JSON decoding that tolerates reasoning prefaces.

        Newer reasoning models often wrap their answer in `<think>` tags or
        fenced code blocks. This helper strips those decorations and tries
        multiple strategies to recover a dictionary payload.
        """

        if not raw:
            return {"translation": "", "examples": [], "notes": None}

        candidates: List[str] = []

        # Remove optional reasoning tags such as `<think>...</think>`.
        cleaned = re.sub(r"(?is)<think>.*?</think>", "", raw).strip()

        # Capture JSON inside fenced code blocks (```json ... ```).
        fence_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
        if fence_match:
            candidates.append(fence_match.group(1).strip())

        # Add the cleaned response itself.
        candidates.append(cleaned)

        # Add the first JSON object substring if present.
        brace_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if brace_match:
            candidates.append(brace_match.group(0))

        # Try to decode each candidate.
        for candidate in candidates:
            if not candidate:
                continue
            try:
                decoded = json.loads(candidate)
                if isinstance(decoded, dict):
                    return decoded
            except json.JSONDecodeError:
                continue

        # Fall back to json_repair if available.
        try:
            from json_repair import repair_json  # type: ignore
        except ImportError:  # pragma: no cover - optional dependency
            repair_json = None

        if repair_json:
            for candidate in candidates:
                if not candidate:
                    continue
                try:
                    fixed = repair_json(candidate)
                    decoded = json.loads(fixed)
                    if isinstance(decoded, dict):
                        return decoded
                except Exception:
                    continue

        # As a last resort return the cleaned text as plain translation.
        return {"translation": cleaned}

    def _assemble_result(self, state: TranslationGraphState) -> TranslationGraphState:
        """LangGraph node: Combine all stage outputs into final result.
        
        Args:
            state: Complete graph state with all translation stages.
            
        Returns:
            Updated state with assembled TranslationResult.
        """
        synset = state["synset"]
        sense_call = state.get("sense_analysis", {}) or {}
        definition_call = state.get("definition_translation", {}) or {}
        synonym_call = state.get("synonym_translation", {}) or {}

        sense_payload = sense_call.get("payload", {}) or {}
        definition_payload = definition_call.get("payload", {}) or {}
        synonym_payload = synonym_call.get("payload", {}) or {}

        definition_translation = str(
            definition_payload.get("definition_translation", "")
        ).strip()

        translated_synonyms: List[str] = []
        synonym_entries = synonym_payload.get("synonyms", [])
        if isinstance(synonym_entries, (list, tuple)):
            for entry in synonym_entries:
                if isinstance(entry, dict):
                    value = entry.get("translation") or entry.get("translated")
                    if value:
                        translated_synonyms.append(str(value).strip())
                elif entry:
                    translated_synonyms.append(str(entry).strip())
        elif synonym_entries:
            # allow single string payloads
            translated_synonyms.append(str(synonym_entries).strip())

        if not translated_synonyms:
            fallback_syn = synonym_payload.get("translation")
            if fallback_syn:
                translated_synonyms.append(str(fallback_syn).strip())

        preferred_headword = synonym_payload.get("preferred_headword", "")
        translation = str(preferred_headword or "").strip()
        if not translation and translated_synonyms:
            translation = translated_synonyms[0]
        if not translation:
            translation = str(definition_payload.get("recommended_headword", "")).strip()
        if not translation:
            translation = str(sense_payload.get("recommended_translation", "")).strip()
        if not translation:
            translation = str(synonym_payload.get("translation", "")).strip()

        examples: List[str] = []
        payload_examples = synonym_payload.get("examples")
        if isinstance(payload_examples, (list, tuple)):
            examples.extend(str(ex).strip() for ex in payload_examples if ex)
        elif isinstance(payload_examples, str) and payload_examples.strip():
            examples.append(payload_examples.strip())

        # enrich examples from synonym entry notes if provided
        if isinstance(synonym_entries, (list, tuple)):
            for entry in synonym_entries:
                if isinstance(entry, dict):
                    example_text = entry.get("example") or entry.get("usage")
                    if example_text and example_text.strip():
                        examples.append(str(example_text).strip())

        if not examples:
            definition_examples = definition_payload.get("examples")
            if isinstance(definition_examples, (list, tuple)):
                examples.extend(str(ex).strip() for ex in definition_examples if ex)
            elif isinstance(definition_examples, str) and definition_examples.strip():
                examples.append(definition_examples.strip())

        # Deduplicate while preserving order.
        seen_examples = set()
        unique_examples: List[str] = []
        for ex in examples:
            if ex and ex not in seen_examples:
                seen_examples.add(ex)
                unique_examples.append(ex)
        examples = unique_examples

        notes = (
            definition_payload.get("notes")
            or synonym_payload.get("notes")
            or sense_payload.get("contextual_notes")
        )
        notes = str(notes).strip() if notes else None

        # Build curator-friendly summary text.
        summary_lines: List[str] = []
        summary_lines.append(
            f"Headword ({self.target_lang}): {translation or '—'}"
        )
        summary_lines.append(
            f"Definition translation: {definition_translation or '—'}"
        )
        if translated_synonyms:
            summary_lines.append("Synonym candidates:")
            for syn in translated_synonyms[:self._MAX_SYNONYMS_DISPLAY]:
                summary_lines.append(f"  • {syn}")
            if len(translated_synonyms) > self._MAX_SYNONYMS_DISPLAY:
                summary_lines.append(
                    f"  (+{len(translated_synonyms) - self._MAX_SYNONYMS_DISPLAY} more candidates)"
                )
        else:
            summary_lines.append("Synonym candidates: (none returned)")

        if examples:
            summary_lines.append(
                f"Example sentences: {len(examples)} (showing first)"
            )
            summary_lines.append(f"  “{examples[0]}”")
        else:
            summary_lines.append("Example sentences: none")

        if notes:
            summary_lines.append(f"Notes: {notes}")

        curator_summary = "\n".join(summary_lines)

        combined_payload: Dict[str, Any] = {
            "sense": sense_payload,
            "definition": definition_payload,
            "synonyms": synonym_payload,
            "calls": {
                "sense": sense_call,
                "definition": definition_call,
                "synonyms": synonym_call,
            },
            "logs": {
                "sense": self._summarise_call(sense_call),
                "definition": self._summarise_call(definition_call),
                "synonyms": self._summarise_call(synonym_call),
            },
        }

        raw_response = synonym_call.get("raw_response") or definition_call.get("raw_response") or sense_call.get("raw_response", "")

        result = TranslationResult(
            translation=translation,
            definition_translation=definition_translation,
            translated_synonyms=translated_synonyms,
            target_lang=self.target_lang,
            source_lang=self.source_lang,
            source=dict(synset),
            examples=examples,
            notes=notes,
            raw_response=raw_response,
            payload=combined_payload,
            curator_summary=curator_summary,
        )

        return {"result": result}