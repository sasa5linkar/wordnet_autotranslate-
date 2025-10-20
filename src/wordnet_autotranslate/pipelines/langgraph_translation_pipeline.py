"""Translation pipeline powered by LangGraph and Ollama.

This module implements a sophisticated multi-stage translation pipeline for WordNet synsets,
orchestrating LLM calls through LangGraph with a local Ollama runtime.

Architecture Overview
--------------------
The pipeline employs a "generate-and-filter" approach to ensure high-quality translations:

    1. **Sense Analysis** - Understand semantic nuances and context before translation
    2. **Definition Translation** - Translate gloss with cultural adaptation
    3. **Initial Translation** - Direct 1:1 translation of each English lemma
    4. **Synonym Expansion** - Iteratively broaden candidate pool (up to 5 iterations)
    5. **Synonym Filtering** - Quality check with per-word confidence scores
    6. **Definition Quality Review** - Final grammatical and stylistic polish of translated gloss
    7. **Result Assembly** - Combine outputs, deduplicate, and format final synset

Key Features
-----------
- **Iterative Expansion**: Runs expansion multiple times until convergence
- **Schema Validation**: Pydantic schemas with auto-repair for all stages
- **Retry Logic**: Automatic retry (2 attempts) on LLM failures
- **Compound Deduplication**: Removes redundant multiword expressions
- **Per-Word Confidence**: Individual quality scores for each synonym
- **Full Log Preservation**: Untruncated LLM outputs for analysis
- **Definition Quality Safeguard**: Post-filter review catches stylistic or grammatical issues
- **WordNet Domain Integration**: Automatic lexname and topic domain extraction

Language Support
---------------
- Maintains Serbian WordNet conventions (e.g., adverb POS tag "b")
- Compatible with English WordNet conventions (e.g., "r" for adverbs)
- Uses LanguageUtils for cross-lingual POS mapping

Configuration
------------
- Default model: `gpt-oss:120b` (reasoning-oriented)
- Default timeout: 600 seconds (10 minutes)
- Default temperature: 0.2 (more deterministic)
- Expansion iterations: 5 (configurable via max_expansion_iterations)

Notes
-----
The final output is a **synset** (set of synonymous literals), not a headword.
This design supports easy extension with additional validation steps following
LangGraph best practices.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
import textwrap
from typing import Any, Dict, Generator, Iterable, List, Literal, Optional, Sequence, TypedDict

from pydantic import BaseModel, Field, ValidationError
from pydantic_core import PydanticUndefined

from ..utils.language_utils import LanguageUtils


# ============================================================================
# TYPE DEFINITIONS AND STATE MANAGEMENT
# ============================================================================


class TranslationGraphState(TypedDict, total=False):
    """State container passed between LangGraph nodes.
    
    This TypedDict defines the structure of data flowing through the pipeline.
    Each key corresponds to the output of a specific processing stage.
    
    Attributes:
        synset: Input synset with lemmas, definition, examples, POS, etc.
        sense_analysis: Output from sense analysis stage
        definition_translation: Output from definition translation stage
        initial_translation_call: Output from initial lemma translation stage
        expansion_call: Output from synonym expansion stage (may contain multiple iterations)
    filtering_call: Output from synonym filtering stage
    definition_quality_call: Output from definition quality review stage
        result: Final assembled result
    """

    synset: Dict[str, Any]
    sense_analysis: Dict[str, Any]
    definition_translation: Dict[str, Any]
    
    # Multi-step synonym translation (generate-and-filter approach)
    initial_translation_call: Dict[str, Any]
    expansion_call: Dict[str, Any]
    filtering_call: Dict[str, Any]
    definition_quality_call: Dict[str, Any]
    
    result: Dict[str, Any]


@dataclass
class TranslationResult:
    """Structured output returned by the LangGraph translation pipeline.
    
    This dataclass encapsulates all information about a translated synset,
    including the final synonyms, intermediate outputs, metadata, and domain information.
    
    Attributes:
        translation: Representative literal (first synonym) for display purposes
        definition_translation: Translated gloss/definition in target language
        translated_synonyms: List of validated, deduplicated synonyms (the final synset)
        target_lang: Target language code (e.g., 'sr' for Serbian)
        source_lang: Source language code (e.g., 'en' for English)
        source: Original input synset dictionary
        examples: Translated usage examples in target language
        notes: Optional lexicographer notes or translation commentary
        raw_response: Full untruncated LLM output from all stages
        payload: Structured outputs from each pipeline stage
        curator_summary: Human-readable summary for manual review
        lexname: WordNet lexical file category (e.g., 'noun.artifact', 'verb.motion')
        topic_domains: Semantic field markers from WordNet (e.g., ['biochemistry.n.01'])
    
    Notes:
        - translation is NOT a headword; the synset is represented by translated_synonyms
        - payload contains full stage-by-stage results for debugging and analysis
        - lexname and topic_domains are auto-fetched from English WordNet via NLTK
    """

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
    lexname: Optional[str] = None
    topic_domains: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a serializable dictionary representation.
        
        Useful for JSON export, logging, or downstream processing.
        
        Returns:
            Dictionary with all fields, suitable for JSON serialization.
        """
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


# ============================================================================
# PYDANTIC SCHEMAS FOR VALIDATION
# ============================================================================
# These schemas define the expected structure of LLM outputs for each stage.
# Pydantic provides automatic validation, type checking, and error reporting.
# ============================================================================


class SenseAnalysisSchema(BaseModel):
    """Schema for validating sense analysis stage output.
    
    This stage analyzes the semantic nuances and context of the source synset
    before translation begins.
    
    Attributes:
        sense_summary: 1-2 sentence English description capturing the specific sense
        contrastive_note: What distinguishes this sense from other senses of the lemma
        key_features: List of salient semantic features
        domain_tags: Optional topical/domain tags (e.g., 'medical', 'legal')
        confidence: Overall confidence level (high/medium/low)
    """
    sense_summary: str = Field(..., min_length=3)
    contrastive_note: Optional[str] = None
    key_features: List[str] = Field(default_factory=list)
    domain_tags: Optional[List[str]] = Field(default_factory=list)
    confidence: str


class DefinitionTranslationSchema(BaseModel):
    """Schema for validating definition translation stage output.
    
    This stage translates the WordNet gloss/definition into the target language,
    maintaining dictionary-style brevity and neutrality.
    
    Attributes:
        definition_translation: Translated gloss in target language
        notes: Optional lexicographer comments or clarifications
        examples: Optional usage examples in target language
    """
    definition_translation: str
    notes: Optional[str] = None
    examples: Optional[List[str]] = Field(default_factory=list)


class LemmaTranslationSchema(BaseModel):
    """Schema for validating initial lemma translation stage output.
    
    This stage performs direct 1:1 translation of each English lemma,
    preserving array order and using null for untranslatable items.
    
    Attributes:
        initial_translations: List of translations (may contain None for untranslatable lemmas)
        alignment: Dictionary mapping source lemmas to their translations
    """
    initial_translations: List[Optional[str]]
    alignment: Dict[str, Optional[str]]


class ExpansionSchema(BaseModel):
    """Schema for validating synonym expansion stage output.
    
    This stage iteratively expands the synonym pool by generating additional
    target-language synonyms. May run multiple times until convergence.
    
    Attributes:
        expanded_synonyms: List of all candidate synonyms (initial + expanded)
        rationale: Optional justification for each added synonym
        iterations_run: Number of expansion iterations performed (default: 1)
        synonym_provenance: Tracks which iteration found each synonym (0=initial, 1+=iteration)
        converged: Whether expansion stopped early due to no new synonyms (True)
                   or hit max iterations (False)
    """
    expanded_synonyms: List[str]
    rationale: Optional[Dict[str, str]] = Field(default_factory=dict)
    iterations_run: Optional[int] = 1
    synonym_provenance: Optional[Dict[str, int]] = Field(default_factory=dict)
    converged: Optional[bool] = False


class FilteringSchema(BaseModel):
    """Schema for validating synonym filtering stage output.
    
    This stage performs quality control, removing candidates that don't precisely
    match the intended sense or exhibit other issues.
    
    Attributes:
        filtered_synonyms: Final list of high-quality synonyms
        confidence_by_word: Per-synonym confidence scores (high/medium/low)
        removed: List of rejected candidates with reasons for removal
        confidence: Overall confidence in the synset quality (high/medium/low)
    """
    filtered_synonyms: List[str]
    confidence_by_word: Optional[Dict[str, str]] = Field(default_factory=dict)
    removed: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    confidence: str


class DefinitionQualityIssue(BaseModel):
    """Schema for individual issues flagged during definition quality review."""

    type: Literal["circular", "grammar", "style"]
    message: str


class DefinitionQualitySchema(BaseModel):
    """Schema for validating post-filter definition quality review output."""

    status: Literal["ok", "needs_revision"]
    issues: List[DefinitionQualityIssue] = Field(default_factory=list)
    revised_definition: Optional[str] = None
    notes: Optional[str] = None


def validate_stage_payload(payload: dict, schema_cls: type[BaseModel], stage_name: str) -> dict:
    """Validate LLM JSON payload against expected schema with auto-repair.
    
    Attempts to validate the raw LLM output against a Pydantic schema. If validation
    fails, logs warnings and returns a fallback dictionary with required fields filled
    with sensible defaults.
    
    Args:
        payload: Raw dictionary from LLM output (after JSON parsing)
        schema_cls: Pydantic model class defining the expected structure
        stage_name: Pipeline stage name for logging (e.g., 'sense_analysis')
        
    Returns:
        Validated payload dictionary. If validation failed, returns a merged dictionary
        with defaults for missing/invalid fields.
        
    Example:
        >>> payload = {"sense_summary": "test", "confidence": "high"}
        >>> validated = validate_stage_payload(payload, SenseAnalysisSchema, "sense_analysis")
        >>> assert "key_features" in validated  # Auto-filled with default empty list
    """
    try:
        model = schema_cls(**payload)
        return model.model_dump()
    except ValidationError as e:
        print(f"[WARN] Validation failed for stage '{stage_name}': {e}")
        
        # Build fallback dictionary with sensible defaults
        fallback = {}
        for field_name, field_info in schema_cls.model_fields.items():
            if field_info.is_required():
                # Required fields get empty string
                fallback[field_name] = ""
            elif field_info.default is not PydanticUndefined:
                # Use explicit default value
                fallback[field_name] = field_info.default
            elif field_info.default_factory is not None:
                # Call factory function (e.g., list, dict, etc.)
                fallback[field_name] = field_info.default_factory()
            else:
                # No default - use None
                fallback[field_name] = None
        
        # Merge fallback with original payload (original values take precedence for valid fields)
        return {**fallback, **payload}


# ============================================================================
# MAIN PIPELINE CLASS
# ============================================================================


class LangGraphTranslationPipeline:
    """Multi-stage translation pipeline using LangGraph and Ollama.
    
    This pipeline orchestrates WordNet synset translation through a sophisticated
    generate-and-filter workflow with iterative expansion, quality validation,
    and automatic deduplication.
    
    The pipeline is designed for lexicographic quality, producing sets of validated
    synonyms rather than single headword translations.
    
    Class Constants:
        DEFAULT_SYSTEM_PROMPT: System message defining LLM role and expectations
        DEFAULT_PROMPT_TEMPLATE: Legacy template (deprecated, use stage-specific prompts)
        _PREVIEW_LIMIT: Maximum characters to show in log previews (600)
        _MAX_SYNONYMS_DISPLAY: Maximum synonyms to show in curator summary (5)
    
    Instance Attributes:
        source_lang: Source language code (e.g., 'en')
        target_lang: Target language code (e.g., 'sr')
        model: Ollama model name (e.g., 'gpt-oss:120b')
        temperature: LLM temperature (0.0-1.0, lower = more deterministic)
        base_url: Ollama API endpoint
        timeout: LLM request timeout in seconds
        system_prompt: System message sent with each LLM request
        prompt_template: Legacy template (not used in multi-stage pipeline)
        max_expansion_iterations: Maximum synonym expansion iterations (default: 5)
        llm: LangChain LLM instance
        _graph: Compiled LangGraph state machine
    
    Example:
        >>> pipeline = LangGraphTranslationPipeline(
        ...     source_lang="en",
        ...     target_lang="sr",
        ...     model="gpt-oss:120b",
        ...     max_expansion_iterations=5
        ... )
        >>> synset = {
        ...     "id": "eng-30-00001740-n",
        ...     "lemmas": ["entity"],
        ...     "definition": "that which is perceived or known or inferred...",
        ...     "pos": "n"
        ... }
        >>> result = pipeline.translate_synset(synset)
        >>> print(result["payload"]["filtering"]["filtered_synonyms"])
        ['entitet', 'biće', 'jedinica']
    """

    # ========================================================================
    # CLASS CONSTANTS
    # ========================================================================

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

    _PREVIEW_LIMIT: int = 600  # Log preview character limit
    _MAX_SYNONYMS_DISPLAY: int = 5  # Curator summary display limit

    # ========================================================================
    # INITIALIZATION
    # ========================================================================

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
        max_expansion_iterations: int = 5,
    ) -> None:
        """Initialize the LangGraph translation pipeline.
        
        Args:
            source_lang: Source language code (default: 'en')
            target_lang: Target language code (default: 'sr')
            model: Ollama model name (default: 'gpt-oss:120b')
            temperature: LLM temperature 0.0-1.0 (default: 0.2 for determinism)
            base_url: Ollama API endpoint (default: 'http://localhost:11434')
            timeout: Request timeout in seconds (default: 600 = 10 minutes)
            system_prompt: Custom system message (optional, uses DEFAULT_SYSTEM_PROMPT if None)
            prompt_template: Legacy template (deprecated, not used in multi-stage pipeline)
            llm: Pre-configured LangChain LLM instance (optional, will create if None)
            max_expansion_iterations: Maximum synonym expansion iterations (default: 5)
        
        Raises:
            ImportError: If required dependencies (langgraph, langchain_ollama) not installed
        
        Notes:
            - The pipeline automatically builds a LangGraph state machine on initialization
            - If llm is None, creates a ChatOllama instance with the specified configuration
            - Temperature 0.0 = fully deterministic, 1.0 = maximum creativity
        """
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.model = model
        self.temperature = temperature
        self.base_url = base_url
        self.timeout = timeout
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.prompt_template = prompt_template or self.DEFAULT_PROMPT_TEMPLATE
        self.max_expansion_iterations = max_expansion_iterations

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

        # Build and compile the LangGraph state machine
        self._graph = self._build_graph()

    # ========================================================================
    # GRAPH CONSTRUCTION
    # ========================================================================

    @staticmethod
    def _load_dependencies(provided_llm: Optional[Any]):
        """Dynamically import LangGraph and Ollama dependencies.
        
        This method lazy-loads the required libraries to avoid import errors
        when the user hasn't installed the optional dependencies.
        
        Args:
            provided_llm: Optional pre-configured LLM instance. If None, will
                         also import ChatOllama for creating a new LLM.
        
        Returns:
            Tuple of (StateGraph, START, END, SystemMessage, HumanMessage, chat_factory)
            where chat_factory is None if provided_llm was given, or ChatOllama otherwise.
        
        Raises:
            ImportError: If required dependencies are not installed.
        """

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
        """Build and compile the LangGraph state machine for the translation pipeline.
        
        Constructs a directed graph with 7 stages:
            1. **analyse_sense**: Understand semantic nuances before translation
            2. **translate_definition**: Translate the gloss with cultural adaptation
            3. **translate_all_lemmas**: Direct 1:1 translation of each English lemma
            4. **expand_synonyms**: Iteratively broaden the candidate pool (up to max_expansion_iterations)
            5. **filter_synonyms**: Quality check with per-word confidence scores
            6. **review_definition_quality**: Final pass for grammatical and stylistic polish
            7. **assemble_result**: Combine outputs, deduplicate, format final synset
        
        The graph uses a linear pipeline architecture (no branching or loops).
        Each stage receives the accumulated state and adds its results.
        
        Returns:
            Compiled LangGraph application ready for execution.
        
        Notes:
            - The graph is stateless between synsets (each translation is independent)
            - State flows sequentially through all 7 stages
            - Each node is a method of this class (e.g., self._analyse_sense)
        """
        graph = self._StateGraph(TranslationGraphState)
        graph.add_node("analyse_sense", self._analyse_sense)
        graph.add_node("translate_definition", self._translate_definition)
        graph.add_node("translate_all_lemmas", self._translate_all_lemmas)
        graph.add_node("expand_synonyms", self._expand_synonyms)
        graph.add_node("filter_synonyms", self._filter_synonyms)
        graph.add_node("review_definition_quality", self._review_definition_quality)
        graph.add_node("assemble_result", self._assemble_result)

        graph.add_edge(self._START, "analyse_sense")
        graph.add_edge("analyse_sense", "translate_definition")
        graph.add_edge("translate_definition", "translate_all_lemmas")
        graph.add_edge("translate_all_lemmas", "expand_synonyms")
        graph.add_edge("expand_synonyms", "filter_synonyms")
        graph.add_edge("filter_synonyms", "review_definition_quality")
        graph.add_edge("review_definition_quality", "assemble_result")
        graph.add_edge("assemble_result", self._END)

        return graph.compile()

    # ========================================================================
    # PUBLIC API METHODS
    # ========================================================================

    def translate_synset(self, synset: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a single synset and return a structured dictionary.
        
    This is the primary entry point for translating individual synsets.
    The method invokes the complete 7-stage pipeline and returns all results.
        
        Args:
            synset: Dictionary containing synset data with fields:
                   - id: Synset ID (e.g., 'eng-30-00001740-n')
                   - lemmas: List of English words (e.g., ['entity'])
                   - definition: WordNet gloss
                   - pos: Part of speech ('n', 'v', 'a', 'r')
                   - examples: Optional list of usage examples
        
        Returns:
            Dictionary containing:
                - translation: Representative literal (first synonym)
                - translated_synonyms: Full list of validated synonyms
                - definition_translation: Translated gloss
                - payload: Complete stage-by-stage outputs
                - curator_summary: Human-readable summary
                - lexname: WordNet lexical file category
                - topic_domains: Semantic field markers
                And other metadata fields
        
        Example:
            >>> result = pipeline.translate_synset({
            ...     "id": "eng-30-00001740-n",
            ...     "lemmas": ["entity"],
            ...     "definition": "that which is perceived...",
            ...     "pos": "n"
            ... })
            >>> print(result["translated_synonyms"])
            ['entitet', 'biće', 'jedinica']
        """

        state = self._graph.invoke({"synset": synset})
        result: TranslationResult = state["result"]  # type: ignore[index]
        return result.to_dict()

    def translate(self, synsets: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Translate a batch of synsets sequentially.
        
        Convenience method for translating multiple synsets. Each synset is
        processed independently through the full pipeline.
        
        Args:
            synsets: Sequence of synset dictionaries (same format as translate_synset)
        
        Returns:
            List of translation result dictionaries, one per input synset.
        
        Notes:
            - Processing is sequential (not parallel)
            - Each synset takes ~5-10 minutes with iterative expansion
            - For large batches, consider using translate_stream for memory efficiency
        """

        return [self.translate_synset(synset) for synset in synsets]

    def translate_stream(
        self, synsets: Iterable[Dict[str, Any]]
    ) -> Generator[Dict[str, Any], None, None]:
        """Generator variant that yields translations as they complete.
        
        Memory-efficient alternative to translate() for large batches.
        Results are yielded one at a time as they finish processing.
        
        Args:
            synsets: Iterable of synset dictionaries
        
        Yields:
            Translation result dictionaries, one at a time.
        
        Example:
            >>> for result in pipeline.translate_stream(large_dataset):
            ...     save_to_database(result)  # Process incrementally
        """

        for synset in synsets:
            yield self.translate_synset(synset)

    # ========================================================================
    # LANGGRAPH NODE METHODS (Pipeline Stages)
    # ========================================================================
    # Each method below corresponds to one stage in the 7-stage pipeline.
    # They are invoked by the LangGraph state machine in sequence.
    # ========================================================================

    def _analyse_sense(self, state: TranslationGraphState) -> TranslationGraphState:
        """LangGraph node: Analyze synset sense before translation.
        
        This is Stage 1 of 6. Examines the source synset to understand
        semantic nuances, distinguish from other senses, and identify key features.
        
        Args:
            state: Current graph state containing synset data.
            
        Returns:
            Updated state with sense_analysis results including:
                - sense_summary: 1-2 sentence description
                - contrastive_note: What makes this sense unique
                - key_features: Salient semantic properties
                - confidence: Overall confidence level
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
        
        This runs expansion iteratively (up to max_expansion_iterations times)
        until no new synonyms appear, accumulating unique synonyms across runs.
        
        Args:
            state: Current graph state with initial translations.
            
        Returns:
            Updated state with expansion_call results including iteration metadata.
        """
        initial_payload = state.get("initial_translation_call", {}).get("payload", {})
        sense_payload = state.get("sense_analysis", {}).get("payload", {})
        definition_payload = state.get("definition_translation", {}).get("payload", {})
        
        # Start with initial translations
        initial_translations = initial_payload.get("initial_translations", [])
        all_synonyms = set(t for t in initial_translations if t is not None)
        
        # Track which iteration found which synonym
        synonym_provenance = {syn: 0 for syn in all_synonyms}  # 0 = initial
        all_rationales = {}
        iteration_calls = []
        new_count = 0  # Initialize before loop
        
        for iteration in range(self.max_expansion_iterations):
            # Generate prompt with current synonym set
            prompt = self._render_expansion_prompt(initial_payload, sense_payload, definition_payload)
            
            # Call LLM
            call_result = self._call_llm(prompt, stage=f"expansion_iter_{iteration+1}")
            iteration_calls.append(call_result)
            
            # Extract new synonyms
            payload = call_result.get("payload", {})
            if "error" in payload:
                # Stop on error
                break
                
            new_expanded = payload.get("expanded_synonyms", [])
            new_rationale = payload.get("rationale", {})
            
            # Check for convergence
            before_count = len(all_synonyms)
            
            for syn in new_expanded:
                if syn and syn not in all_synonyms:
                    all_synonyms.add(syn)
                    synonym_provenance[syn] = iteration + 1
                    if syn in new_rationale:
                        all_rationales[syn] = new_rationale[syn]
            
            new_count = len(all_synonyms) - before_count
            
            # Early stopping if no new synonyms
            if new_count == 0:
                print(f"[Expansion] Converged after {iteration + 1} iteration(s) - no new synonyms found")
                break
            else:
                print(f"[Expansion] Iteration {iteration + 1}: Added {new_count} new synonym(s), total: {len(all_synonyms)}")
        
        # Construct final result
        final_payload = {
            "expanded_synonyms": sorted(all_synonyms),
            "rationale": all_rationales,
            "iterations_run": iteration + 1,
            "synonym_provenance": synonym_provenance,
            "converged": new_count == 0
        }
        
        final_call_result = {
            "payload": final_payload,
            "stage": "synonym_expansion",
            "calls": iteration_calls,  # All LLM calls made
            "response": f"Iterative expansion completed in {iteration + 1} iteration(s)"
        }
        
        return {"expansion_call": final_call_result}

    def _filter_synonyms(self, state: TranslationGraphState) -> TranslationGraphState:
        """LangGraph node: Filter and validate synonym candidates.

        This stage performs a quality check to remove candidates that don't precisely match the
        intended sense, ensuring high-quality output before the final definition review.

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

    def _review_definition_quality(self, state: TranslationGraphState) -> TranslationGraphState:
        """LangGraph node: Review translated definition for grammar and style."""

        filtering_payload = state.get("filtering_call", {}).get("payload", {})
        definition_payload = state.get("definition_translation", {}).get("payload", {})

        filtered_synonyms = filtering_payload.get("filtered_synonyms", [])
        definition_translation = str(definition_payload.get("definition_translation", "") or "")

        prompt = self._render_definition_quality_prompt(
            filtered_synonyms,
            definition_translation,
            self.target_lang,
        )

        call_result = self._call_llm(prompt, stage="definition_quality")
        return {"definition_quality_call": call_result}

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
        """Generate prompt for synonym expansion stage (revised: prevents semantic drift).
        
        This revised prompt emphasizes alignment with the core concept to prevent
        expansion into homonyms or polysemous translations. It instructs the LLM
        to reason from the concept itself rather than surface word similarity.
        
        Args:
            initial_payload: Output from initial translation stage.
            sense_payload: Output from sense analysis stage.
            definition_payload: Output from definition translation stage.
            
        Returns:
            Formatted prompt for LLM that prevents semantic drift across senses.
        """
        target_name = LanguageUtils.get_language_name(self.target_lang)
        initial_translations = initial_payload.get("initial_translations", [])
        # Filter out null values from initial translations
        initial_translations = [t for t in initial_translations if t is not None]
        base_synonyms = ", ".join(str(t) for t in initial_translations) if initial_translations else "(none)"
        
        sense_summary = sense_payload.get("sense_summary", "")
        definition_translation = definition_payload.get("definition_translation", "")

        prompt = textwrap.dedent(
            f"""
            You are expanding a synonym set for a WordNet synset in {target_name}.

            Core meaning (sense summary):
            {sense_summary or "(no summary available)"}

            Translated definition (for reference):
            {definition_translation or "(not available)"}

            Existing {target_name} translations:
            {base_synonyms}

            Guidelines:
            - Generate new synonyms that express **exactly this concept**, not other senses of the same word.
            - Stay faithful to the described meaning and avoid extensions that fit different senses.
            - Exclude expressions that refer to locations, titles, or figurative uses unless the definition requires them.
            - Do not rely on surface similarity to the existing words; reason from the concept itself.
            - Keep to canonical lemma forms and natural, modern vocabulary.

            Return JSON:
            {{
              "expanded_synonyms": ["lemma1", "lemma2", ...],
              "rationale": {{
                 "lemma1": "explanation of conceptual alignment",
                 "lemma2": "explanation of conceptual alignment"
              }}
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
        """Definition-anchored filtering prompt with balanced scope and hypernym control.

        This version emphasizes strict alignment with the translated definition,
        robust handling of morphological and polysemous variants, and removal
        of overly generic or compositional forms.
        
        Args:
            expansion_payload: Output from expansion stage.
            sense_payload: Output from sense analysis stage.
            definition_payload: Output from definition translation stage.
            
        Returns:
            Formatted prompt for LLM with definition-anchored validation and polysemy awareness.
        """
        target_name = LanguageUtils.get_language_name(self.target_lang)
        expanded_synonyms = expansion_payload.get("expanded_synonyms", [])
        expanded = ", ".join(str(t) for t in expanded_synonyms) if expanded_synonyms else "(none)"
        
        sense_summary = sense_payload.get("sense_summary", "")
        definition_translation = definition_payload.get("definition_translation", "")

        prompt = textwrap.dedent(
            f"""
            Final validation of {target_name} synonym candidates.

            Candidates: {expanded}

            Sense summary: {sense_summary or "(no summary available)"}
            Definition (translated): {definition_translation or "(not available)"}

            Guidelines:
            - Evaluate each candidate strictly against the definition, not surface similarity.
            - Keep words that express the same central meaning or a culturally natural equivalent.
            - Prefer base lemmas, but also keep aspectual or derivational variants if they express
              the same action, state, or entity type.
            - When a candidate's meaning naturally spans multiple related interpretations
              (e.g., an entity and its location, or an organization and its premises),
              treat this as normal lexical polysemy. Keep the word if at least one of its
              established interpretations clearly fits the definition, even if others do not.
            - Remove candidates that merely restate the generic hypernym from the definition
              (for instance, a term meaning only "object" or "building" when the sense is a specific kind).
            - Remove expressions with added modifiers, particles, or typical objects that narrow or
              shift the intended scope.
            - Retain idiomatic forms only if they are genuinely used interchangeably with the target concept.

            Return structured JSON:
            {{
              "filtered_synonyms": ["lemma1", "lemma2"],
              "confidence_by_word": {{"lemma1": "high", "lemma2": "medium"}},
              "removed": [{{"word": "X", "reason": "too generic / mismatched sense"}}],
              "confidence": "high|medium|low"
            }}
            """
        ).strip()

        return prompt

    def _render_definition_quality_prompt(
        self,
        filtered_synonyms: List[str],
        definition_translation: str,
        target_lang: str,
    ) -> str:
        """Post-filter definition quality check prompt.

        Performs a neutral, language-independent review for grammatical agreement,
        fluency, and stylistic clarity of the translated definition.
        """

        expanded = ", ".join(filtered_synonyms) if filtered_synonyms else "(none)"
        target_name = LanguageUtils.get_language_name(target_lang)

        prompt = textwrap.dedent(
            f"""
            Evaluate the linguistic and stylistic quality of this {target_name} dictionary definition.

            Definition:
            "{definition_translation}"

            Synonyms (lemmas):
            {expanded}

            Tasks:
            1. **Circularity** — Check if any lemma word or its close inflectional form
               appears directly in the definition, which would create a circular definition.
               If this occurs, suggest a neutral rephrasing that avoids repetition.

            2. **Grammar and agreement** — Verify correctness of inflection, case,
               number, and gender, as appropriate for {target_name}. Identify ungrammatical
               or mechanically translated phrasing.

            3. **Style and fluency** — Ensure the definition is concise, clear, and
               natural in the lexicographic register of {target_name}. Prefer balanced
               clause structure and neutral tone over heavy nominalization or literal phrasing.

            4. If any issues are detected, produce a corrected version that maintains
               the original meaning while improving grammar and style.

            Return structured JSON:
            {{
              "status": "ok" | "needs_revision",
              "issues": [
                {{"type": "circular" | "grammar" | "style", "message": "brief explanation"}},
              ],
              "revised_definition": "rewritten definition if revision is required, otherwise original",
              "notes": "short summary of evaluation outcome"
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
            "definition_quality": DefinitionQualitySchema,
        }
        schema_cls = schema_map.get(stage)
        if schema_cls:
            return validate_stage_payload(payload, schema_cls, stage)
        return payload

    # ==============================================================
    # Deduplication helper: removes redundant compounds and modifiers
    # ==============================================================

    def _deduplicate_compounds(self, words: list[str]) -> list[str]:
        """Remove multiword expressions that contain any single-word lemma as a token.
        
        This prevents redundancy where both a base word and its compound variants
        appear in the same synset.
        
        Example:
            Input: ['ustanova', 'centar', 'administrativni centar', 'sedište']
            Output: ['ustanova', 'centar', 'sedište']
            (Removes 'administrativni centar' because 'centar' exists as single word)
        
        Args:
            words: List of candidate synonyms (may include multiword expressions)
            
        Returns:
            Cleaned list with redundant compounds removed
        """
        words = [w.strip().lower() for w in words if w.strip()]
        singles = {w for w in words if " " not in w}
        cleaned, flagged = [], []

        for w in words:
            if " " in w and any(f" {s} " in f" {w} " for s in singles):
                flagged.append(w)
            else:
                cleaned.append(w)

        if flagged:
            print(f"[Deduplicate] Flagged: {flagged}")
        return cleaned

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
        definition_quality_call = state.get("definition_quality_call", {}) or {}

        sense_payload = sense_call.get("payload", {}) or {}
        definition_payload = definition_call.get("payload", {}) or {}
        initial_payload = initial_call.get("payload", {}) or {}
        expansion_payload = expansion_call.get("payload", {}) or {}
        filtering_payload = filtering_call.get("payload", {}) or {}
        definition_quality_payload = definition_quality_call.get("payload", {}) or {}

        definition_translation = str(
            definition_payload.get("definition_translation", "")
        ).strip()

        quality_status = str(definition_quality_payload.get("status", "") or "").lower()
        quality_revision = definition_quality_payload.get("revised_definition")
        if isinstance(quality_revision, str):
            quality_revision_text = quality_revision.strip()
        elif quality_revision is not None:
            quality_revision_text = str(quality_revision).strip()
        else:
            quality_revision_text = ""

        if quality_revision_text and (
            quality_status == "needs_revision" or not definition_translation
        ):
            definition_translation = quality_revision_text

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

        # Apply compound deduplication to remove redundant multiword expressions
        translated_synonyms = self._deduplicate_compounds(translated_synonyms)

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
        definition_notes = definition_payload.get("notes")
        quality_notes = definition_quality_payload.get("notes")
        primary_note = str(definition_notes).strip() if definition_notes and str(definition_notes).strip() else ""
        fallback_note = str(quality_notes).strip() if quality_notes and str(quality_notes).strip() else ""
        notes = primary_note or fallback_note or None

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
        issues = definition_quality_payload.get("issues") or []
        issues_count = len(issues) if isinstance(issues, list) else 0
        status_label = quality_status or "unknown"
        issue_suffix = f" ({issues_count} issue(s) flagged)" if issues_count else ""
        summary_lines.append(f"  4. Definition quality: {status_label}{issue_suffix}")

        curator_summary = "\n".join(summary_lines)

        combined_payload: Dict[str, Any] = {
            "sense": sense_payload,
            "definition": definition_payload,
            "initial_translation": initial_payload,
            "expansion": expansion_payload,
            "filtering": filtering_payload,
            "definition_quality": definition_quality_payload,
            "calls": {
                "sense": sense_call,
                "definition": definition_call,
                "initial_translation": initial_call,
                "expansion": expansion_call,
                "filtering": filtering_call,
                "definition_quality": definition_quality_call,
            },
            "logs": {
                "sense": self._summarise_call(sense_call),
                "definition": self._summarise_call(definition_call),
                "initial_translation": self._summarise_call(initial_call),
                "expansion": self._summarise_call(expansion_call),
                "filtering": self._summarise_call(filtering_call),
                "definition_quality": self._summarise_call(definition_quality_call),
            },
        }

        raw_response = (
            definition_quality_call.get("raw_response")
            or filtering_call.get("raw_response") 
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