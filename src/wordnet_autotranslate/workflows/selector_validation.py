"""Shared selector validation helpers for CLI and workflow entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SelectorValidationResult:
    """Simple result object for selector-family validation."""

    selector_count: int
    has_english_id: bool
    has_synset_name: bool
    has_lemma_pos: bool


def validate_selector_families(
    *,
    english_id: Optional[str] = None,
    synset_name: Optional[str] = None,
    lemma: Optional[str] = None,
    pos: Optional[str] = None,
) -> SelectorValidationResult:
    """Validate that exactly one selector family is provided.

    Selector families:
    - english_id
    - synset_name
    - lemma+pos
    """

    has_english_id = bool(english_id)
    has_synset_name = bool(synset_name)
    has_lemma_pos = bool(lemma and pos)
    selector_count = sum([has_english_id, has_synset_name, has_lemma_pos])

    if selector_count != 1:
        raise ValueError(
            "Provide exactly one selector: english_id OR synset_name OR lemma+pos."
        )

    return SelectorValidationResult(
        selector_count=selector_count,
        has_english_id=has_english_id,
        has_synset_name=has_synset_name,
        has_lemma_pos=has_lemma_pos,
    )
