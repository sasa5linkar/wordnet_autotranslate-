"""Baseline synset-translation pipeline.

This module implements the dissertation's baseline workflow:
English gloss + English literals -> Serbian gloss + Serbian literals.

`TranslationPipeline` is kept as a compatibility alias for older imports.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..utils.language_utils import LanguageUtils


@lru_cache(maxsize=128)
def _load_text_file(file_path: str) -> Tuple[str, ...]:
    """Load and cache text file contents."""
    with open(file_path, "r", encoding="utf-8") as f:
        return tuple(
            line.strip() for line in f if line.strip() and not line.startswith("#")
        )


class BaselineTranslationPipeline:
    """Simple direct-translation baseline for WordNet synsets."""

    DEFAULT_SYSTEM_PROMPT: str = (
        "You are a bilingual lexicographer. Translate only the provided English "
        "WordNet gloss and literals into the target language. Return JSON only."
    )

    def __init__(
        self,
        source_lang: str = "en",
        target_lang: str = "sr",
        llm: Optional[Any] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.llm = llm
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.examples_path = Path(__file__).parent.parent.parent.parent / "examples"

    def load_english_synsets(self) -> List[Dict[str, Any]]:
        """Load English synsets (placeholder for future dataset adapters)."""
        return []

    def load_target_synsets(self) -> List[Dict[str, Any]]:
        """Load target-language synsets (placeholder for future adapters)."""
        return []

    def load_examples(self) -> Dict[str, List[str]]:
        """Load language examples with cached file reads."""
        examples = {"words": [], "sentences": []}

        target_path = self.examples_path / self.target_lang
        if target_path.exists():
            words_file = target_path / "words.txt"
            if words_file.exists():
                examples["words"] = list(_load_text_file(str(words_file)))

            sentences_file = target_path / "sentences.txt"
            if sentences_file.exists():
                examples["sentences"] = list(_load_text_file(str(sentences_file)))

        return examples

    def translate_synset(self, synset: Dict[str, Any]) -> Dict[str, Any]:
        """Translate one synset using only gloss and literals."""
        lemmas = self._coerce_to_str_list(synset.get("lemmas") or synset.get("literals"))
        definition = str(synset.get("definition") or synset.get("gloss") or "").strip()

        call_log = self._call_llm(lemmas=lemmas, definition=definition)
        payload = call_log.get("payload", {})

        definition_translation = str(payload.get("definition_translation") or "").strip()
        translated_synonyms = self._coerce_to_str_list(
            payload.get("translated_synonyms") or payload.get("selected_literals_sr")
        )

        if not translated_synonyms:
            translated_synonyms = [item for item in lemmas if item]
        translation = translated_synonyms[0] if translated_synonyms else ""

        if not definition_translation:
            definition_translation = definition

        summary = (
            f"Baseline workflow ({self.source_lang}->{self.target_lang}) produced "
            f"{len(translated_synonyms)} literal(s) from gloss+literals only. "
            f"Representative literal: '{translation or '(none)'}'."
        )

        return {
            "translation": translation,
            "definition_translation": definition_translation,
            "translated_synonyms": translated_synonyms,
            "target_lang": self.target_lang,
            "source_lang": self.source_lang,
            "source": {
                "id": synset.get("id") or synset.get("english_id"),
                "name": synset.get("name"),
                "pos": synset.get("pos") or synset.get("part_of_speech"),
                "lemmas": lemmas,
                "definition": definition,
            },
            "payload": {
                "baseline": payload,
                "call": {
                    "prompt": call_log.get("prompt", ""),
                    "raw_response": call_log.get("raw_response", ""),
                },
            },
            "source_selector": synset.get("id") or synset.get("english_id"),
            "curator_summary": summary,
        }

    def translate(self, synsets: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Translate a sequence of synsets."""
        return [self.translate_synset(synset) for synset in synsets]

    def translate_stream(self, synsets: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
        """Yield baseline translations one by one."""
        for synset in synsets:
            yield self.translate_synset(synset)

    def _call_llm(self, *, lemmas: List[str], definition: str) -> Dict[str, Any]:
        """Call the configured LLM if present; otherwise use deterministic fallback."""
        prompt = self._render_prompt(lemmas=lemmas, definition=definition)

        if self.llm is None:
            fallback_payload = {
                "definition_translation": definition,
                "translated_synonyms": lemmas,
                "notes": "No LLM configured; returned deterministic baseline fallback.",
            }
            return {
                "prompt": prompt,
                "raw_response": json.dumps(fallback_payload, ensure_ascii=False),
                "payload": fallback_payload,
            }

        response = self.llm.invoke(
            [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ]
        )
        content: Any = getattr(response, "content", response)
        raw_response = str(content).strip()
        payload = self._decode_llm_payload(raw_response)

        return {
            "prompt": prompt,
            "raw_response": raw_response,
            "payload": payload,
        }

    def _render_prompt(self, *, lemmas: List[str], definition: str) -> str:
        target_name = LanguageUtils.get_language_name(self.target_lang)
        return (
            "Baseline WordNet synset translation. Use only the provided gloss and literals.\n"
            f"Source language: {self.source_lang}\n"
            f"Target language: {self.target_lang} ({target_name})\n"
            f"English literals: {lemmas}\n"
            f"English gloss: {definition or '(missing)'}\n\n"
            "Return JSON with keys:\n"
            "- definition_translation: translated gloss\n"
            "- translated_synonyms: list of translated literals\n"
            "- notes: optional short note\n"
        )

    @staticmethod
    def _decode_llm_payload(raw: str) -> Dict[str, Any]:
        if not raw:
            return {"definition_translation": "", "translated_synonyms": []}
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, dict):
                return decoded
        except json.JSONDecodeError:
            pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = raw[start : end + 1]
            try:
                decoded = json.loads(snippet)
                if isinstance(decoded, dict):
                    return decoded
            except json.JSONDecodeError:
                pass

        return {"definition_translation": "", "translated_synonyms": []}

    @staticmethod
    def _coerce_to_str_list(value: Any) -> List[str]:
        if isinstance(value, (list, tuple)):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        return []


class TranslationPipeline(BaselineTranslationPipeline):
    """Compatibility alias for the baseline workflow implementation."""
