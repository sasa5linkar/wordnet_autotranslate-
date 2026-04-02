#!/usr/bin/env python3
"""CLI wrapper for agent-friendly synset translation workflow."""

from __future__ import annotations

import argparse
import sys

from wordnet_autotranslate.workflows.synset_translation_workflow import (
    WorkflowConfig,
    resolve_wordnet_synset,
    results_to_json,
    run_translation_workflow,
)
from wordnet_autotranslate.workflows.selector_validation import (
    validate_selector_families,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Translate an English WordNet synset to Serbian."
    )
    parser.add_argument("--english-id", help="ENG30 ID (e.g., ENG30-00001740-n)")
    parser.add_argument("--synset-name", help="WordNet synset name (e.g., entity.n.01)")
    parser.add_argument("--lemma", help="English lemma (requires --pos)")
    parser.add_argument("--pos", help="POS tag: n|v|a|r (Serbian b is accepted)")
    parser.add_argument(
        "--sense-index",
        type=int,
        default=1,
        help="1-based sense index for lemma lookup",
    )

    parser.add_argument(
        "--pipeline",
        default="langgraph",
        choices=["langgraph", "conceptual", "all", "dspy"],
        help="Pipeline(s) to run",
    )
    parser.add_argument("--model", default="gpt-oss:120b", help="Ollama model name")
    parser.add_argument(
        "--base-url", default="http://localhost:11434", help="Ollama base URL"
    )
    parser.add_argument("--source-lang", default="en")
    parser.add_argument("--target-lang", default="sr")
    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="Per-request timeout in seconds (30-3600; default 1800 for local long prompts).",
    )
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail immediately if any selected pipeline errors.",
    )
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--retry-delay-seconds", type=float, default=1.0)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.lemma and not args.pos:
        parser.error("--lemma requires --pos")
    try:
        validate_selector_families(
            english_id=args.english_id,
            synset_name=args.synset_name,
            lemma=args.lemma,
            pos=args.pos,
        )
    except ValueError:
        parser.error(
            "provide exactly one selector: --english-id OR --synset-name OR --lemma + --pos"
        )

    try:
        synset_payload = resolve_wordnet_synset(
            english_id=args.english_id,
            synset_name=args.synset_name,
            lemma=args.lemma,
            pos=args.pos,
            sense_index=args.sense_index,
        )
        config = WorkflowConfig(
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            model=args.model,
            timeout=args.timeout,
            base_url=args.base_url,
            temperature=args.temperature,
            max_retries=args.max_retries,
            retry_delay_seconds=args.retry_delay_seconds,
            strict=args.strict,
        )
        result = run_translation_workflow(
            synset_payload,
            pipeline=args.pipeline,
            config=config,
        )
        print(results_to_json(result))
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
