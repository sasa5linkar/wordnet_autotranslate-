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
import re
import textwrap
from typing import Any, Dict, Generator, Iterable, List, Sequence, TypedDict

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
    precision_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How precisely the candidate matches the target synset meaning.",
    )
    naturalness_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How natural the candidate sounds as a Serbian lexical item.",
    )
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
    auto_status: str = "review"
    quality_flags: List[str] = Field(default_factory=list)
    needs_human_review: bool = False
    needs_domain_check: bool = False


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
            "validation_passed": bool(self.validation.get("validation_passed")),
            "final_synset_ready": bool(self.validation.get("final_synset_ready")),
            "auto_status": self.validation.get("auto_status", "review"),
            "validation_issues": self.validation.get("issues", []),
            "quality_flags": self.validation.get("quality_flags", []),
            "needs_human_review": bool(self.validation.get("needs_human_review")),
            "needs_domain_check": bool(self.validation.get("needs_domain_check")),
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
    """Dissertation concept-oriented workflow using a concept-package graph."""

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

    @staticmethod
    def _taxonomy_guidelines_block(concept_package: Dict[str, Any]) -> str:
        """Return conservative taxonomy guidance when the concept is biological/taxonomic."""
        domains = [str(item).lower() for item in concept_package.get("domains", [])]
        literals = [str(item) for item in concept_package.get("source_literals", [])]
        looks_taxonomic = any(domain == "noun.animal" for domain in domains) or any(
            literal[:1].isupper() and any(ch.islower() for ch in literal)
            for literal in literals
        )
        if not looks_taxonomic:
            return ""
        return textwrap.dedent(
            """

            Taxonomy safety rules:
            - This appears to be a biological or taxonomic entry.
            - Do not invent Serbian common names or assert that an uncertain term is established.
            - First try to find an established Serbian lexicalized equivalent from the provided data and relations.
            - If a plausible established Serbian term is selected, keep both forms: Serbian term first and Latin taxon second.
            - If no reliable Serbian lexicalized equivalent is evident from the provided data, retain the Latin taxon as the safer literal.
            - Mark uncertain taxonomy entries with needs_domain_check=true and final_synset_ready=false.
            """
        ).strip()

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
            - Use hypernyms as genus constraints when available.
            - Use hyponyms to understand the lower boundary of the concept, not as direct synonyms.
            - Use meronyms and holonyms to capture part-whole structure when relevant.
            - Use sister synsets to avoid drifting into neighboring senses.
            - For every related synset, use its gloss/definition more than its lemma alone; relation lemmas can be ambiguous.
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
        target_rules = self._target_language_guidelines_block()
        pos_rules = self._source_pos_constraint_block(concept_package)
        taxonomy_rules = self._taxonomy_guidelines_block(concept_package)
        return textwrap.dedent(f"""
            Translate and adapt the expanded English semantic definition into Serbian.

            Rules:
            - Preserve the exact meaning.
            - Do not add new facts.
            - Use natural Serbian lexicographic language.
            - Keep the definition semantically explicit because it will drive literal extraction.
            - Avoid circularity where possible.
            {target_rules}
            {pos_rules}
            {taxonomy_rules}

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
        target_rules = self._target_language_guidelines_block()
        pos_rules = self._source_pos_constraint_block(concept_package)
        taxonomy_rules = self._taxonomy_guidelines_block(concept_package)
        return textwrap.dedent(f"""
            Propose Serbian literal candidates for a Serbian WordNet synset.

            Rules:
            - Prefer real lexical items over descriptive paraphrases.
            - Mark descriptive phrases explicitly when no lexicalized form is available.
            - Propose at most 5 candidates.
            - Judge each candidate for precision and naturalness.
            - Note whether it is a good equivalent, too broad, too narrow, or descriptive.
            - Prefer recall for human curation: include plausible broader candidates, but label them as broad.
            - Too narrow is worse than slightly broad because narrow literals can distort the synset.
            {target_rules}
            {pos_rules}
            {taxonomy_rules}

            Return JSON:
            {{
              "candidates": [
                {{
                  "literal": "candidate",
                  "candidate_type": "primary|secondary|variant|descriptive",
                  "precision_score": 0.85,
                  "naturalness_score": 0.92,
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
        target_rules = self._target_language_guidelines_block()
        pos_rules = self._source_pos_constraint_block(concept_package)
        taxonomy_rules = self._taxonomy_guidelines_block(concept_package)
        return textwrap.dedent(f"""
            Select the final Serbian literals for this WordNet synset.

            Rules:
            - Keep only literals that match the target synset precisely.
            - Prefer recall for human curation: keep plausible broader candidates as secondary literals when they still cover the synset.
            - Reject clearly too-narrow items because they change the synset meaning.
            - Reject stylistically odd or merely descriptive items unless necessary.
            - Prefer a compact but semantically useful literal set: normally 1-5 literals, ranked best first.
            - For adverb/particle synsets, keep stable literals and reject construction-bound variants.
            {target_rules}
            {pos_rules}
            {taxonomy_rules}

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
        target_rules = self._target_language_guidelines_block()
        pos_rules = self._source_pos_constraint_block(concept_package)
        return textwrap.dedent(f"""
            Write a final short Serbian WordNet gloss.

            Rules:
            - The gloss must be short, precise, lexicographic, and non-circular.
            - Do not use any selected Serbian literal, inflected form, or close derivation in the gloss.
            - Keep it faithful to the expanded Serbian definition.
            - Keep it compatible with the selected Serbian literals.
            - Prefer genus + differentia wording when natural.
            {target_rules}
            {pos_rules}

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
        target_rules = self._target_language_guidelines_block()
        pos_rules = self._source_pos_constraint_block(concept_package)
        taxonomy_rules = self._taxonomy_guidelines_block(concept_package)
        return textwrap.dedent(f"""
            Validate a drafted Serbian WordNet synset.

            Default stance: mark final_synset_ready=false unless every check clearly passes.

            Check:
            - circularity between selected literals and final gloss
            - semantic precision
            - compatibility of literals with the gloss
            - compatibility with the concept package
            - suitability for WordNet-style entry
            - same lexical entry type as the source WordNet POS
            - do not perform a full Serbian grammar audit; only flag obvious broken text
            - do not infer Serbian POS from suffixes alone; use lexical category and dictionary-like usage
            {target_rules}
            {pos_rules}
            {taxonomy_rules}

            Return JSON:
            {{
                            "validation_passed": false,
              "issues": [
                {{
                  "code": "optional_code",
                  "message": "brief explanation",
                  "severity": "info|warning|error"
                }}
              ],
                            "final_synset_ready": false,
                            "auto_status": "blocked|review|ready",
                            "quality_flags": ["optional_machine_flag"],
                            "needs_human_review": true,
                            "needs_domain_check": false
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
        final_gloss_sr = str(final_gloss_payload.get("final_gloss_sr", "")).strip()

        if self.target_lang.lower() in {"sr", "srp", "serbian"}:
            selected_literals_sr = LanguageUtils.normalize_serbian_latin_items(
                selected_literals_sr
            )
            rejected_literals_sr = LanguageUtils.normalize_serbian_latin_items(
                rejected_literals_sr
            )
            final_gloss_sr = LanguageUtils.normalize_serbian_latin_text(final_gloss_sr)

        selected_literals_sr, rejected_literals_sr = self._filter_selected_literals_by_pos(
            selected_literals_sr,
            rejected_literals_sr,
            concept_package,
        )
        fallback_literal_used = False
        if not selected_literals_sr and self._looks_taxonomic_entry(concept_package):
            selected_literals_sr = self._latin_taxon_literals_from_payload(concept_package)[:1]
            fallback_literal_used = bool(selected_literals_sr)
        selected_literals_sr = self._ensure_taxonomy_dual_literals(
            selected_literals_sr,
            concept_package,
        )
        if not selected_literals_sr:
            selected_literals_sr = self._select_minimum_conceptual_literals(
                rejected_literals_sr,
                literal_candidates_payload,
                concept_package,
            )
            fallback_literal_used = bool(selected_literals_sr)
        if selected_literals_sr:
            selected_keys = {literal.casefold().strip() for literal in selected_literals_sr}
            rejected_literals_sr = [
                literal
                for literal in rejected_literals_sr
                if literal.casefold().strip() not in selected_keys
            ]
        final_gloss_sr = self._fallback_non_circular_gloss(
            final_gloss_sr,
            selected_literals_sr,
            expanded_sr_payload,
        )

        validation_payload = self._apply_deterministic_validation_gates(
            validation_payload,
            concept_package,
            selected_literals_sr,
            final_gloss_sr,
            fallback_literal_used=fallback_literal_used,
        )
        literal_selection_payload = dict(literal_selection_payload)
        literal_selection_payload["selected_literals_sr"] = selected_literals_sr
        literal_selection_payload["rejected_literals_sr"] = rejected_literals_sr
        final_gloss_payload = dict(final_gloss_payload)
        final_gloss_payload["final_gloss_sr"] = final_gloss_sr

        translation = selected_literals_sr[0] if selected_literals_sr else ""

        validation_passed = bool(validation_payload.get("validation_passed"))
        issues = validation_payload.get("issues", []) or []
        issue_count = len(issues) if isinstance(issues, list) else 0

        summary_lines = [
            f"Representative literal ({self.target_lang}): {translation or '—'}",
            f"Final Serbian gloss: {final_gloss_sr or '—'}",
            f"Validation passed: {'yes' if validation_passed else 'no'}",
            f"Auto status: {validation_payload.get('auto_status', 'review')}",
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
            "  7. Result assembly",
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

    def _filter_selected_literals_by_pos(
        self,
        selected: List[str],
        rejected: List[str],
        concept_package: Dict[str, Any],
    ) -> tuple[List[str], List[str]]:
        """Move only explicit construction-bound adverb variants into rejected list.

        Serbian POS tagging is not deterministic here; candidate POS compatibility
        is handled by prompts/model judgment using the source WordNet POS.
        """
        raw_pos = str(concept_package.get("pos") or "").strip()
        pos = LanguageUtils.normalize_pos_for_english(raw_pos) if raw_pos else ""
        if not pos:
            return selected, rejected

        kept: List[str] = []
        moved: List[str] = []
        has_single_adverb = pos == "r" and any(" " not in item.strip() for item in selected)
        has_core_even_particle = pos == "r" and any(
            item.strip().casefold() == "čak" for item in selected
        )
        for literal in selected:
            text = str(literal or "").strip()
            folded = text.casefold()
            move = False
            if pos == "r" and has_single_adverb:
                move = " " in folded or (
                    has_core_even_particle and folded in {"još", "ni", "i", "takođe", "baš"}
                )
            if move:
                moved.append(text)
            else:
                kept.append(text)

        if moved:
            rejected = self._dedupe_list(list(rejected) + moved)
        return kept, rejected

    def _fallback_non_circular_gloss(
        self,
        final_gloss: str,
        selected_literals: List[str],
        expanded_sr_payload: Dict[str, Any],
    ) -> str:
        """Use an available non-circular Serbian definition when final gloss repeats a literal."""
        if not final_gloss or not selected_literals:
            return final_gloss
        if not self._gloss_contains_any_literal(final_gloss, selected_literals):
            return final_gloss

        candidates = [
            str(expanded_sr_payload.get("expanded_definition_sr") or "").strip(),
        ]
        for candidate in candidates:
            if candidate and not self._gloss_contains_any_literal(candidate, selected_literals):
                return candidate
        return final_gloss

    @staticmethod
    def _gloss_contains_any_literal(gloss: str, literals: List[str]) -> bool:
        """Return True when a gloss contains a selected literal exactly."""
        gloss_folded = str(gloss or "").casefold()
        for literal in literals:
            literal_folded = str(literal or "").casefold().strip()
            if literal_folded and re.search(rf"(?<!\w){re.escape(literal_folded)}(?!\w)", gloss_folded):
                return True
        return False

    def _select_minimum_conceptual_literals(
        self,
        rejected_literals: List[str],
        literal_candidates_payload: Dict[str, Any],
        concept_package: Dict[str, Any],
    ) -> List[str]:
        """Select a single fallback literal when conceptual strict selection is empty."""
        candidates: List[tuple[float, str]] = []

        for item in literal_candidates_payload.get("candidates", []) or []:
            if not isinstance(item, dict):
                continue
            literal = str(item.get("literal") or "").strip()
            if not literal:
                continue
            precision = float(item.get("precision_score") or 0.0)
            naturalness = float(item.get("naturalness_score") or 0.0)
            candidate_type = str(item.get("candidate_type") or "").casefold()
            fit = str(item.get("fit_assessment") or "").casefold()
            score = precision + naturalness
            if "descriptive" in candidate_type or "descriptive" in fit:
                score -= 0.15
            if "too broad" in fit:
                score -= 0.05
            if "too narrow" in fit:
                score -= 0.30
            if self._is_descriptive_literal(literal):
                score -= 0.15
            candidates.append((score, literal))

        if not candidates:
            for literal in rejected_literals:
                if str(literal).strip():
                    candidates.append((0.0, str(literal).strip()))

        candidates.extend(
            (0.0, literal) for literal in self._latin_taxon_literals_from_payload(concept_package)
        )
        source_literals = concept_package.get("source_literals") or []
        if not isinstance(source_literals, (list, tuple, set)):
            source_literals = [source_literals]
        candidates.extend((0.0, str(literal).strip()) for literal in source_literals if str(literal).strip())

        deduped: List[str] = []
        seen: set[str] = set()
        for _score, literal in sorted(candidates, key=lambda item: item[0], reverse=True):
            key = literal.casefold().strip()
            if key and key not in seen:
                seen.add(key)
                deduped.append(literal.strip())
                break
        if self.target_lang.lower() in {"sr", "srp", "serbian"}:
            deduped = LanguageUtils.normalize_serbian_latin_items(deduped)
        return deduped

    def _apply_deterministic_validation_gates(
        self,
        validation_payload: Dict[str, Any],
        concept_package: Dict[str, Any],
        selected_literals: List[str],
        final_gloss: str,
        *,
        fallback_literal_used: bool = False,
    ) -> Dict[str, Any]:
        """Apply non-LLM safety gates before exposing conceptual readiness."""
        payload = dict(validation_payload or {})
        quality_flags = list(payload.get("quality_flags") or [])
        issues: List[Any] = []
        model_error_downgraded = False
        for issue in list(payload.get("issues") or []):
            if isinstance(issue, dict):
                normalised_issue = dict(issue)
                if str(normalised_issue.get("severity", "")).lower() == "error":
                    normalised_issue["original_severity"] = "error"
                    normalised_issue["severity"] = "warning"
                    normalised_issue.setdefault("source", "model_validation")
                    model_error_downgraded = True
                issues.append(normalised_issue)
            else:
                issues.append(issue)
        if model_error_downgraded and "model_validation_error_unconfirmed" not in quality_flags:
            quality_flags.append("model_validation_error_unconfirmed")

        def add_issue(code: str, message: str, severity: str = "warning") -> None:
            if code not in quality_flags:
                quality_flags.append(code)
            existing_issue = next(
                (issue for issue in issues if isinstance(issue, dict) and issue.get("code") == code),
                None,
            )
            if existing_issue is None:
                issues.append(
                    {
                        "code": code,
                        "message": message,
                        "severity": severity,
                        "source": "deterministic_gate",
                    }
                )
                return
            severity_rank = {"info": 0, "warning": 1, "error": 2}
            old_rank = severity_rank.get(str(existing_issue.get("severity", "")).lower(), 0)
            new_rank = severity_rank.get(str(severity).lower(), 1)
            if new_rank > old_rank:
                existing_issue["message"] = message
                existing_issue["severity"] = severity
                existing_issue["source"] = "deterministic_gate"

        gloss_folded = final_gloss.casefold()
        for literal in selected_literals:
            literal_folded = literal.casefold().strip()
            if literal_folded and re.search(rf"\b{re.escape(literal_folded)}\b", gloss_folded):
                add_issue(
                    "literal_in_gloss",
                    f"Selected literal '{literal}' appears in the final gloss.",
                    "error",
                )

        domains = [str(item).lower() for item in concept_package.get("domains", [])]
        source_literals = [str(item) for item in concept_package.get("source_literals", [])]
        source_gloss = str(concept_package.get("source_gloss") or "")
        looks_taxonomic = any(domain == "noun.animal" for domain in domains) or any(
            literal[:1].isupper() and any(ch.islower() for ch in literal)
            for literal in source_literals
        )
        if looks_taxonomic and len(source_gloss.split()) <= 3:
            payload["needs_domain_check"] = True
            add_issue(
                "taxonomy_domain_check",
                "Biological/taxonomic entry with short source gloss requires domain verification.",
                "warning",
            )

        broad_literals = {"stvar", "objekat", "predmet", "postojanje", "biće"}
        for literal in selected_literals:
            if literal.casefold().strip() in broad_literals:
                add_issue(
                    "broad_literal_risk",
                    f"Selected literal '{literal}' is broad and may be a hypernym rather than a synset equivalent.",
                    "warning",
                )

        if not selected_literals:
            add_issue("missing_literals", "No final Serbian literal was selected.", "error")

        auto_report = self._build_auto_quality_report(
            concept_package,
            selected_literals,
            final_gloss,
            raw_literals=selected_literals,
            lexname=None,
            topic_domains=None,
            model_ready=bool(payload.get("final_synset_ready")),
            fallback_literal_used=fallback_literal_used,
        )
        for issue in auto_report["quality_issues"]:
            add_issue(
                str(issue.get("code") or "quality_issue"),
                str(issue.get("message") or "Deterministic quality issue."),
                str(issue.get("severity") or "warning"),
            )
        if auto_report.get("needs_domain_check"):
            payload["needs_domain_check"] = True

        has_error = any(
            isinstance(issue, dict) and str(issue.get("severity", "")).lower() == "error"
            for issue in issues
        )
        if issues:
            payload["needs_human_review"] = True
        if has_error or payload.get("needs_domain_check"):
            payload["validation_passed"] = False
            payload["final_synset_ready"] = False

        payload["issues"] = issues
        payload["quality_flags"] = quality_flags
        payload.setdefault("needs_human_review", bool(issues))
        payload.setdefault("needs_domain_check", False)
        payload["auto_status"] = self._auto_status_from_issues(
            issues,
            needs_domain_check=bool(payload.get("needs_domain_check")),
            model_ready=bool(payload.get("final_synset_ready")),
        )
        return payload

    @staticmethod
    def _lookup_related_synset_details(synset_id: str) -> tuple[List[str], str]:
        """Return English WordNet literals and gloss for a related synset id when possible."""
        identifier = str(synset_id or "").strip()
        if not identifier:
            return [], ""

        try:
            from nltk.corpus import wordnet as wn
        except Exception:
            return [], ""

        synset = None
        eng30_match = re.match(
            r"^ENG30-(?P<offset>\d{8})-(?P<pos>[a-z])$",
            identifier,
            flags=re.IGNORECASE,
        )
        try:
            if eng30_match:
                synset = wn.synset_from_pos_and_offset(
                    eng30_match.group("pos").lower(),
                    int(eng30_match.group("offset")),
                )
            elif re.match(r"^[\w-]+\.[nvars]\.[0-9]{2}$", identifier):
                synset = wn.synset(identifier)
        except Exception:
            synset = None

        if synset is None:
            return [], ""

        try:
            literals = [lemma.name().replace("_", " ") for lemma in synset.lemmas()]
        except Exception:
            literals = []
        try:
            gloss = str(synset.definition() or "").strip()
        except Exception:
            gloss = ""
        return literals, gloss

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
                synset_id = str(
                    item.get("synset_id")
                    or item.get("id")
                    or item.get("name")
                    or ""
                ).strip()
                gloss = str(
                    item.get("gloss") or item.get("definition") or ""
                ).strip()
                lookup_literals, lookup_gloss = (
                    ConceptualLangGraphTranslationPipeline._lookup_related_synset_details(
                        synset_id
                    )
                )
                if not any(str(literal).strip() for literal in literals) and lookup_literals:
                    literals = lookup_literals
                if not gloss and lookup_gloss:
                    gloss = lookup_gloss
                if not any(str(literal).strip() for literal in literals) and synset_id:
                    literals = [
                        synset_id.split(".")[0].replace("_", " ").replace("-", " ")
                    ]
                normalised.append(
                    RelatedSynsetSchema(
                        synset_id=synset_id,
                        literals=[
                            str(literal).strip()
                            for literal in literals
                            if str(literal).strip()
                        ],
                        gloss=gloss,
                    ).model_dump()
                )
                continue

            text = str(item).strip()
            if text:
                literals, gloss = ConceptualLangGraphTranslationPipeline._lookup_related_synset_details(
                    text
                )
                normalised.append(
                    RelatedSynsetSchema(
                        synset_id=text,
                        literals=literals,
                        gloss=gloss,
                    ).model_dump()
                )
        return normalised
