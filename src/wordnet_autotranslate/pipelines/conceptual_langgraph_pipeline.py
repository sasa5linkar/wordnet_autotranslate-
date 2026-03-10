"""Concept-oriented LangGraph pipeline for Serbian WordNet drafting.

This module keeps the existing generate-and-filter pipeline intact while adding
an alternative multi-phase workflow closer to lexicographic analysis:

1. extract_concept
2. expand_definition_en
3. expand_definition_sr
4. generate_literal_candidates
5. select_literals
6. build_final_gloss
7. validate_synset
8. assemble_result

The class reuses the same LangGraph/Ollama model configuration as the existing
``LangGraphTranslationPipeline`` so results can be compared side by side.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import textwrap
from typing import Any, Dict, Generator, Iterable, List, Optional, Sequence, TypedDict

from pydantic import BaseModel, Field

from ..utils.language_utils import LanguageUtils
from .langgraph_translation_pipeline import (
    LangGraphTranslationPipeline,
    validate_stage_payload,
)


class RelatedSynsetSchema(BaseModel):
    """Minimal related-synset representation used in the concept package."""

    synset_id: str = ""
    literals: List[str] = Field(default_factory=list)
    gloss: str = ""


class ConceptPackageSchema(BaseModel):
    """Language-agnostic concept bundle extracted from the source synset."""

    synset_id: str = ""
    pos: str = ""
    source_literals: List[str] = Field(default_factory=list)
    source_gloss: str = ""
    examples: List[str] = Field(default_factory=list)
    hypernyms: List[RelatedSynsetSchema] = Field(default_factory=list)
    hyponyms: List[RelatedSynsetSchema] = Field(default_factory=list)
    meronyms: List[RelatedSynsetSchema] = Field(default_factory=list)
    holonyms: List[RelatedSynsetSchema] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    sister_synsets: List[RelatedSynsetSchema] = Field(default_factory=list)
    anti_circularity_blocklist_en: List[str] = Field(default_factory=list)


class ExpandedEnglishOutputSchema(BaseModel):
    """Expanded English semantic definition."""

    expanded_definition_en: str = ""
    blocked_terms_en: List[str] = Field(default_factory=list)
    notes_en: List[str] = Field(default_factory=list)


class ExpandedSerbianOutputSchema(BaseModel):
    """Expanded Serbian semantic definition."""

    expanded_definition_sr: str = ""
    blocked_terms_sr: List[str] = Field(default_factory=list)
    notes_sr: List[str] = Field(default_factory=list)


class LiteralCandidateSchema(BaseModel):
    """Candidate Serbian literal for the target concept."""

    literal: str = ""
    candidate_type: str = ""
    precision_score: float = Field(default=0.0, ge=0.0, le=1.0)
    naturalness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str = ""
    fit_assessment: str = ""
    register_note: str = ""


class LiteralCandidatesOutputSchema(BaseModel):
    """Collection of Serbian literal candidates."""

    candidates: List[LiteralCandidateSchema] = Field(default_factory=list)


class LiteralSelectionOutputSchema(BaseModel):
    """Final literal selection decision."""

    selected_literals_sr: List[str] = Field(default_factory=list)
    rejected_literals_sr: List[str] = Field(default_factory=list)
    rationale_sr: str = ""


class FinalGlossOutputSchema(BaseModel):
    """Short final Serbian WordNet gloss."""

    final_gloss_sr: str = ""
    style_notes_sr: List[str] = Field(default_factory=list)


class ValidationIssueSchema(BaseModel):
    """Validation issue produced by the final checking stage."""

    code: str = ""
    message: str = ""
    severity: str = "info"


class ValidationOutputSchema(BaseModel):
    """Validation summary for the drafted Serbian synset."""

    validation_passed: bool = False
    issues: List[ValidationIssueSchema] = Field(default_factory=list)
    final_synset_ready: bool = False


class ConceptualTranslationGraphState(TypedDict, total=False):
    """State container passed through the concept-oriented LangGraph pipeline."""

    synset: Dict[str, Any]
    concept_package: Dict[str, Any]
    expanded_en_call: Dict[str, Any]
    expanded_sr_call: Dict[str, Any]
    literal_candidates_call: Dict[str, Any]
    literal_selection_call: Dict[str, Any]
    final_gloss_call: Dict[str, Any]
    validation_call: Dict[str, Any]
    result: Dict[str, Any]


@dataclass
class ConceptualTranslationResult:
    """Structured output for the concept-oriented Serbian pipeline."""

    translation: str
    selected_literals_sr: List[str]
    rejected_literals_sr: List[str]
    final_gloss_sr: str
    target_lang: str
    source_lang: str
    source: Dict[str, Any]
    concept_package: Dict[str, Any]
    expanded_en: Dict[str, Any]
    expanded_sr: Dict[str, Any]
    candidates: Dict[str, Any]
    selection: Dict[str, Any]
    final_gloss: Dict[str, Any]
    validation: Dict[str, Any]
    payload: Dict[str, Any]
    raw_response: str
    curator_summary: str

    def to_dict(self) -> Dict[str, Any]:
        """Return a serializable representation for downstream consumers."""

        return {
            "translation": self.translation,
            "selected_literals_sr": self.selected_literals_sr,
            "rejected_literals_sr": self.rejected_literals_sr,
            "final_gloss_sr": self.final_gloss_sr,
            "target_lang": self.target_lang,
            "source_lang": self.source_lang,
            "source": self.source,
            "concept_package": self.concept_package,
            "expanded_en": self.expanded_en,
            "expanded_sr": self.expanded_sr,
            "candidates": self.candidates,
            "selection": self.selection,
            "final_gloss": self.final_gloss,
            "validation": self.validation,
            "payload": self.payload,
            "raw_response": self.raw_response,
            "curator_summary": self.curator_summary,
        }


class ConceptualLangGraphTranslationPipeline(LangGraphTranslationPipeline):
    """Alternative LangGraph pipeline based on a concept package workflow."""

    def _build_graph(self) -> Any:
        """Build and compile the concept-oriented LangGraph state machine."""

        graph = self._StateGraph(ConceptualTranslationGraphState)
        graph.add_node("extract_concept", self._extract_concept)
        graph.add_node("expand_definition_en", self._expand_definition_en)
        graph.add_node("expand_definition_sr", self._expand_definition_sr)
        graph.add_node("generate_literal_candidates", self._generate_literal_candidates)
        graph.add_node("select_literals", self._select_literals)
        graph.add_node("build_final_gloss", self._build_final_gloss)
        graph.add_node("validate_synset", self._validate_synset)
        graph.add_node("assemble_result", self._assemble_result)

        graph.add_edge(self._START, "extract_concept")
        graph.add_edge("extract_concept", "expand_definition_en")
        graph.add_edge("expand_definition_en", "expand_definition_sr")
        graph.add_edge("expand_definition_sr", "generate_literal_candidates")
        graph.add_edge("generate_literal_candidates", "select_literals")
        graph.add_edge("select_literals", "build_final_gloss")
        graph.add_edge("build_final_gloss", "validate_synset")
        graph.add_edge("validate_synset", "assemble_result")
        graph.add_edge("assemble_result", self._END)

        return graph.compile()

    def translate_synset(self, synset: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a single synset via the concept-oriented Serbian workflow."""

        state = self._graph.invoke({"synset": synset})
        result: ConceptualTranslationResult = state["result"]  # type: ignore[index]
        return result.to_dict()

    def translate(self, synsets: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Translate a batch of synsets sequentially."""

        return [self.translate_synset(synset) for synset in synsets]

    def translate_stream(
        self, synsets: Iterable[Dict[str, Any]]
    ) -> Generator[Dict[str, Any], None, None]:
        """Yield concept-oriented results one by one."""

        for synset in synsets:
            yield self.translate_synset(synset)

    def _validate_payload_for_stage(self, stage: str, payload: dict) -> dict:
        """Validate concept-pipeline payloads and fall back to the base schemas."""

        schema_map = {
            "expanded_definition_en": ExpandedEnglishOutputSchema,
            "expanded_definition_sr": ExpandedSerbianOutputSchema,
            "literal_candidates_sr": LiteralCandidatesOutputSchema,
            "literal_selection_sr": LiteralSelectionOutputSchema,
            "final_gloss_sr": FinalGlossOutputSchema,
            "synset_validation_sr": ValidationOutputSchema,
        }
        schema_cls = schema_map.get(stage)
        if schema_cls:
            return validate_stage_payload(payload, schema_cls, stage)
        return super()._validate_payload_for_stage(stage, payload)

    def _extract_concept(
        self, state: ConceptualTranslationGraphState
    ) -> ConceptualTranslationGraphState:
        """Create a language-agnostic concept package from the source synset."""

        synset = state["synset"]
        lemmas = synset.get("lemmas") or synset.get("literals") or []
        if not isinstance(lemmas, (list, tuple)):
            lemmas = [lemmas]
        source_literals = [str(lemma).strip() for lemma in lemmas if str(lemma).strip()]

        raw_pos = str(synset.get("pos") or synset.get("part_of_speech") or "").strip()
        english_pos = LanguageUtils.normalize_pos_for_english(raw_pos)

        synset_id = str(
            synset.get("id") or synset.get("english_id") or synset.get("ili_id") or ""
        ).strip()
        domain_info = self._get_wordnet_domain_info(synset_id)

        domains = self._coerce_to_str_list(synset.get("domains"))
        if not domains:
            domains = self._coerce_to_str_list(synset.get("domain_tags"))
        domains.extend(self._coerce_to_str_list(synset.get("lexname")))
        if domain_info.get("lexname"):
            domains.append(str(domain_info["lexname"]).strip())
        domains.extend(
            str(item).strip() for item in domain_info.get("topic_domains", [])
        )

        concept_package = ConceptPackageSchema(
            synset_id=synset_id,
            pos=english_pos or raw_pos,
            source_literals=source_literals,
            source_gloss=str(
                synset.get("definition") or synset.get("gloss") or ""
            ).strip(),
            examples=[
                str(example).strip()
                for example in (synset.get("examples") or [])
                if str(example).strip()
            ],
            hypernyms=self._normalise_related_synsets(synset.get("hypernyms")),
            hyponyms=self._normalise_related_synsets(synset.get("hyponyms")),
            meronyms=self._normalise_related_synsets(synset.get("meronyms")),
            holonyms=self._normalise_related_synsets(synset.get("holonyms")),
            sister_synsets=self._normalise_related_synsets(
                synset.get("sister_synsets") or synset.get("similar_synsets")
            ),
            domains=self._dedupe_list(domains),
            anti_circularity_blocklist_en=self._build_blocklist(source_literals),
        )
        return {"concept_package": concept_package.model_dump()}

    def _expand_definition_en(
        self, state: ConceptualTranslationGraphState
    ) -> ConceptualTranslationGraphState:
        """Generate an expanded English semantic definition."""

        concept_package = state["concept_package"]
        prompt = self._render_expanded_definition_en_prompt(concept_package)
        call_result = self._call_llm(prompt, stage="expanded_definition_en")
        return {"expanded_en_call": call_result}

    def _expand_definition_sr(
        self, state: ConceptualTranslationGraphState
    ) -> ConceptualTranslationGraphState:
        """Generate an expanded Serbian semantic definition."""

        concept_package = state["concept_package"]
        expanded_en = state.get("expanded_en_call", {}).get("payload", {})
        prompt = self._render_expanded_definition_sr_prompt(
            concept_package, expanded_en
        )
        call_result = self._call_llm(prompt, stage="expanded_definition_sr")
        return {"expanded_sr_call": call_result}

    def _generate_literal_candidates(
        self, state: ConceptualTranslationGraphState
    ) -> ConceptualTranslationGraphState:
        """Propose Serbian literal candidates from the expanded definition."""

        concept_package = state["concept_package"]
        expanded_sr = state.get("expanded_sr_call", {}).get("payload", {})
        prompt = self._render_literal_candidates_prompt(concept_package, expanded_sr)
        call_result = self._call_llm(prompt, stage="literal_candidates_sr")
        return {"literal_candidates_call": call_result}

    def _select_literals(
        self, state: ConceptualTranslationGraphState
    ) -> ConceptualTranslationGraphState:
        """Choose the final Serbian literals."""

        concept_package = state["concept_package"]
        expanded_sr = state.get("expanded_sr_call", {}).get("payload", {})
        literal_candidates = state.get("literal_candidates_call", {}).get("payload", {})
        prompt = self._render_literal_selection_prompt(
            concept_package, expanded_sr, literal_candidates
        )
        call_result = self._call_llm(prompt, stage="literal_selection_sr")
        return {"literal_selection_call": call_result}

    def _build_final_gloss(
        self, state: ConceptualTranslationGraphState
    ) -> ConceptualTranslationGraphState:
        """Produce the final short Serbian WordNet gloss."""

        concept_package = state["concept_package"]
        expanded_sr = state.get("expanded_sr_call", {}).get("payload", {})
        selection = state.get("literal_selection_call", {}).get("payload", {})
        prompt = self._render_final_gloss_prompt(
            concept_package, expanded_sr, selection
        )
        call_result = self._call_llm(prompt, stage="final_gloss_sr")
        return {"final_gloss_call": call_result}

    def _validate_synset(
        self, state: ConceptualTranslationGraphState
    ) -> ConceptualTranslationGraphState:
        """Validate the drafted Serbian synset."""

        concept_package = state["concept_package"]
        expanded_sr = state.get("expanded_sr_call", {}).get("payload", {})
        selection = state.get("literal_selection_call", {}).get("payload", {})
        final_gloss = state.get("final_gloss_call", {}).get("payload", {})
        prompt = self._render_validation_prompt(
            concept_package, expanded_sr, selection, final_gloss
        )
        call_result = self._call_llm(prompt, stage="synset_validation_sr")
        return {"validation_call": call_result}

    def _render_expanded_definition_en_prompt(
        self, concept_package: Dict[str, Any]
    ) -> str:
        """Render the prompt for the expanded English definition stage."""

        concept_json = self._to_pretty_json(concept_package)
        return textwrap.dedent(f"""
            Create an expanded English semantic definition for a WordNet synset.

            Rules:
            - Preserve the exact synset meaning.
            - Be richer than the original gloss while staying faithful.
            - Prefer genus + differentia wording when possible.
            - Do not introduce unsupported encyclopedic facts.
            - Avoid circularity by not using blocked source literals as defining terms.

            Return JSON:
            {{
              "expanded_definition_en": "coherent expanded definition",
              "blocked_terms_en": ["literal1", "literal2"],
              "notes_en": ["brief note", "brief note"]
            }}

            Concept package:
            {concept_json}
            """).strip()

    def _render_expanded_definition_sr_prompt(
        self,
        concept_package: Dict[str, Any],
        expanded_en: Dict[str, Any],
    ) -> str:
        """Render the prompt for the expanded Serbian definition stage."""

        concept_json = self._to_pretty_json(concept_package)
        expanded_en_json = self._to_pretty_json(expanded_en)
        return textwrap.dedent(f"""
            Translate and adapt the expanded English semantic definition into Serbian.

            Rules:
            - Preserve the exact meaning.
            - Do not add new facts.
            - Use natural Serbian lexicographic language.
            - Keep the definition semantically explicit because it will drive literal extraction.
            - Avoid circularity where possible.

            Return JSON:
            {{
              "expanded_definition_sr": "expanded Serbian semantic definition",
              "blocked_terms_sr": ["term1", "term2"],
              "notes_sr": ["brief note", "brief note"]
            }}

            Concept package:
            {concept_json}

            Expanded English output:
            {expanded_en_json}
            """).strip()

    def _render_literal_candidates_prompt(
        self,
        concept_package: Dict[str, Any],
        expanded_sr: Dict[str, Any],
    ) -> str:
        """Render the prompt for Serbian literal candidate generation."""

        concept_json = self._to_pretty_json(concept_package)
        expanded_sr_json = self._to_pretty_json(expanded_sr)
        return textwrap.dedent(f"""
            Propose Serbian literal candidates for a Serbian WordNet synset.

            Rules:
            - Prefer real lexical items over descriptive paraphrases.
            - Mark descriptive phrases explicitly when no lexicalized form is available.
            - Judge each candidate for precision and naturalness.
            - Note whether it is a good equivalent, too broad, too narrow, or descriptive.

            Return JSON:
            {{
              "candidates": [
                {{
                  "literal": "candidate",
                  "candidate_type": "primary|secondary|variant|descriptive",
                  "precision_score": 0.0,
                  "naturalness_score": 0.0,
                  "rationale": "why this candidate fits",
                  "fit_assessment": "good equivalent|too broad|too narrow|descriptive phrase",
                  "register_note": "brief note on register or usage"
                }}
              ]
            }}

            Concept package:
            {concept_json}

            Expanded Serbian output:
            {expanded_sr_json}
            """).strip()

    def _render_literal_selection_prompt(
        self,
        concept_package: Dict[str, Any],
        expanded_sr: Dict[str, Any],
        literal_candidates: Dict[str, Any],
    ) -> str:
        """Render the prompt for final literal selection."""

        concept_json = self._to_pretty_json(concept_package)
        expanded_sr_json = self._to_pretty_json(expanded_sr)
        candidates_json = self._to_pretty_json(literal_candidates)
        return textwrap.dedent(f"""
            Select the final Serbian literals for this WordNet synset.

            Rules:
            - Keep only literals that match the target synset precisely.
            - Reject items that are too broad, too narrow, stylistically odd, or merely descriptive unless necessary.
            - Prefer a compact but semantically correct literal set.

            Return JSON:
            {{
              "selected_literals_sr": ["literal1", "literal2"],
              "rejected_literals_sr": ["candidate_to_reject"],
              "rationale_sr": "brief Serbian rationale"
            }}

            Concept package:
            {concept_json}

            Expanded Serbian output:
            {expanded_sr_json}

            Candidate literals:
            {candidates_json}
            """).strip()

    def _render_final_gloss_prompt(
        self,
        concept_package: Dict[str, Any],
        expanded_sr: Dict[str, Any],
        selection: Dict[str, Any],
    ) -> str:
        """Render the prompt for the final short Serbian gloss."""

        concept_json = self._to_pretty_json(concept_package)
        expanded_sr_json = self._to_pretty_json(expanded_sr)
        selection_json = self._to_pretty_json(selection)
        return textwrap.dedent(f"""
            Write a final short Serbian WordNet gloss.

            Rules:
            - The gloss must be short, precise, lexicographic, and non-circular.
            - Keep it faithful to the expanded Serbian definition.
            - Keep it compatible with the selected Serbian literals.
            - Prefer genus + differentia wording when natural.

            Return JSON:
            {{
              "final_gloss_sr": "short Serbian gloss",
              "style_notes_sr": ["brief note", "brief note"]
            }}

            Concept package:
            {concept_json}

            Expanded Serbian output:
            {expanded_sr_json}

            Selected literals:
            {selection_json}
            """).strip()

    def _render_validation_prompt(
        self,
        concept_package: Dict[str, Any],
        expanded_sr: Dict[str, Any],
        selection: Dict[str, Any],
        final_gloss: Dict[str, Any],
    ) -> str:
        """Render the prompt for the final validation stage."""

        concept_json = self._to_pretty_json(concept_package)
        expanded_sr_json = self._to_pretty_json(expanded_sr)
        selection_json = self._to_pretty_json(selection)
        final_gloss_json = self._to_pretty_json(final_gloss)
        return textwrap.dedent(f"""
            Validate a drafted Serbian WordNet synset.

            Check:
            - circularity between selected literals and final gloss
            - semantic precision
            - compatibility of literals with the gloss
            - compatibility with the concept package
            - suitability for WordNet-style entry

            Return JSON:
            {{
              "validation_passed": true,
              "issues": [
                {{
                  "code": "optional_code",
                  "message": "brief explanation",
                  "severity": "info|warning|error"
                }}
              ],
              "final_synset_ready": true
            }}

            Concept package:
            {concept_json}

            Expanded Serbian output:
            {expanded_sr_json}

            Selected literals:
            {selection_json}

            Final gloss:
            {final_gloss_json}
            """).strip()

    def _assemble_result(
        self, state: ConceptualTranslationGraphState
    ) -> ConceptualTranslationGraphState:
        """Combine all concept-oriented stage outputs into the final result."""

        synset = state["synset"]
        concept_package = state.get("concept_package", {}) or {}
        expanded_en_call = state.get("expanded_en_call", {}) or {}
        expanded_sr_call = state.get("expanded_sr_call", {}) or {}
        literal_candidates_call = state.get("literal_candidates_call", {}) or {}
        literal_selection_call = state.get("literal_selection_call", {}) or {}
        final_gloss_call = state.get("final_gloss_call", {}) or {}
        validation_call = state.get("validation_call", {}) or {}

        expanded_en_payload = expanded_en_call.get("payload", {}) or {}
        expanded_sr_payload = expanded_sr_call.get("payload", {}) or {}
        literal_candidates_payload = literal_candidates_call.get("payload", {}) or {}
        literal_selection_payload = literal_selection_call.get("payload", {}) or {}
        final_gloss_payload = final_gloss_call.get("payload", {}) or {}
        validation_payload = validation_call.get("payload", {}) or {}

        selected_literals_sr = self._dedupe_list(
            literal_selection_payload.get("selected_literals_sr", [])
        )
        rejected_literals_sr = self._dedupe_list(
            literal_selection_payload.get("rejected_literals_sr", [])
        )
        translation = selected_literals_sr[0] if selected_literals_sr else ""
        final_gloss_sr = str(final_gloss_payload.get("final_gloss_sr", "")).strip()

        validation_passed = bool(validation_payload.get("validation_passed"))
        issues = validation_payload.get("issues", []) or []
        issue_count = len(issues) if isinstance(issues, list) else 0

        summary_lines = [
            f"Representative literal ({self.target_lang}): {translation or '—'}",
            f"Final Serbian gloss: {final_gloss_sr or '—'}",
            f"Validation passed: {'yes' if validation_passed else 'no'}",
            f"Selected literals: {', '.join(selected_literals_sr) if selected_literals_sr else '—'}",
            f"Rejected literals: {', '.join(rejected_literals_sr) if rejected_literals_sr else '—'}",
            f"Validation issues: {issue_count}",
            "",
            "Concept pipeline stages completed:",
            "  0. Concept extraction",
            "  1. Expanded English definition",
            "  2. Expanded Serbian definition",
            f"  3. Literal candidates: {len(literal_candidates_payload.get('candidates', []))}",
            f"  4. Selected literals: {len(selected_literals_sr)}",
            "  5. Final short gloss",
            "  6. Synset validation",
        ]
        curator_summary = "\n".join(summary_lines)

        payload = {
            "concept_package": concept_package,
            "expanded_en": expanded_en_payload,
            "expanded_sr": expanded_sr_payload,
            "candidates": literal_candidates_payload,
            "selection": literal_selection_payload,
            "final_gloss": final_gloss_payload,
            "validation": validation_payload,
            "calls": {
                "expanded_en": expanded_en_call,
                "expanded_sr": expanded_sr_call,
                "literal_candidates": literal_candidates_call,
                "literal_selection": literal_selection_call,
                "final_gloss": final_gloss_call,
                "validation": validation_call,
            },
            "logs": {
                "expanded_en": self._summarise_call(expanded_en_call),
                "expanded_sr": self._summarise_call(expanded_sr_call),
                "literal_candidates": self._summarise_call(literal_candidates_call),
                "literal_selection": self._summarise_call(literal_selection_call),
                "final_gloss": self._summarise_call(final_gloss_call),
                "validation": self._summarise_call(validation_call),
            },
        }

        raw_response = (
            validation_call.get("raw_response")
            or final_gloss_call.get("raw_response")
            or literal_selection_call.get("raw_response")
            or literal_candidates_call.get("raw_response")
            or expanded_sr_call.get("raw_response")
            or expanded_en_call.get("raw_response", "")
        )

        result = ConceptualTranslationResult(
            translation=translation,
            selected_literals_sr=selected_literals_sr,
            rejected_literals_sr=rejected_literals_sr,
            final_gloss_sr=final_gloss_sr,
            target_lang=self.target_lang,
            source_lang=self.source_lang,
            source=dict(synset),
            concept_package=concept_package,
            expanded_en=expanded_en_payload,
            expanded_sr=expanded_sr_payload,
            candidates=literal_candidates_payload,
            selection=literal_selection_payload,
            final_gloss=final_gloss_payload,
            validation=validation_payload,
            payload=payload,
            raw_response=raw_response,
            curator_summary=curator_summary,
        )
        return {"result": result}

    @staticmethod
    def _to_pretty_json(payload: Dict[str, Any]) -> str:
        """Serialize a dictionary for prompt embedding."""

        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def _dedupe_list(values: Any) -> List[str]:
        """Return unique non-empty string values while preserving order."""

        items = values if isinstance(values, (list, tuple)) else [values]
        deduped: List[str] = []
        seen = set()
        for item in items:
            text = str(item).strip()
            if text and text not in seen:
                seen.add(text)
                deduped.append(text)
        return deduped

    @staticmethod
    def _build_blocklist(source_literals: List[str]) -> List[str]:
        """Build a simple anti-circularity blocklist from source literals."""

        candidates: List[str] = []
        for literal in source_literals:
            normalized = literal.strip()
            if not normalized:
                continue
            candidates.extend(
                [
                    normalized,
                    normalized.lower(),
                    normalized.replace("_", " "),
                    normalized.replace("-", " "),
                ]
            )
        return ConceptualLangGraphTranslationPipeline._dedupe_list(candidates)

    @staticmethod
    def _coerce_to_str_list(value: Any) -> List[str]:
        """Coerce scalar or list-like metadata values into a clean string list."""

        if not value:
            return []
        items = value if isinstance(value, (list, tuple, set)) else [value]
        return [str(item).strip() for item in items if str(item).strip()]

    @staticmethod
    def _normalise_related_synsets(value: Any) -> List[Dict[str, Any]]:
        """Normalise relation payloads into the shared related-synset schema."""

        if not value:
            return []
        items = value if isinstance(value, (list, tuple)) else [value]
        normalised: List[Dict[str, Any]] = []
        for item in items:
            if isinstance(item, dict):
                literals = item.get("literals") or item.get("lemmas") or []
                if not isinstance(literals, (list, tuple)):
                    literals = [literals]
                normalised.append(
                    RelatedSynsetSchema(
                        synset_id=str(
                            item.get("synset_id")
                            or item.get("id")
                            or item.get("name")
                            or ""
                        ).strip(),
                        literals=[
                            str(literal).strip()
                            for literal in literals
                            if str(literal).strip()
                        ],
                        gloss=str(
                            item.get("gloss") or item.get("definition") or ""
                        ).strip(),
                    ).model_dump()
                )
                continue

            text = str(item).strip()
            if text:
                normalised.append(RelatedSynsetSchema(synset_id=text).model_dump())
        return normalised
