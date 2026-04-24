"""Agent-friendly workflow for translating English WordNet synsets into Serbian.

Supports lookup by:
- ENG30 synset ID (e.g. ENG30-00001740-n)
- Synset name (e.g. entity.n.01)
- Lemma + POS + sense index (e.g. lemma=entity, pos=n, sense=1)

And execution via one or multiple pipelines.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from ..models.synset_handler import SynsetHandler
from ..pipelines.translation_pipeline import BaselineTranslationPipeline
from ..pipelines.conceptual_langgraph_pipeline import ConceptualLangGraphTranslationPipeline
from ..pipelines.langgraph_translation_pipeline import LangGraphTranslationPipeline
from ..utils.language_utils import LanguageUtils

_ILI_ID_RE = re.compile(r"^i\d+$", re.IGNORECASE)
_EWN_SYNSET_ID_RE = re.compile(r"^ewn-(?P<offset>\d{8})-(?P<pos>[a-z])$", re.IGNORECASE)
_EWN_PROJECT = "ewn:2020"


@dataclass(frozen=True)
class WorkflowConfig:
    source_lang: str = "en"
    target_lang: str = "sr"
    model: str = "gpt-oss:120b"
    timeout: int = 600
    base_url: str = "http://localhost:11434"
    temperature: float = 0.2
    strict: bool = False


def parse_eng30_id(english_id: str) -> Tuple[int, str]:
    """Parse ENG30 IDs into (offset, pos)."""
    parts = str(english_id).strip().split("-")
    if len(parts) != 3 or parts[0] != "ENG30":
        raise ValueError(
            f"parse_eng30_id: invalid selector {english_id!r}; expected 'ENG30-########-[n|v|a|s|r]'."
        )

    offset_token = parts[1]
    if len(offset_token) != 8 or not offset_token.isascii() or not offset_token.isdigit():
        raise ValueError(
            f"parse_eng30_id: invalid offset in selector {english_id!r}; offset must be exactly 8 digits."
        )

    try:
        offset = int(offset_token)
    except ValueError as exc:
        raise ValueError(
            f"parse_eng30_id: invalid offset in selector {english_id!r}; offset must be an integer."
        ) from exc

    raw_pos = parts[2].lower()
    if raw_pos not in {"n", "v", "a", "s", "r", "b"}:
        raise ValueError(
            f"parse_eng30_id: invalid POS in selector {english_id!r}; expected one of n,v,a,s,r."
        )
    pos = LanguageUtils.normalize_pos_for_english(raw_pos)
    if pos not in {"n", "v", "a", "r"}:
        raise ValueError(
            f"parse_eng30_id: invalid POS mapping in selector {english_id!r}; normalized POS={pos!r} is unsupported."
        )

    return offset, pos


def parse_ili_id(ili_id: str) -> str:
    """Validate an interlingual index identifier."""
    normalized = str(ili_id or "").strip().lower()
    if not _ILI_ID_RE.match(normalized):
        raise ValueError(
            f"parse_ili_id: invalid selector {ili_id!r}; expected format like 'i35545'."
        )
    return normalized


def _resolve_sense_index(sense_index: int, candidate_count: int) -> int:
    """Resolve 1-based sense index to zero-based list index."""
    if sense_index <= 0:
        raise ValueError(
            f"sense-index resolution routine: invalid sense_index={sense_index}; expected positive integer."
        )
    idx = sense_index - 1
    if idx >= candidate_count:
        raise ValueError(
            "sense-index resolution routine: "
            f"sense_index={sense_index} out of range; available senses={candidate_count}."
        )
    return idx


def synset_to_payload(synset: Any) -> Dict[str, Any]:
    """Convert an NLTK WordNet synset object into pipeline payload format."""
    try:
        offset = synset.offset()
        pos = synset.pos()
        name = synset.name()
        definition = synset.definition()
        examples = synset.examples()
        lemmas = [lemma.name().replace("_", " ") for lemma in synset.lemmas()]
    except AttributeError as exc:
        raise ValueError("Provided object is not a valid WordNet synset") from exc

    return {
        "id": f"ENG30-{offset:08d}-{pos}",
        "english_id": f"ENG30-{offset:08d}-{pos}",
        "name": name,
        "lemmas": lemmas,
        "definition": definition,
        "examples": examples,
        "pos": pos,
    }


def _ewn_synset_to_payload(synset: Any, *, ili_id: str) -> Dict[str, Any]:
    """Convert a `wn` English WordNet synset into the shared payload format."""
    raw_synset_id = str(getattr(synset, "id", "") or "").strip()
    match = _EWN_SYNSET_ID_RE.match(raw_synset_id)
    if not match:
        raise ValueError(
            f"ILI resolver returned unexpected English WordNet synset id {raw_synset_id!r}."
        )

    offset = int(match.group("offset"))
    pos = LanguageUtils.normalize_pos_for_english(match.group("pos"))

    lemmas: List[str] = []
    try:
        for word in synset.words():
            forms = word.forms()
            if forms:
                lemma = str(forms[0]).replace("_", " ").strip()
                if lemma and lemma not in lemmas:
                    lemmas.append(lemma)
    except Exception:
        pass

    if not lemmas:
        lemmas = [str(lemma).replace("_", " ").strip() for lemma in getattr(synset, "lemmas", lambda: [])()]
        lemmas = [lemma for lemma in lemmas if lemma]

    examples = [str(example).strip() for example in synset.examples() if str(example).strip()]
    english_id = f"ENG30-{offset:08d}-{pos}"
    return {
        "id": english_id,
        "english_id": english_id,
        "ili_id": ili_id,
        "name": raw_synset_id or english_id,
        "lemmas": lemmas,
        "definition": str(synset.definition() or "").strip(),
        "examples": examples,
        "pos": pos,
        "resolution_source": "ewn_ili_fallback",
    }


@lru_cache(maxsize=1)
def _get_ewn_wordnet() -> Any:
    """Load the external English WordNet used for ILI resolution."""
    try:
        import wn as external_wn  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError(
            "ILI resolution requires the optional 'wn' package. Install project dependencies first."
        ) from exc

    if not any(getattr(lexicon, "id", "") == "ewn" for lexicon in external_wn.lexicons()):
        external_wn.download(_EWN_PROJECT, progress_handler=None)

    return external_wn.Wordnet("ewn")


def resolve_ili_to_payload(ili_id: str) -> Dict[str, Any]:
    """Resolve an ILI selector into the shared English synset payload."""
    normalized_ili = parse_ili_id(ili_id)
    english_wordnet = _get_ewn_wordnet()
    candidates = english_wordnet.synsets(ili=normalized_ili)
    if not candidates:
        raise LookupError(f"No English WordNet synset found for ILI={normalized_ili!r}")

    external_synset = candidates[0]
    payload = _ewn_synset_to_payload(external_synset, ili_id=normalized_ili)

    # Prefer the Princeton NLTK payload whenever the offset/POS can be resolved there too.
    try:
        offset, pos = parse_eng30_id(payload["english_id"])
        from nltk.corpus import wordnet as nltk_wn

        nltk_synset = nltk_wn.synset_from_pos_and_offset(pos, offset)
        nltk_payload = synset_to_payload(nltk_synset)
        nltk_payload["ili_id"] = normalized_ili
        nltk_payload["resolution_source"] = "nltk_via_ili"
        return nltk_payload
    except Exception:
        return payload


@lru_cache(maxsize=1)
def _get_synset_handler() -> SynsetHandler:
    """Return a cached English WordNet helper for relation enrichment."""
    return SynsetHandler(language="en")


def enrich_synset_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Attach relation and domain metadata useful for native-agent workflows."""
    english_id = str(payload.get("english_id") or payload.get("id") or "").strip()
    if not english_id.startswith("ENG30-"):
        return dict(payload)

    offset, pos = parse_eng30_id(english_id)
    from nltk.corpus import wordnet as wn

    synset = wn.synset_from_pos_and_offset(pos, offset)
    enriched = dict(payload)

    try:
        enriched["lexname"] = synset.lexname()
    except Exception:
        pass

    try:
        topic_domains = [domain.name() for domain in synset.topic_domains()]
    except Exception:
        topic_domains = []
    if topic_domains:
        enriched["topic_domains"] = topic_domains
        if not enriched.get("domain_tags"):
            enriched["domain_tags"] = topic_domains
        if not enriched.get("domains"):
            enriched["domains"] = topic_domains

    relation_data = _get_synset_handler().get_synset_by_offset(f"{offset:08d}", pos) or {}
    relations = relation_data.get("relations") or {}
    if relations:
        enriched["relations"] = relations
        enriched["hypernyms"] = relations.get("hypernyms", [])
        enriched["hyponyms"] = relations.get("hyponyms", [])
        enriched["meronyms"] = (
            relations.get("part_meronyms", [])
            + relations.get("member_meronyms", [])
            + relations.get("substance_meronyms", [])
        )
        enriched["holonyms"] = (
            relations.get("part_holonyms", [])
            + relations.get("member_holonyms", [])
            + relations.get("substance_holonyms", [])
        )
        enriched["similar_synsets"] = relations.get("similar_tos", []) + relations.get("also", [])

    return enriched


def resolve_wordnet_synset(
    *,
    ili: Optional[str] = None,
    english_id: Optional[str] = None,
    synset_name: Optional[str] = None,
    lemma: Optional[str] = None,
    pos: Optional[str] = None,
    sense_index: int = 1,
    include_relations: bool = False,
) -> Dict[str, Any]:
    """Resolve a synset from one of the supported selectors and return payload."""
    from nltk.corpus import wordnet as wn

    def _finalize(payload: Dict[str, Any]) -> Dict[str, Any]:
        if include_relations:
            return enrich_synset_payload(payload)
        return payload

    if ili:
        return _finalize(resolve_ili_to_payload(ili))

    if english_id:
        offset, mapped_pos = parse_eng30_id(english_id)
        synset = wn.synset_from_pos_and_offset(mapped_pos, offset)
        return _finalize(synset_to_payload(synset))

    if synset_name:
        synset = wn.synset(synset_name)
        return _finalize(synset_to_payload(synset))

    if lemma and pos:
        mapped_pos = LanguageUtils.normalize_pos_for_english(pos)
        candidates = wn.synsets(lemma, pos=mapped_pos)
        if not candidates:
            raise LookupError(f"No synsets found for lemma={lemma!r}, pos={pos!r}")
        idx = _resolve_sense_index(sense_index, len(candidates))
        return _finalize(synset_to_payload(candidates[idx]))

    raise ValueError(
        "Provide one selector: ili OR english_id OR synset_name OR lemma+pos."
    )


def run_translation_workflow(
    synset_payload: Dict[str, Any],
    *,
    pipeline: str = "langgraph",
    config: WorkflowConfig = WorkflowConfig(),
) -> Dict[str, Any]:
    """Run requested pipeline(s) for a synset payload.

    Supported workflows:
    - baseline: dissertation baseline workflow (gloss + literals only)
    - langgraph: dissertation multi-phase workflow
    - conceptual: dissertation concept-oriented workflow
    - dspy: legacy alias for baseline
    """
    selected = pipeline.lower().strip()

    results: Dict[str, Any] = {
        "selector_id": synset_payload.get("id") or synset_payload.get("english_id"),
        "source_synset": synset_payload,
        "pipelines": {},
    }

    def _run_with_capture(name: str, runner: Any) -> None:
        try:
            results["pipelines"][name] = runner()
        except Exception as exc:
            if config.strict:
                raise
            results["pipelines"][name] = {
                "status": "error",
                "message": str(exc),
            }

    if selected in {"baseline", "dspy", "all"}:
        # Legacy compatibility: "dspy" selector now maps to the dissertation baseline workflow.
        baseline = BaselineTranslationPipeline(
            source_lang=config.source_lang,
            target_lang=config.target_lang,
            model=config.model,
            base_url=config.base_url,
            temperature=config.temperature,
            timeout=config.timeout,
        )
        _run_with_capture("baseline", lambda: baseline.translate_synset(synset_payload))
        # Backwards compatibility: callers using "dspy" may read results["pipelines"]["dspy"].
        # Share the same result object to avoid a second LLM call.
        if selected == "dspy" and "baseline" in results["pipelines"]:
            results["pipelines"]["dspy"] = results["pipelines"]["baseline"]

    if selected in {"langgraph", "all"}:
        lg = LangGraphTranslationPipeline(
            source_lang=config.source_lang,
            target_lang=config.target_lang,
            model=config.model,
            timeout=config.timeout,
            base_url=config.base_url,
            temperature=config.temperature,
        )
        _run_with_capture("langgraph", lambda: lg.translate_synset(synset_payload))

    if selected in {"conceptual", "all"}:
        cg = ConceptualLangGraphTranslationPipeline(
            source_lang=config.source_lang,
            target_lang=config.target_lang,
            model=config.model,
            timeout=config.timeout,
            base_url=config.base_url,
            temperature=config.temperature,
        )
        _run_with_capture("conceptual", lambda: cg.translate_synset(synset_payload))

    if not results["pipelines"]:
        raise ValueError("Unsupported pipeline. Use: baseline | langgraph | conceptual | all | dspy")

    return results


def results_to_json(data: Dict[str, Any]) -> str:
    """Serialize workflow output for CLI/tools."""
    return json.dumps(data, ensure_ascii=False, indent=2)
