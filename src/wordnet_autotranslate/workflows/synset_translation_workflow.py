"""Agent-friendly workflow for translating English WordNet synsets into Serbian.

Supports lookup by:
- ENG30 synset ID (e.g. ENG30-00001740-n)
- Synset name (e.g. entity.n.01)
- Lemma + POS + sense index (e.g. lemma=entity, pos=n, sense=1)

And execution via one or multiple pipelines.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..pipelines.translation_pipeline import TranslationPipeline
from ..pipelines.conceptual_langgraph_pipeline import ConceptualLangGraphTranslationPipeline
from ..pipelines.langgraph_translation_pipeline import LangGraphTranslationPipeline
from ..utils.language_utils import LanguageUtils


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

    try:
        offset = int(parts[1])
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


def resolve_wordnet_synset(
    *,
    english_id: Optional[str] = None,
    synset_name: Optional[str] = None,
    lemma: Optional[str] = None,
    pos: Optional[str] = None,
    sense_index: int = 1,
) -> Dict[str, Any]:
    """Resolve a synset from one of the supported selectors and return payload."""
    from nltk.corpus import wordnet as wn

    if english_id:
        offset, mapped_pos = parse_eng30_id(english_id)
        synset = wn.synset_from_pos_and_offset(mapped_pos, offset)
        return synset_to_payload(synset)

    if synset_name:
        synset = wn.synset(synset_name)
        return synset_to_payload(synset)

    if lemma and pos:
        mapped_pos = LanguageUtils.normalize_pos_for_english(pos)
        candidates = wn.synsets(lemma, pos=mapped_pos)
        if not candidates:
            raise LookupError(f"No synsets found for lemma={lemma!r}, pos={pos!r}")
        idx = _resolve_sense_index(sense_index, len(candidates))
        return synset_to_payload(candidates[idx])

    raise ValueError(
        "Provide one selector: english_id OR synset_name OR lemma+pos."
    )


def run_translation_workflow(
    synset_payload: Dict[str, Any],
    *,
    pipeline: str = "langgraph",
    config: WorkflowConfig = WorkflowConfig(),
) -> Dict[str, Any]:
    """Run requested pipeline(s) for a synset payload."""
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

    if selected in {"dspy", "all"}:
        dspy_pipeline = TranslationPipeline(
            source_lang=config.source_lang,
            target_lang=config.target_lang,
        )
        dspy_output = dspy_pipeline.translate([synset_payload])
        if dspy_output:
            results["pipelines"]["dspy"] = dspy_output[0]
        else:
            results["pipelines"]["dspy"] = {
                "status": "not_implemented",
                "message": "TranslationPipeline.translate currently returns no outputs for synsets.",
            }

    if not results["pipelines"]:
        raise ValueError("Unsupported pipeline. Use: langgraph | conceptual | all | dspy")

    return results


def results_to_json(data: Dict[str, Any]) -> str:
    """Serialize workflow output for CLI/tools."""
    return json.dumps(data, ensure_ascii=False, indent=2)
