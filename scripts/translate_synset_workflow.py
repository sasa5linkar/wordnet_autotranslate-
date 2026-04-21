#!/usr/bin/env python3
"""CLI wrapper for agent-friendly synset translation workflow."""

from __future__ import annotations

import argparse
import sys

from wordnet_autotranslate.workflows.synset_translation_workflow import (
    build_resolution_result,
    WorkflowConfig,
    resolve_wordnet_synset,
    results_to_json,
    run_translation_workflow,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Translate an English WordNet synset to Serbian.")
    parser.add_argument("--english-id", help="ENG30 ID (e.g., ENG30-00001740-n)")
    parser.add_argument("--synset-name", help="WordNet synset name (e.g., entity.n.01)")
    parser.add_argument("--lemma", help="English lemma (requires --pos)")
    parser.add_argument("--pos", help="POS tag: n|v|a|r (Serbian b is accepted)")
    parser.add_argument("--sense-index", type=int, default=1, help="1-based sense index for lemma lookup")

    parser.add_argument(
        "--pipeline",
        default="langgraph",
        choices=["baseline", "langgraph", "conceptual", "all", "dspy"],
        help="Pipeline(s) to run (dspy is a legacy alias for baseline)",
    )
    parser.add_argument("--model", default="gpt-oss:120b", help="Ollama model name")
    parser.add_argument("--base-url", default="http://localhost:11434", help="Ollama base URL")
    parser.add_argument("--source-lang", default="en")
    parser.add_argument("--target-lang", default="sr")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument(
        "--resolve-only",
        action="store_true",
        help="Resolve the selector and print the synset payload without running a translation pipeline.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail immediately if any selected pipeline errors.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.lemma and not args.pos:
        parser.error("--lemma requires --pos")

    try:
        synset_payload = resolve_wordnet_synset(
            english_id=args.english_id,
            synset_name=args.synset_name,
            lemma=args.lemma,
            pos=args.pos,
            sense_index=args.sense_index,
        )
        if args.resolve_only:
            print(results_to_json(build_resolution_result(synset_payload)))
            return 0

        config = WorkflowConfig(
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            model=args.model,
            timeout=args.timeout,
            base_url=args.base_url,
            temperature=args.temperature,
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
