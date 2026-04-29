#!/usr/bin/env python3
"""CLI wrapper for agent-friendly synset translation workflow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Union

from wordnet_autotranslate.utils.llm_factory import (
    load_project_env,
    normalize_provider,
    resolve_base_url_for_provider,
    resolve_model_for_provider,
)

from wordnet_autotranslate.workflows.synset_translation_workflow import (
    WorkflowConfig,
    resolve_wordnet_synset,
    results_to_json,
    run_translation_workflow,
)


def _resolve_reasoning_arg(args: argparse.Namespace) -> Optional[Union[bool, str]]:
    if args.disable_reasoning and args.reasoning is not None:
        raise ValueError("Use either --disable-reasoning or --reasoning, not both.")
    if args.disable_reasoning:
        return False
    return args.reasoning


def _resolve_provider_model_base_url(args: argparse.Namespace) -> tuple[str, str, str | None]:
    provider = normalize_provider(args.provider)
    model = resolve_model_for_provider(provider, args.model)
    base_url = resolve_base_url_for_provider(provider, args.base_url)
    return provider, model, base_url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Translate an English WordNet synset to Serbian.")
    parser.add_argument("--ili", help="ILI selector (e.g., i35545)")
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
    parser.add_argument(
        "--provider",
        default=None,
        choices=["ollama", "openai"],
        help="Chat model provider. Defaults to LLM_PROVIDER from .env, or ollama.",
    )
    parser.add_argument(
        "--model",
        help="Model name. Defaults to OLLAMA_MODEL or OPENAI_MODEL from .env for the provider.",
    )
    parser.add_argument("--base-url", help="Provider base URL override")
    parser.add_argument("--source-lang", default="en")
    parser.add_argument("--target-lang", default="sr")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--num-ctx", type=int, help="Ollama context window override")
    parser.add_argument("--num-predict", type=int, help="Ollama max generated tokens per request")
    parser.add_argument(
        "--disable-reasoning",
        action="store_true",
        help="Disable model thinking/reasoning mode when supported by Ollama",
    )
    parser.add_argument(
        "--reasoning",
        choices=["low", "medium", "high"],
        help="Set model reasoning effort when supported (for example: low, medium, high)",
    )
    parser.add_argument(
        "--json-format",
        action="store_true",
        help="Request Ollama JSON response format when supported",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail immediately if any selected pipeline errors.",
    )
    parser.add_argument(
        "--output",
        help="Write the UTF-8 JSON result to this file instead of printing it to stdout.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.lemma and not args.pos:
        parser.error("--lemma requires --pos")

    try:
        load_project_env()
        provider, model, base_url = _resolve_provider_model_base_url(args)
        synset_payload = resolve_wordnet_synset(
            ili=args.ili,
            english_id=args.english_id,
            synset_name=args.synset_name,
            lemma=args.lemma,
            pos=args.pos,
            sense_index=args.sense_index,
        )
        config = WorkflowConfig(
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            provider=provider,
            model=model,
            timeout=args.timeout,
            base_url=base_url or "",
            temperature=args.temperature,
            strict=args.strict,
            num_ctx=args.num_ctx,
            num_predict=args.num_predict,
            reasoning=_resolve_reasoning_arg(args),
            response_format="json" if args.json_format else None,
        )
        result = run_translation_workflow(
            synset_payload,
            pipeline=args.pipeline,
            config=config,
        )
        output = results_to_json(result)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output, encoding="utf-8")
            print(f"Wrote {output_path}")
        else:
            print(output)
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
