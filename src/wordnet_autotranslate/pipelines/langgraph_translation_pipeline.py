"""Translation pipeline powered by LangGraph and Ollama.

This module defines an alternative translation pipeline that orchestrates
LLM calls through LangGraph while relying on a local Ollama runtime. It keeps
Serbian WordNet conventions (for example, the adverb POS tag "b") compatible
with English WordNet conventions ("r") via LanguageUtils.

By default it targets the reasoning-oriented `gpt-oss:120b` model and allows up
to 10 minutes per request so heavier local models have time to respond.

The pipeline uses a multi-step "generate-and-filter" approach for synonym translation:

1. analyse_sense: Understand semantic nuances before translation
2. translate_definition: Translate the definition with context
3. translate_all_lemmas: Direct translation of each English lemma
4. expand_synonyms: Broaden the candidate pool with target-language synonyms
5. filter_synonyms: Quality check to remove imperfect matches
6. assemble_result: Combine all outputs into final synset

This generate-and-filter approach ensures high-quality synsets by first casting
a wide net for candidates, then rigorously validating each one against the precise
sense. The final output is a set of synonymous literals (synset), not a headword.

The design makes it straightforward to extend with additional guard rails (e.g.,
quality estimation, dictionary cross checks) following LangGraph best practices.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
import textwrap
from typing import Any, Dict, Generator, Iterable, List, Optional, Sequence, TypedDict

from pydantic import BaseModel, Field, ValidationError
from pydantic_core import PydanticUndefined

from ..utils.language_utils import LanguageUtils


class TranslationGraphState(TypedDict, total=False):
    """State container passed between LangGraph nodes."""

    synset: Dict[str, Any]
    sense_analysis: Dict[str, Any]
    definition_translation: Dict[str, Any]
    
    # New keys for multi-step synonym translation (generate-and-filter approach)
    initial_translation_call: Dict[str, Any]
    expansion_call: Dict[str, Any]
    filtering_call: Dict[str, Any]
    
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
    # English WordNet domain information (automatically fetched from NLTK)
    lexname: Optional[str] = None  # Broad lexical category (e.g., "noun.artifact", "verb.motion")
    topic_domains: Optional[List[str]] = None  # Semantic field markers (e.g., ["biochemistry.n.01"])

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
            "lexname": self.lexname,
            "topic_domains": self.topic_domains,
        }


# ==============================================================
# Schema validation helpers for LangGraphTranslationPipeline
# ==============================================================

class SenseAnalysisSchema(BaseModel):
    """Pydantic schema for sense analysis stage output."""
    sense_summary: str = Field(..., min_length=3)
    contrastive_note: Optional[str] = None
    key_features: List[str] = Field(default_factory=list)
    domain_tags: Optional[List[str]] = Field(default_factory=list)
    confidence: str


class DefinitionTranslationSchema(BaseModel):
    """Pydantic schema for definition translation stage output."""
    definition_translation: str
    notes: Optional[str] = None
    examples: Optional[List[str]] = Field(default_factory=list)


class LemmaTranslationSchema(BaseModel):
    """Pydantic schema for initial lemma translation stage output."""
    initial_translations: List[Optional[str]]
    alignment: Dict[str, Optional[str]]


class ExpansionSchema(BaseModel):
    """Pydantic schema for synonym expansion stage output."""
    expanded_synonyms: List[str]
    rationale: Optional[Dict[str, str]] = Field(default_factory=dict)


class FilteringSchema(BaseModel):
    """Pydantic schema for synonym filtering stage output."""
    filtered_synonyms: List[str]
    removed: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    confidence: str


def validate_stage_payload(payload: dict, schema_cls: type[BaseModel], stage_name: str) -> dict:
    """Validate LLM JSON payload against the expected schema.
    
    Auto-repairs empty or malformed values and logs warnings.
    
    Args:
        payload: Raw dictionary from LLM output.
        schema_cls: Pydantic model class to validate against.
        stage_name: Stage name for logging.
        
    Returns:
        Validated and potentially repaired payload dictionary.
    """
    try:
        model = schema_cls(**payload)
        return model.model_dump()
    except ValidationError as e:
        print(f"[WARN] Validation failed for stage '{stage_name}': {e}")
        # Return fallback with required keys if possible
        fallback = {}
        for field_name, field_info in schema_cls.model_fields.items():
            if field_info.is_required():
                fallback[field_name] = ""
            elif field_info.default is not PydanticUndefined:
                fallback[field_name] = field_info.default
            elif field_info.default_factory is not None:
                # Call the factory function to get default value
                fallback[field_name] = field_info.default_factory()
            else:
                fallback[field_name] = None
        return {**fallback, **payload}


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
        
        The graph now uses a multi-step synonym translation approach:
        1. analyse_sense - Understand semantic features
        2. translate_definition - Translate the definition
        3. translate_all_lemmas - Direct translation of each lemma
        4. expand_synonyms - Broaden the candidate pool
        5. filter_synonyms - Quality check and validation
        6. assemble_result - Combine all outputs
        
        Returns:
            Compiled graph ready for invocation.
        """
        graph = self._StateGraph(TranslationGraphState)
        graph.add_node("analyse_sense", self._analyse_sense)
        graph.add_node("translate_definition", self._translate_definition)
        graph.add_node("translate_all_lemmas", self._translate_all_lemmas)
        graph.add_node("expand_synonyms", self._expand_synonyms)
        graph.add_node("filter_synonyms", self._filter_synonyms)
        graph.add_node("assemble_result", self._assemble_result)

        graph.add_edge(self._START, "analyse_sense")
        graph.add_edge("analyse_sense", "translate_definition")
        graph.add_edge("translate_definition", "translate_all_lemmas")
        graph.add_edge("translate_all_lemmas", "expand_synonyms")
        graph.add_edge("expand_synonyms", "filter_synonyms")
        graph.add_edge("filter_synonyms", "assemble_result")
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

    def _translate_all_lemmas(self, state: TranslationGraphState) -> TranslationGraphState:
        """LangGraph node: Translate all English lemmas directly.
        
        This is the first step in the multi-step synonym pipeline. It gets
        initial direct translations for each English lemma in the source synset.
        
        Args:
            state: Current graph state with synset and sense_analysis.
            
        Returns:
            Updated state with initial_translation_call results.
        """
        synset = state["synset"]
        sense_payload = state.get("sense_analysis", {}).get("payload", {})
        prompt = self._render_initial_translation_prompt(synset, sense_payload)
        call_result = self._call_llm(prompt, stage="initial_translation")
        return {"initial_translation_call": call_result}

    def _expand_synonyms(self, state: TranslationGraphState) -> TranslationGraphState:
        """LangGraph node: Expand the candidate pool with additional synonyms.
        
        This is the second step in the multi-step synonym pipeline. It takes
        the initial translations and finds more synonyms in the target language
        that align with the sense and definition.
        
        Args:
            state: Current graph state with initial translations.
            
        Returns:
            Updated state with expansion_call results.
        """
        initial_payload = state.get("initial_translation_call", {}).get("payload", {})
        sense_payload = state.get("sense_analysis", {}).get("payload", {})
        definition_payload = state.get("definition_translation", {}).get("payload", {})
        prompt = self._render_expansion_prompt(initial_payload, sense_payload, definition_payload)
        call_result = self._call_llm(prompt, stage="synonym_expansion")
        return {"expansion_call": call_result}

    def _filter_synonyms(self, state: TranslationGraphState) -> TranslationGraphState:
        """LangGraph node: Filter and validate synonym candidates.
        
        This is the final step in the multi-step synonym pipeline. It performs
        a quality check to remove candidates that don't precisely match the
        intended sense, ensuring high-quality output.
        
        Args:
            state: Current graph state with expanded synonyms.
            
        Returns:
            Updated state with filtering_call results.
        """
        expansion_payload = state.get("expansion_call", {}).get("payload", {})
        sense_payload = state.get("sense_analysis", {}).get("payload", {})
        definition_payload = state.get("definition_translation", {}).get("payload", {})
        prompt = self._render_filtering_prompt(expansion_payload, sense_payload, definition_payload)
        call_result = self._call_llm(prompt, stage="synonym_filtering")
        return {"filtering_call": call_result}

    # ============================================================================
    # PROMPT GENERATION METHODS
    # ============================================================================
    # This section contains all prompt rendering methods for each pipeline stage.
    # Each method constructs the specific prompt text sent to the LLM.
    # ============================================================================

    def _render_sense_prompt(self, synset: Dict[str, Any]) -> str:
        """Generate prompt for sense analysis stage (improved with contrastive notes).
        
        Args:
            synset: Source synset with lemmas, definition, examples.
            
        Returns:
            Formatted prompt for LLM.
        """
        lemmas = synset.get("lemmas") or synset.get("literals") or []
        lemmas_str = ", ".join(lemmas) if isinstance(lemmas, (list, tuple)) else str(lemmas)

        definition = synset.get("definition") or synset.get("gloss") or ""
        examples = synset.get("examples") or []
        examples_str = "\n- ".join(str(ex) for ex in examples) if examples else "(no examples)"

        pos = synset.get("pos") or synset.get("part_of_speech") or ""
        normalized_pos = LanguageUtils.normalize_pos_for_english(str(pos)) if pos else ""
        english_id = synset.get("id") or synset.get("english_id") or synset.get("ili_id") or ""

        # Fetch domain information from English WordNet
        domain_info = self._get_wordnet_domain_info(english_id)
        lexname = domain_info.get("lexname", "")
        topic_domains = domain_info.get("topic_domains", [])
        topic_domains_str = ", ".join(topic_domains) if topic_domains else "(none)"

        prompt = textwrap.dedent(
            f"""
            Analyse the following WordNet synset carefully.

            Synset ID: {english_id}
            POS: {normalized_pos or pos or "unknown"}
            Lexname: {lexname or "(not available)"}
            Topic domains: {topic_domains_str}
            English lemmas: {lemmas_str}
            Definition: {definition or "(not provided)"}
            Usage examples:
            - {examples_str}

            Return JSON:
            {{
              "sense_summary": "1–2 sentence English description capturing nuance.",
              "contrastive_note": "What distinguishes this sense from other senses of the lemma.",
              "key_features": ["short salient features"],
              "domain_tags": ["optional topical tags"],
              "confidence": "high|medium|low"
            }}
            Focus on *what makes this sense unique*, not just definitional paraphrasing.
            """
        ).strip()

        return prompt

    def _render_definition_prompt(
        self,
        synset: Dict[str, Any],
        sense_payload: Dict[str, Any],
    ) -> str:
        """Generate prompt for definition translation stage (improved: concise gloss style + fallback rules).
        
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
        key_features_str = "\n- ".join(str(item) for item in key_features) if key_features else "(none)"

        prompt = textwrap.dedent(
            f"""
            Translate this English WordNet gloss into {target_name}.

            Original definition: "{definition or '(not provided)'}"
            Sense summary: {sense_summary or "(no summary provided)"}
            Key features:
            - {key_features_str}

            Guidelines:
            - Output must sound like a *dictionary gloss* in {target_name}: short, neutral, non-sentence form.
            - Keep factual and stylistic fidelity.
            - If uncertain, give literal translation plus clarifying note.

            Return JSON:
            {{
              "definition_translation": "gloss in {target_name}",
              "notes": "optional lexicographer comment",
              "examples": ["example1", "example2"]
            }}
            """
        ).strip()

        return prompt

    def _render_initial_translation_prompt(
        self,
        synset: Dict[str, Any],
        sense_payload: Dict[str, Any],
    ) -> str:
        """Generate prompt for initial lemma translation stage (improved: 1:1 alignment + null placeholders).
        
        Args:
            synset: Source synset data.
            sense_payload: Output from sense analysis stage.
            
        Returns:
            Formatted prompt for LLM.
        """
        target_name = LanguageUtils.get_language_name(self.target_lang)
        lemmas = synset.get("lemmas") or synset.get("literals") or []
        # Keep lemmas as list for proper JSON formatting
        lemmas_list = lemmas if isinstance(lemmas, (list, tuple)) else [lemmas]

        sense_summary = sense_payload.get("sense_summary", "")

        prompt = textwrap.dedent(
            f"""
            Translate each English lemma into {target_name}, preserving one-to-one order.

            English lemmas: {lemmas_list}
            Sense summary: {sense_summary or "(no summary available)"}

            Rules:
            - Each translation must match *this sense*, not general meaning.
            - Keep array order aligned to lemmas; use null if no exact equivalent.

            Return JSON:
            {{
              "initial_translations": ["lemma1_translation", "lemma2_translation", ...],
              "alignment": {{"lemma1": "translation1", "lemma2": "translation2"}}
            }}
            """
        ).strip()

        return prompt

    def _render_expansion_prompt(
        self,
        initial_payload: Dict[str, Any],
        sense_payload: Dict[str, Any],
        definition_payload: Dict[str, Any],
    ) -> str:
        """Generate prompt for synonym expansion stage (improved: requires rationale for each new synonym).
        
        Args:
            initial_payload: Output from initial translation stage.
            sense_payload: Output from sense analysis stage.
            definition_payload: Output from definition translation stage.
            
        Returns:
            Formatted prompt for LLM.
        """
        target_name = LanguageUtils.get_language_name(self.target_lang)
        initial_translations = initial_payload.get("initial_translations", [])
        # Filter out null values from initial translations
        initial_translations = [t for t in initial_translations if t is not None]
        initial_str = ", ".join(str(t) for t in initial_translations) if initial_translations else "(none)"
        
        sense_summary = sense_payload.get("sense_summary", "")
        definition_translation = definition_payload.get("definition_translation", "")

        prompt = textwrap.dedent(
            f"""
            Generate additional {target_name} synonyms matching this precise sense.

            Initial translations: {initial_str}
            Sense summary: {sense_summary or "(no summary available)"}
            Translated definition: {definition_translation or "(not available)"}

            Tasks:
            1. Retain all initial translations.
            2. Add strictly synonymous words—same POS, meaning, and register.
            3. Exclude hypernyms, antonyms, or stylistic shifts.

            Return JSON:
            {{
              "expanded_synonyms": ["word1", "word2", ...],
              "rationale": {{"word2": "colloquial variant", "word3": "archaic synonym"}}
            }}
            """
        ).strip()

        return prompt

    def _render_filtering_prompt(
        self,
        expansion_payload: Dict[str, Any],
        sense_payload: Dict[str, Any],
        definition_payload: Dict[str, Any],
    ) -> str:
        """Generate prompt for synonym filtering/validation stage (improved: structured rejections + confidence level).
        
        Args:
            expansion_payload: Output from expansion stage.
            sense_payload: Output from sense analysis stage.
            definition_payload: Output from definition translation stage.
            
        Returns:
            Formatted prompt for LLM.
        """
        target_name = LanguageUtils.get_language_name(self.target_lang)
        expanded_synonyms = expansion_payload.get("expanded_synonyms", [])
        expanded_str = ", ".join(str(t) for t in expanded_synonyms) if expanded_synonyms else "(none)"
        
        sense_summary = sense_payload.get("sense_summary", "")
        definition_translation = definition_payload.get("definition_translation", "")

        prompt = textwrap.dedent(
            f"""
            Validate the following {target_name} candidates; keep only *perfect synonyms*.

            Candidates: {expanded_str}
            Sense summary: {sense_summary or "(no summary available)"}
            Definition: {definition_translation or "(not available)"}

            Reject any that:
            - Differ in meaning or register
            - Violate POS or grammatical gender/number
            - Are dialectal or figurative unless universally interchangeable

            Return JSON:
            {{
              "filtered_synonyms": ["final1", "final2"],
              "removed": [{{"word": "X", "reason": "broader meaning"}}],
              "confidence": "high|medium|low"
            }}
            """
        ).strip()

        return prompt

    # ============================================================================
    # END OF PROMPT GENERATION METHODS
    # ============================================================================

    def _call_llm(self, prompt: str, stage: str, retries: int = 2) -> Dict[str, Any]:
        """Invoke LLM with automatic JSON validation + retry on malformed output.
        
        Args:
            prompt: User message to send to LLM.
            stage: Current pipeline stage (for logging).
            retries: Number of retry attempts on validation failure.
            
        Returns:
            Dict containing prompt, response, parsed payload, and metadata.
        """
        for attempt in range(retries + 1):
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
            
            # Validate payload against schema for this stage
            payload = self._validate_payload_for_stage(stage, payload)

            # Basic success check - ensure we have valid data
            if payload and any(payload.values()):
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
            
            # Log retry attempt
            if attempt < retries:
                print(f"[Retry {attempt + 1}/{retries}] Invalid or empty JSON for stage '{stage}'")
        
        # Fallback return after max retries
        print(f"[ERROR] Max retries exceeded for stage '{stage}', returning error payload")
        return {
            "stage": stage,
            "prompt": prompt,
            "system_prompt": system_content,
            "raw_response": raw,
            "payload": {"error": "max retries exceeded"},
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

    def _validate_payload_for_stage(self, stage: str, payload: dict) -> dict:
        """Auto-choose schema based on stage name and validate payload.
        
        Args:
            stage: Current pipeline stage name.
            payload: Raw dictionary from LLM output.
            
        Returns:
            Validated and potentially repaired payload dictionary.
        """
        schema_map = {
            "sense_analysis": SenseAnalysisSchema,
            "definition_translation": DefinitionTranslationSchema,
            "initial_translation": LemmaTranslationSchema,
            "synonym_expansion": ExpansionSchema,
            "synonym_filtering": FilteringSchema,
        }
        schema_cls = schema_map.get(stage)
        if schema_cls:
            return validate_stage_payload(payload, schema_cls, stage)
        return payload

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

    @staticmethod
    def _get_wordnet_domain_info(english_id: str) -> Dict[str, Any]:
        """Fetch domain information from NLTK WordNet using english_id.
        
        Returns both lexname (broad category) and topic_domains (semantic field markers).
        
        Args:
            english_id: English WordNet synset ID (e.g., "ENG30-03574555-n")
            
        Returns:
            Dictionary with 'lexname' and 'topic_domains' keys, or empty dict if not found.
        """
        if not english_id:
            return {}
        
        try:
            from nltk.corpus import wordnet as wn
        except ImportError:
            # NLTK not available, skip domain lookup
            return {}
        
        try:
            # Parse the english_id format (e.g., "ENG30-03574555-n")
            # Extract offset and POS
            parts = english_id.split('-')
            if len(parts) < 3:
                return {}
            
            offset_str = parts[1]
            pos_char = parts[2]
            
            # Convert offset to integer
            offset = int(offset_str)
            
            # Get the synset from WordNet
            synset = wn.synset_from_pos_and_offset(pos_char, offset)
            
            # Get lexname (broad category like "noun.artifact", "verb.motion")
            lexname = synset.lexname()
            
            # Get topic domains (semantic field markers like "biology.n.01", "music.n.01")
            topic_domains = synset.topic_domains()
            topic_domain_names = [td.name() for td in topic_domains] if topic_domains else []
            
            return {
                "lexname": lexname,
                "topic_domains": topic_domain_names,
            }
            
        except (ValueError, LookupError, AttributeError):
            # Could not parse or find synset
            return {}
            
            # Return the lexname (domain)
            return synset.lexname()
            
        except (ValueError, LookupError, AttributeError):
            # Could not parse or find synset
            return None

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
        
        # Get results from the new multi-step synonym pipeline
        initial_call = state.get("initial_translation_call", {}) or {}
        expansion_call = state.get("expansion_call", {}) or {}
        filtering_call = state.get("filtering_call", {}) or {}

        sense_payload = sense_call.get("payload", {}) or {}
        definition_payload = definition_call.get("payload", {}) or {}
        initial_payload = initial_call.get("payload", {}) or {}
        expansion_payload = expansion_call.get("payload", {}) or {}
        filtering_payload = filtering_call.get("payload", {}) or {}

        definition_translation = str(
            definition_payload.get("definition_translation", "")
        ).strip()

        # Extract the final, validated synonyms from the filtering stage
        # This is the high-quality synset produced by the generate-and-filter pipeline
        translated_synonyms: List[str] = []
        filtered_synonyms = filtering_payload.get("filtered_synonyms", [])
        
        if isinstance(filtered_synonyms, (list, tuple)):
            for syn in filtered_synonyms:
                if syn:
                    translated_synonyms.append(str(syn).strip())
        elif filtered_synonyms:
            # Handle single string case
            translated_synonyms.append(str(filtered_synonyms).strip())
        
        # Remove any empty strings and deduplicate while preserving order
        seen = set()
        deduped_synonyms: List[str] = []
        for syn in translated_synonyms:
            if syn and syn not in seen:
                seen.add(syn)
                deduped_synonyms.append(syn)
        translated_synonyms = deduped_synonyms

        # The "translation" field holds a representative literal for convenience
        # (e.g., for logging or display). This is NOT a formal "headword" - 
        # the final output is a synset (set of synonymous literals).
        # We simply use the first item from the filtered list if available.
        translation = translated_synonyms[0] if translated_synonyms else ""

        # Gather examples from definition translation
        examples: List[str] = []
        definition_examples = definition_payload.get("examples")
        if isinstance(definition_examples, (list, tuple)):
            examples.extend(str(ex).strip() for ex in definition_examples if ex)
        elif isinstance(definition_examples, str) and definition_examples.strip():
            examples.append(definition_examples.strip())

        # Deduplicate examples while preserving order
        seen_examples = set()
        unique_examples: List[str] = []
        for ex in examples:
            if ex and ex not in seen_examples:
                seen_examples.add(ex)
                unique_examples.append(ex)
        examples = unique_examples

        # Gather notes from definition stage
        notes = definition_payload.get("notes")
        notes = str(notes).strip() if notes else None

        # Fetch domain information from English WordNet
        english_id = synset.get("id") or synset.get("english_id") or synset.get("ili_id") or ""
        domain_info = self._get_wordnet_domain_info(english_id)
        lexname = domain_info.get("lexname")
        topic_domains = domain_info.get("topic_domains", [])

        # Build curator-friendly summary text
        summary_lines: List[str] = []
        summary_lines.append(
            f"Representative literal ({self.target_lang}): {translation or '—'}"
        )
        summary_lines.append(
            f"Definition translation: {definition_translation or '—'}"
        )
        if lexname:
            summary_lines.append(f"Lexname: {lexname}")
        if topic_domains:
            summary_lines.append(f"Topic domains: {', '.join(topic_domains)}")
        if translated_synonyms:
            summary_lines.append(f"Synset literals ({len(translated_synonyms)} total):")
            for syn in translated_synonyms[:self._MAX_SYNONYMS_DISPLAY]:
                summary_lines.append(f"  • {syn}")
            if len(translated_synonyms) > self._MAX_SYNONYMS_DISPLAY:
                summary_lines.append(
                    f"  (+{len(translated_synonyms) - self._MAX_SYNONYMS_DISPLAY} more literals)"
                )
        else:
            summary_lines.append("Synset literals: (none returned)")

        if examples:
            summary_lines.append(
                f"Example sentences: {len(examples)} (showing first)"
            )
            summary_lines.append(f"  “{examples[0]}”")
        else:
            summary_lines.append("Example sentences: none")

        if notes:
            summary_lines.append(f"Notes: {notes}")
        
        # Add pipeline stage info
        summary_lines.append(f"\nPipeline stages completed:")
        summary_lines.append(f"  1. Initial translations: {len(initial_payload.get('initial_translations', []))} lemmas")
        summary_lines.append(f"  2. Expanded candidates: {len(expansion_payload.get('expanded_synonyms', []))} synonyms")
        summary_lines.append(f"  3. Filtered results: {len(translated_synonyms)} final literals")

        curator_summary = "\n".join(summary_lines)

        combined_payload: Dict[str, Any] = {
            "sense": sense_payload,
            "definition": definition_payload,
            "initial_translation": initial_payload,
            "expansion": expansion_payload,
            "filtering": filtering_payload,
            "calls": {
                "sense": sense_call,
                "definition": definition_call,
                "initial_translation": initial_call,
                "expansion": expansion_call,
                "filtering": filtering_call,
            },
            "logs": {
                "sense": self._summarise_call(sense_call),
                "definition": self._summarise_call(definition_call),
                "initial_translation": self._summarise_call(initial_call),
                "expansion": self._summarise_call(expansion_call),
                "filtering": self._summarise_call(filtering_call),
            },
        }

        raw_response = (
            filtering_call.get("raw_response") 
            or expansion_call.get("raw_response") 
            or initial_call.get("raw_response")
            or definition_call.get("raw_response") 
            or sense_call.get("raw_response", "")
        )

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
            lexname=lexname,
            topic_domains=topic_domains,
        )

        return {"result": result}