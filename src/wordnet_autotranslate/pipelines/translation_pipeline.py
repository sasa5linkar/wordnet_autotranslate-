"""
Translation Pipeline using DSPy for WordNet auto-translation.

Enhancements:
- Load examples from enhanced JSON pairs (v2.0) under examples/<lang>/
- Save translation results to JSON with metadata
- Generate few-shot examples (first or random) from loaded examples
"""

from typing import List, Dict, Optional, Tuple, Union, Callable
from pathlib import Path
import json
import random
from datetime import datetime
import re
from collections import Counter

from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

try:
    import dspy
    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False

# Default rubric for LLM-as-judge evaluation
DEFAULT_JUDGE_RUBRIC = {
    "goal": "Assess the quality of a predicted translation of a WordNet definition/sense against a gold translation.",
    "criteria": [
        {
            "name": "meaning_equivalence",
            "weight": 0.5,
            "description": "Predicted translation preserves the meaning and sense of the source as expressed by the gold translation."
        },
        {
            "name": "terminology_appropriateness",
            "weight": 0.2,
            "description": "Terminology/lexical choice is appropriate for WordNet-like dictionary definitions."
        },
        {
            "name": "fluency_grammar",
            "weight": 0.2,
            "description": "Fluent and grammatically correct in the target language."
        },
        {
            "name": "conciseness",
            "weight": 0.1,
            "description": "Concise and definition-style (avoid unnecessary verbosity)."
        }
    ],
    "scoring": {
        "scale": [0, 1],
        "anchors": {
            "1.0": "Fully correct: meaning equivalent or trivially paraphrased with correct terminology.",
            "0.5": "Partially correct: captures core meaning but has notable errors or omissions.",
            "0.0": "Incorrect: wrong meaning or largely unrelated to the gold."
        },
        "verdict_labels": ["correct", "partially_correct", "incorrect"],
        "error_categories": ["lexical_choice", "meaning", "grammar", "other"]
    },
    "instructions": "Return ONLY a strict JSON object with keys: score (0..1), verdict (one of: correct|partially_correct|incorrect), reasoning (short), category (one of: lexical_choice|meaning|grammar|other). Do not include extra text."
}


class TranslationPipeline:
    """Main translation pipeline for WordNet synset translation."""
    
    def __init__(self, source_lang: str = 'en', target_lang: str = 'es'):
        """
        Initialize translation pipeline.
        
        Args:
            source_lang: Source language code (default: 'en')
            target_lang: Target language code (default: 'es')
        """
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.examples_path = Path(__file__).parent.parent.parent.parent / "examples"
        self._examples_cache = None  # type: Optional[Dict]
        # Central language field map: customize per language to avoid hardcoded keys
        # Keys: definition, lemmas (aka synonyms), examples, usage, relations, id
        # Provide fallbacks to generic keys if language-specific ones are missing.
        self.LANGUAGE_FIELD_MAP: Dict[str, Dict[str, Optional[str]]] = {
            # English fields as found in enhanced example JSON
            "en": {
                "definition": "english_definition",
                "lemmas": "english_lemmas",
                "examples": "english_examples",
                "usage": None,  # English side typically doesn't provide 'usage'
                "relations": "english_relations",
                "id": "english_id",
            },
            # Serbian fields as found in enhanced example JSON
            "sr": {
                "definition": "serbian_definition",
                "lemmas": "serbian_synonyms",
                "examples": None,  # Serbian side typically doesn't provide 'examples'
                "usage": "serbian_usage",
                "relations": "serbian_relations",
                "id": "serbian_id",
            },
        }
        # Generic fallbacks used for any language when language-specific keys are missing
        self.GENERIC_FALLBACKS: Dict[str, List[str]] = {
            "definition": ["definition"],
            "lemmas": ["lemmas", "synonyms"],
            "examples": ["examples"],
            "usage": ["usage"],
            "relations": ["relations"],
            "id": ["id"],
        }
        
    def load_english_synsets(self) -> List[Dict]:
        """Load English WordNet synsets."""
        # TODO: Implement WordNet loading
        return []
    
    def load_target_synsets(self) -> List[Dict]:
        """Load target language synsets if available."""
        # TODO: Implement target language synset loading
        return []
    
    def load_examples(self) -> Dict:
        """Load example synset pairs for the target language.

        Prefers enhanced JSON examples if present:
        - Looks for *.json under examples/<target_lang>/ (prefers *_enhanced.json)
        - Expects structure with top-level keys: pairs (list), metadata (dict)

        Returns a dict with keys:
        - pairs: list
        - metadata: dict
        """
        target_path = self.examples_path / self.target_lang
        result: Dict = {"pairs": [], "metadata": {}}

        # Attempt JSON-first loading
        if target_path.exists():
            json_files: List[Path] = sorted(target_path.glob("*.json"))
            # Prefer *_enhanced.json
            preferred = [p for p in json_files if p.stem.endswith("_enhanced")]
            to_try = preferred + [p for p in json_files if p not in preferred]

            for jf in to_try:
                try:
                    with open(jf, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict) and isinstance(data.get("pairs"), list):
                        result["pairs"] = data.get("pairs", [])
                        result["metadata"] = data.get("metadata", {})

                        self._examples_cache = result
                        return result
                except Exception:
                    # Try next JSON file if available
                    continue

        self._examples_cache = result
        return result

    # ---------------------------
    # Translation helpers
    # ---------------------------
    def _build_source_text(self, synset: Dict) -> str:
        """Construct a source text from a synset dict based on source_lang.

        Tries definition, then lemmas/examples as fallback.
        """
        # Definition first
        definition = self._get_text_field(synset, kind="definition", lang=self.source_lang)
        if definition:
            return definition

        # Lemmas / synonyms next
        lemmas = self._get_list_field(synset, kind="lemmas", lang=self.source_lang)
        if lemmas:
            return ", ".join([str(x) for x in lemmas if isinstance(x, str)]).strip()

        # Examples next
        examples = self._get_list_field(synset, kind="examples", lang=self.source_lang)
        if examples:
            first_ex = next((e for e in examples if isinstance(e, str) and e.strip()), None)
            if first_ex:
                return first_ex.strip()

        # Usage (if any) last
        usage = self._get_text_field(synset, kind="usage", lang=self.source_lang)
        if usage:
            return usage

        return ""

    def _build_synset_context(self, synset: Dict) -> str:
        """Build a compact, structured context block from a synset dict.

        Includes: definition, synonyms/lemmas, usage/examples (first), and
        a brief relations summary if available in the pair (e.g., *_relations).
        """
        lines: List[str] = []

        # Definitions for source and target if present
        src_def = self._get_text_field(synset, kind="definition", lang=self.source_lang)
        if src_def:
            lines.append(f"Definition [{self.source_lang}]: {src_def}")
        tgt_def = self._get_text_field(synset, kind="definition", lang=self.target_lang)
        if tgt_def and tgt_def != src_def:
            lines.append(f"Definition [{self.target_lang}]: {tgt_def}")

        # Synonyms / lemmas (source and target)
        src_lemmas = self._get_list_field(synset, kind="lemmas", lang=self.source_lang)
        if src_lemmas:
            lines.append(f"Lemmas/Synonyms [{self.source_lang}]: {', '.join([s for s in src_lemmas if isinstance(s, str)])}")
        tgt_lemmas = self._get_list_field(synset, kind="lemmas", lang=self.target_lang)
        if tgt_lemmas:
            lines.append(f"Lemmas/Synonyms [{self.target_lang}]: {', '.join([s for s in tgt_lemmas if isinstance(s, str)])}")

        # Usage / examples
        tgt_usage = self._get_text_field(synset, kind="usage", lang=self.target_lang)
        if tgt_usage:
            lines.append(f"Usage [{self.target_lang}]: {tgt_usage}")
        src_examples = self._get_list_field(synset, kind="examples", lang=self.source_lang)
        if src_examples:
            eg = next((e for e in src_examples if isinstance(e, str) and e.strip()), None)
            if eg:
                lines.append(f"Example [{self.source_lang}]: {eg.strip()}")

        # Relations summary (prefer target, fall back to source)
        rel_obj = self._get_relations(synset, lang=self.target_lang) or self._get_relations(synset, lang=self.source_lang)
        if isinstance(rel_obj, dict):
            total = rel_obj.get("total_relations")
            by_type = rel_obj.get("relations_by_type") or {}
            parts = []
            for k, v in list(by_type.items())[:5]:
                try:
                    parts.append(f"{k}:{int(v)}")
                except Exception:
                    parts.append(f"{k}:{v}")
            if total is not None or parts:
                rel_line = f"Relations: total={total}"
                if parts:
                    rel_line += f"; types=({', '.join(parts)})"
                lines.append(rel_line)

        return "\n".join(lines)

    def _dummy_translate(self, text: str) -> str:
        """Fallback translation when no model is wired yet.

        Currently returns the input text unchanged (identity). Replace with
        an actual model call when integrating DSPy or another backend.
        """
        return text

    # ---------------------------
    # Language-field utilities
    # ---------------------------
    def _field_candidates(self, kind: str, lang: str) -> List[str]:
        cfg = self.LANGUAGE_FIELD_MAP.get(lang, {})
        primary = cfg.get(kind)
        cands: List[str] = []
        if primary:
            cands.append(primary)
        # Also consider the other side if commonly mirrored (e.g., definition)
        # but avoid cross-language bleed by focusing on generic fallbacks next
        cands.extend(self.GENERIC_FALLBACKS.get(kind, []))
        return cands

    def _get_text_field(self, obj: Dict, kind: str, lang: str) -> str:
        for key in self._field_candidates(kind, lang):
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return ""

    def _get_list_field(self, obj: Dict, kind: str, lang: str) -> List[str]:
        for key in self._field_candidates(kind, lang):
            val = obj.get(key)
            if isinstance(val, list) and val:
                # keep only stringy entries
                return [str(x) for x in val if isinstance(x, (str, int, float))]
        return []

    def _get_relations(self, obj: Dict, lang: str) -> Optional[Dict]:
        for key in self._field_candidates("relations", lang):
            val = obj.get(key)
            if isinstance(val, dict):
                return val
        return None

    def _get_id(self, obj: Dict, lang: str) -> Optional[str]:
        for key in self._field_candidates("id", lang):
            val = obj.get(key)
            if isinstance(val, (str, int)):
                return str(val)
        return None

    # ---------------------------
    # Evaluation helpers and API
    # ---------------------------
    def _normalize_text(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        text = text.lower().strip()
        # remove basic punctuation
        text = re.sub(r"[\.,!?;:\-\(\)\[\]\{\}\"'`]+", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _tokenize(self, text: str) -> List[str]:
        return self._normalize_text(text).split()

    def _token_f1(self, pred: str, gold: str) -> float:
        pred_tokens = self._tokenize(pred)
        gold_tokens = self._tokenize(gold)
        if not pred_tokens or not gold_tokens:
            return 0.0
        pred_counts = Counter(pred_tokens)
        gold_counts = Counter(gold_tokens)
        overlap = sum(min(pred_counts[t], gold_counts[t]) for t in pred_counts)
        precision = overlap / max(1, len(pred_tokens))
        recall = overlap / max(1, len(gold_tokens))
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    def evaluate_examples(
        self,
        examples: List[Dict[str, str]],
        translator: Optional[Callable[[str], str]] = None,
        metrics: Optional[List[str]] = None,
    ) -> Dict[str, Union[Dict, List[Dict]]]:
        """Evaluate a translator function on a gold set of examples.

        Args:
            examples: List with {'input': text, 'output': gold, 'context': {...}}.
            translator: Callable that maps input->prediction. Defaults to identity.
            metrics: Which metrics to compute. Defaults to ['exact','bleu','f1'].

        Returns:
            Dict with 'summary' (global averages) and 'details' per example.
        """
        if metrics is None:
            metrics = ["exact", "bleu", "f1"]
        if translator is None:
            translator = self._dummy_translate

        smooth = SmoothingFunction().method1
        details: List[Dict] = []
        totals = {m: 0.0 for m in metrics}

        for ex in examples:
            inp = ex.get("input", "")
            gold = ex.get("output", "")
            pred = translator(inp)

            scores: Dict[str, float] = {}
            if "exact" in metrics:
                scores["exact"] = 1.0 if self._normalize_text(pred) == self._normalize_text(gold) else 0.0
            if "f1" in metrics:
                scores["f1"] = self._token_f1(pred, gold)
            if "bleu" in metrics:
                # Use unigram-to-4gram BLEU with smoothing
                ref_tokens = self._tokenize(gold)
                hyp_tokens = self._tokenize(pred)
                if ref_tokens and hyp_tokens:
                    try:
                        scores["bleu"] = float(sentence_bleu([ref_tokens], hyp_tokens, smoothing_function=smooth))
                    except Exception:
                        scores["bleu"] = 0.0
                else:
                    scores["bleu"] = 0.0

            for m in metrics:
                totals[m] += scores.get(m, 0.0)

            details.append({
                "input": inp,
                "gold": gold,
                "pred": pred,
                "metrics": scores,
            })

        n = max(1, len(details))
        summary = {
            "count": len(details),
            "metrics": {m: totals[m] / n for m in metrics},
        }
        return {"summary": summary, "details": details}

    def evaluate_from_split(
        self,
        count: int = 3,
        strategy: str = "first",
        prefer_with_usage: bool = True,
        eval_limit: Optional[int] = None,
        translator: Optional[Callable[[str], str]] = None,
        metrics: Optional[List[str]] = None,
    ) -> Dict[str, Union[Dict, List[Dict]]]:
        """Convenience method: build few_shots+eval split and evaluate on eval.

        Returns the evaluation report. You can supply your own translator that
        uses few_shots to construct a prompt; this method does not enforce that
        link, it only computes scores on the eval set.
        """
        split = self.get_few_shot_examples(
            count=count,
            strategy=strategy,
            prefer_with_usage=prefer_with_usage,
            include_eval=True,
            eval_limit=eval_limit,
        )
        eval_set = split.get("eval", []) if isinstance(split, dict) else []
        return self.evaluate_examples(eval_set, translator=translator, metrics=metrics)

    def translate_one(self, synset: Dict, few_shots: Optional[List[Dict[str, str]]] = None) -> Dict:
        """Translate a single synset sequentially.

        Args:
            synset: Source synset dictionary.
            few_shots: Optional few-shot examples to guide translation.

        Returns:
            Translation record with fields: source_id, source_text, translated_text,
            and metadata.
        """
        source_id = self._get_id(synset, self.source_lang) or self._get_id(synset, self.target_lang)
        source_text = self._build_source_text(synset)
        source_context = self._build_synset_context(synset)

        # Guard: nothing to translate
        if not source_text:
            return {
                "source_id": source_id,
                "source_text": "",
                "translated_text": "",
                "metadata": {"status": "skipped", "reason": "empty_source"},
            }

        # TODO: replace with DSPy program invocation when wired
        translated = self._dummy_translate(source_text)

        return {
            "source_id": source_id,
            "source_text": source_text,
            "translated_text": translated,
            "metadata": {
                "source_lang": self.source_lang,
                "target_lang": self.target_lang,
                "used_few_shots": bool(few_shots),
            },
            "source_context": source_context,
        }

    def save_translations(
        self,
        translations: List[Dict],
        output_path: Optional[Union[Path, str]] = None,
        format_version: str = "pipeline-1.0",
        include_metadata: bool = True,
    ) -> Path:
        """Save translation results to JSON with metadata.

        Args:
            translations: List of translation dicts produced by this pipeline.
            output_path: Where to save the JSON. If None, defaults to
                examples/<target_lang>/translations_<timestamp>.json
            format_version: A small version tag for this file format.
            include_metadata: If True, include metadata block.

        Returns:
            Path to the saved file.
        """
        # Determine output path
        if output_path is None:
            out_dir = self.examples_path / self.target_lang
            out_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = out_dir / f"translations_{ts}.json"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        payload: Dict = {"translations": translations}

        if include_metadata:
            payload["metadata"] = {
                "total_translations": len(translations),
                "source_lang": self.source_lang,
                "target_lang": self.target_lang,
                "format_version": format_version,
                "export_timestamp": datetime.now().isoformat(),
                "created_by": "WordNet Auto-Translation Pipeline",
            }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return Path(output_path)

    def get_few_shot_examples(
        self,
        count: int = 3,
        strategy: str = "first",
        prefer_with_usage: bool = True,
        include_eval: bool = True,
        eval_limit: Optional[int] = None,
    ) -> Union[List[Dict[str, str]], Dict[str, List[Dict[str, str]]]]:
        """Build few-shot examples and optionally an evaluation split.

        Examples are built from JSON pairs when available.

        Args:
            count: Number of few-shot examples (1–3 recommended).
            strategy: "first" or "random" for the few-shot selection.
            prefer_with_usage: Prioritize items with usage/examples.
            include_eval: If True, also return a gold evaluation set from remaining items.
            eval_limit: Optional cap on evaluation examples.

        Returns:
            - If include_eval is False: List of few-shot example dicts.
            - If include_eval is True: Dict with keys:
                { 'few_shots': [...], 'eval': [...] }
        """
        examples = self._examples_cache or self.load_examples()
        pairs: List[Dict] = examples.get("pairs", [])
        if not pairs:
            return []

        # Score pairs to prefer those with richer context
        def _score_pair(p: Dict) -> Tuple[int, int]:
            # Prefer items with target usage and source examples to enrich prompts
            has_tgt_usage = 1 if self._get_text_field(p, kind="usage", lang=self.target_lang) else 0
            has_src_examples = 1 if self._get_list_field(p, kind="examples", lang=self.source_lang) else 0
            return has_tgt_usage, has_src_examples

        candidates = pairs[:]
        if prefer_with_usage:
            candidates.sort(key=_score_pair, reverse=True)

        # Choose few-shot subset
        k = max(0, min(count, len(candidates)))
        if strategy == "random" and k > 0:
            chosen = random.sample(candidates, k)
        else:
            chosen = candidates[:k]

        # Build prompt-ready examples mapper
        def _to_example(p: Dict) -> Optional[Dict[str, str]]:
            # Build source text: definition -> lemmas -> example
            source = self._get_text_field(p, kind="definition", lang=self.source_lang)
            if not source:
                src_lemmas = self._get_list_field(p, kind="lemmas", lang=self.source_lang)
                if src_lemmas:
                    source = " ".join(src_lemmas)
            if not source:
                src_examples = self._get_list_field(p, kind="examples", lang=self.source_lang)
                if src_examples:
                    source = src_examples[0]

            # Build target gold: definition -> lemmas/synonyms -> usage
            target = self._get_text_field(p, kind="definition", lang=self.target_lang)
            if not target:
                tgt_lemmas = self._get_list_field(p, kind="lemmas", lang=self.target_lang)
                if tgt_lemmas:
                    target = ", ".join(tgt_lemmas)
            if not target:
                usage = self._get_text_field(p, kind="usage", lang=self.target_lang)
                if usage:
                    target = usage

            if not source or not target:
                return None

            # Provide a minimal, language-agnostic context
            return {
                "input": source,
                "output": target,
                "context": {
                    f"lemmas_{self.source_lang}": self._get_list_field(p, kind="lemmas", lang=self.source_lang),
                    f"lemmas_{self.target_lang}": self._get_list_field(p, kind="lemmas", lang=self.target_lang),
                    f"examples_{self.source_lang}": self._get_list_field(p, kind="examples", lang=self.source_lang),
                    f"usage_{self.target_lang}": self._get_text_field(p, kind="usage", lang=self.target_lang),
                }
            }

        # Few-shot examples
        few_shots: List[Dict[str, str]] = []
        for p in chosen:
            ex = _to_example(p)
            if ex:
                few_shots.append(ex)

        if not include_eval:
            return few_shots

        # Evaluation examples from remaining candidates
        remaining = [p for p in candidates if p not in chosen]
        if eval_limit is not None and eval_limit >= 0:
            remaining = remaining[:eval_limit]

        eval_examples: List[Dict[str, str]] = []
        for p in remaining:
            ex = _to_example(p)
            if ex:
                eval_examples.append(ex)

        return {"few_shots": few_shots, "eval": eval_examples}
    
    def translate(
        self,
        synsets: List[Dict],
        few_shot_strategy: str = "first",
        few_shot_count: int = 3,
        checkpoint_path: Optional[Union[Path, str]] = None,
        checkpoint_every: int = 0,
    ) -> List[Dict]:
        """Translate synsets sequentially (one-by-one).

        This approach improves observability, allows checkpointing, and can adapt
        few-shots over time.

        Args:
            synsets: List of synsets to translate.
            few_shot_strategy: "first" or "random" selection of few-shots.
            few_shot_count: How many few-shot examples to include.
            checkpoint_path: If provided, will save partial results to this file.
            checkpoint_every: Save every N items (>0). 0 disables periodic saves.

        Returns:
            List of translation dicts.
        """
        results: List[Dict] = []

        # Prepare few-shots once (could adapt per-item in the future)
        try:
            fewshot_result = self.get_few_shot_examples(
                count=few_shot_count,
                strategy=few_shot_strategy,
                prefer_with_usage=True,
            )
            if isinstance(fewshot_result, dict):
                few_shots = fewshot_result.get("few_shots", [])
            else:
                few_shots = fewshot_result
        except Exception:
            few_shots = []

        for idx, syn in enumerate(synsets, start=1):
            try:
                translated = self.translate_one(syn, few_shots=few_shots)
                results.append(translated)
            except Exception as e:
                results.append({
                    "source_id": syn.get("id"),
                    "source_text": self._build_source_text(syn),
                    "translated_text": "",
                    "metadata": {"status": "error", "error": str(e)},
                })

            # Periodic checkpoint save
            if checkpoint_every and checkpoint_every > 0 and (idx % checkpoint_every == 0):
                try:
                    self.save_translations(results, output_path=checkpoint_path or None)
                except Exception:
                    # Non-fatal: continue translating
                    pass

        # Final save if a path was given and we didn't save periodically
        if checkpoint_path and (not checkpoint_every or checkpoint_every <= 0):
            try:
                self.save_translations(results, output_path=checkpoint_path)
            except Exception:
                pass

        return results

    # ---------------------------
    # DSPy integration: configuration and LLM-as-judge (single example)
    # ---------------------------
    def configure_lm(self, lm: Optional[object] = None, **kwargs) -> None:
        """Configure DSPy with a language model.

        Options:
        - Pass an instantiated LM via `lm` (preferred when you manage credentials externally).
        - Or pass model details via kwargs with at least model="<provider>:<name>" or model="<name>".
          We'll attempt a minimal construction using common DSPy wrappers.

        Examples:
            pipeline.configure_lm(model="openai:gpt-4o-mini", api_key=os.environ["OPENAI_API_KEY"])  # if your DSPy version supports dspy.OpenAI
        """
        if not DSPY_AVAILABLE:
            raise ImportError("DSPy is not installed. Please install dspy to use LLM-based judging.")

        # Late import to ensure ImportError is raised only when needed
        import dspy as _dspy

        if lm is None:
            model = kwargs.pop("model", None)
            if not model:
                raise ValueError("Provide either an 'lm' instance or a model name via model='provider:name' or model='name'.")
            # Best-effort construction using common wrappers
            name = model.split(":", 1)[-1]
            if hasattr(_dspy, "OpenAI"):
                lm = _dspy.OpenAI(model=name, **kwargs)
            elif hasattr(_dspy, "LM"):
                lm = _dspy.LM(model=name, **kwargs)
            else:
                raise RuntimeError("This DSPy version doesn't expose a known LM wrapper (OpenAI/LM). Pass an instantiated lm instead.")

        _dspy.configure(lm=lm)
        # Mark as configured for later checks
        setattr(self, "_lm_configured", True)

    def evaluate_one(
        self,
        source_text: str,
        predicted_translation: str,
        gold_translation: str,
        rubric: Optional[Dict] = None,
        temperature: float = 0.2,
        max_retries: int = 2,
    ) -> Dict:
        """Evaluate a single prediction vs gold using an LLM judge (if available).

        If DSPy isn't available or not configured, falls back to classical metrics.

        Returns a dict with fields:
          - judge: {score, verdict, reasoning, category}
          - classic: {exact, f1, bleu}
          - raw: raw_model_output (if LLM was used)
          - used_llm: bool
        """
        # Always compute classical metrics for transparency
        classic_scores = {
            "exact": 1.0 if self._normalize_text(predicted_translation) == self._normalize_text(gold_translation) else 0.0,
            "f1": self._token_f1(predicted_translation, gold_translation),
            "bleu": 0.0,
        }
        try:
            smooth = SmoothingFunction().method1
            ref_tokens = self._tokenize(gold_translation)
            hyp_tokens = self._tokenize(predicted_translation)
            if ref_tokens and hyp_tokens:
                classic_scores["bleu"] = float(sentence_bleu([ref_tokens], hyp_tokens, smoothing_function=smooth))
        except Exception:
            classic_scores["bleu"] = 0.0

        # If no DSPy, return classical only
        if not DSPY_AVAILABLE or not getattr(self, "_lm_configured", False):
            return {
                "judge": {
                    "score": classic_scores["f1"],
                    "verdict": "fallback",
                    "reasoning": "DSPy judge not available; using classical metrics as proxy.",
                    "category": "other",
                },
                "classic": classic_scores,
                "raw": None,
                "used_llm": False,
            }

        import dspy as _dspy

        # Prepare rubric
        rubric_obj = rubric or DEFAULT_JUDGE_RUBRIC
        rubric_json = json.dumps(rubric_obj, ensure_ascii=False)

        # Define a local signature for the judge
        class JudgeSignature(_dspy.Signature):
            """Judge the predicted translation against the gold translation.

            Return ONLY JSON with keys: score, verdict, reasoning, category.
            """
            source_text: str = "The original source text or definition."
            predicted_translation: str = "The model's translation to evaluate."
            gold_translation: str = "The gold/reference translation."
            rubric: str = "JSON rubric describing evaluation criteria."
            answer: str = (
                "Return STRICT JSON: {\"score\": <0..1>, \"verdict\": \"correct|partially_correct|incorrect\", "
                "\"reasoning\": <short>, \"category\": \"lexical_choice|meaning|grammar|other\"}"
            )

        predictor = _dspy.Predict(JudgeSignature)

        def _extract_json(text: str) -> Optional[Dict]:
            if not isinstance(text, str):
                return None
            # Try direct parse first
            try:
                return json.loads(text)
            except Exception:
                pass
            # Heuristic: find first {...} block
            try:
                match = re.search(r"\{[\s\S]*\}", text)
                if match:
                    return json.loads(match.group(0))
            except Exception:
                return None
            return None

        last_raw = None
        parsed = None
        for _ in range(max(1, max_retries)):
            out = predictor(
                source_text=source_text,
                predicted_translation=predicted_translation,
                gold_translation=gold_translation,
                rubric=rubric_json,
            )
            # The attribute name can differ across DSPy versions; try common patterns
            candidate = None
            for attr in ("answer", "pred", "prediction", "text"):
                if hasattr(out, attr):
                    candidate = getattr(out, attr)
                    break
            if candidate is None:
                candidate = str(out)
            last_raw = candidate
            parsed = _extract_json(candidate)
            if parsed and all(k in parsed for k in ("score", "verdict", "reasoning", "category")):
                break

        # Validate and coerce parsed result
        judge = {
            "score": float(parsed.get("score", classic_scores["f1"])) if isinstance(parsed, dict) else classic_scores["f1"],
            "verdict": parsed.get("verdict", "partially_correct") if isinstance(parsed, dict) else "partially_correct",
            "reasoning": parsed.get("reasoning", "" ) if isinstance(parsed, dict) else "",
            "category": parsed.get("category", "other") if isinstance(parsed, dict) else "other",
        }

        # Clamp score to [0,1]
        try:
            judge["score"] = max(0.0, min(1.0, float(judge["score"])) )
        except Exception:
            judge["score"] = classic_scores["f1"]

        # Ensure verdict in allowed set
        allowed = {"correct", "partially_correct", "incorrect"}
        if judge.get("verdict") not in allowed:
            judge["verdict"] = "partially_correct"

        return {
            "judge": judge,
            "classic": classic_scores,
            "raw": last_raw,
            "used_llm": True,
        }