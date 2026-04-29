#!/usr/bin/env python3
"""Run repository-backed translation workflows over a resumable work-item queue."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

from wordnet_autotranslate.utils.llm_factory import (
    load_project_env,
    normalize_provider,
    resolve_base_url_for_provider,
    resolve_model_for_provider,
)

from wordnet_autotranslate.workflows.native_translation_queue import (
    claim_next_native_work_item,
    complete_native_work_item,
    fail_native_work_item,
    requeue_in_progress_native_work_items,
    summarize_native_batch_run,
)
from wordnet_autotranslate.workflows.synset_translation_workflow import (
    WorkflowConfig,
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
    parser = argparse.ArgumentParser(
        description=(
            "Run baseline/langgraph/conceptual repository workflows over an existing "
            "batch work-item queue, saving after every item."
        )
    )
    parser.add_argument("run_dir", help="Batch run directory containing work_items/pending")
    parser.add_argument(
        "--pipeline",
        choices=["baseline", "langgraph", "conceptual", "all", "dspy"],
        help="Override the pipeline stored in each work item.",
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
        help="Set Ollama thinking/reasoning effort when supported (use 'low' for gpt-oss smoke tests)",
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
        "--max-items",
        type=int,
        default=0,
        help="Maximum number of pending items to process; 0 means until queue is empty.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop the worker after the first failed item.",
    )
    parser.add_argument(
        "--requeue-in-progress",
        action="store_true",
        help="Move existing in-progress items back to pending before processing.",
    )
    return parser


def _write_claimed_work_item(path: Path, work_item: Dict[str, Any]) -> None:
    path.write_text(json.dumps(work_item, ensure_ascii=False, indent=2), encoding="utf-8")


def _print_event(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True), flush=True)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    load_project_env()
    provider, model, base_url = _resolve_provider_model_base_url(args)
    translation_mode = f"repo_{provider}"

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

    processed = 0
    failed_count = 0

    try:
        if args.requeue_in_progress:
            requeued = requeue_in_progress_native_work_items(run_dir)
            _print_event({"event": "requeued", "count": requeued["count"]})

        while args.max_items <= 0 or processed < args.max_items:
            claimed = claim_next_native_work_item(run_dir)
            if claimed is None:
                break

            work_item_path = Path(claimed["work_item_path"])
            work_item = dict(claimed["work_item"])
            pipeline = args.pipeline or str(work_item.get("pipeline") or "all")
            if args.pipeline:
                work_item["pipeline"] = pipeline
                _write_claimed_work_item(work_item_path, work_item)

            selector_value = str(work_item.get("selector_value") or "")
            row_number = work_item.get("row_number")
            _print_event(
                {
                    "event": "started",
                    "row_number": row_number,
                    "selector_value": selector_value,
                    "pipeline": pipeline,
                    "provider": provider,
                    "model": model,
                }
            )

            try:
                translation_result = run_translation_workflow(
                    work_item["synset_payload"],
                    pipeline=pipeline,
                    config=config,
                )
                completed = complete_native_work_item(
                    run_dir,
                    work_item_path,
                    translation_result,
                    translation_mode=translation_mode,
                )
                processed += 1
                _print_event(
                    {
                        "event": "completed",
                        "row_number": row_number,
                        "selector_value": selector_value,
                        "result_path": completed["result_path"],
                        "pending": completed["progress"]["work_item_counts"]["pending"],
                    }
                )
            except Exception as exc:
                failed_count += 1
                processed += 1
                failed = fail_native_work_item(
                    run_dir,
                    work_item_path,
                    str(exc),
                    details={
                        "error_type": type(exc).__name__,
                        "pipeline": pipeline,
                        "provider": provider,
                        "model": model,
                    },
                    translation_mode=translation_mode,
                )
                _print_event(
                    {
                        "event": "failed",
                        "row_number": row_number,
                        "selector_value": selector_value,
                        "message": str(exc),
                        "result_path": failed["result_path"],
                        "pending": failed["progress"]["work_item_counts"]["pending"],
                    }
                )
                if args.stop_on_error:
                    return 1

        progress = summarize_native_batch_run(run_dir)
        _print_event(
            {
                "event": "finished",
                "processed": processed,
                "failed": failed_count,
                "pending": progress["work_item_counts"]["pending"],
                "in_progress": progress["work_item_counts"]["in_progress"],
                "completed": progress["work_item_counts"]["completed"],
                "queue_empty": progress["all_finished"],
            }
        )
        return 1 if failed_count and args.stop_on_error else 0
    except KeyboardInterrupt:
        _print_event({"event": "interrupted", "processed": processed})
        return 130
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())