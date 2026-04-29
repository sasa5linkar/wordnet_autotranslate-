#!/usr/bin/env python3
"""Manage native-agent translation batch work items."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from wordnet_autotranslate.workflows.native_translation_queue import (
    claim_next_native_work_item,
    complete_native_work_item,
    fail_native_work_item,
    requeue_in_progress_native_work_items,
    summarize_native_batch_run,
)


def _load_optional_json(*, file_path: Optional[str], inline_json: Optional[str], label: str) -> Optional[Dict[str, Any]]:
    if file_path and inline_json:
        raise ValueError(f"Provide only one of --{label}-file or --{label}-json.")
    if file_path:
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
    elif inline_json:
        payload = json.loads(inline_json)
    else:
        return None
    if not isinstance(payload, dict):
        raise ValueError(f"{label} payload must be a JSON object.")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Claim, complete, fail, or inspect native-agent batch work items.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    claim = subparsers.add_parser("claim-next", help="Claim the next pending work item.")
    claim.add_argument("run_dir", help="Native batch run directory")

    complete = subparsers.add_parser("complete", help="Complete a claimed work item.")
    complete.add_argument("run_dir", help="Native batch run directory")
    complete.add_argument("work_item", help="Path to the pending or in-progress work item JSON")
    complete.add_argument("--result-file", help="Path to a JSON file containing the translation_result object")
    complete.add_argument("--result-json", help="Inline JSON string containing the translation_result object")

    fail = subparsers.add_parser("fail", help="Fail a claimed work item.")
    fail.add_argument("run_dir", help="Native batch run directory")
    fail.add_argument("work_item", help="Path to the pending or in-progress work item JSON")
    fail.add_argument("--message", required=True, help="Human-readable failure message")
    fail.add_argument("--details-file", help="Path to a JSON file with structured error details")
    fail.add_argument("--details-json", help="Inline JSON string with structured error details")

    status = subparsers.add_parser("status", help="Show current queue progress.")
    status.add_argument("run_dir", help="Native batch run directory")

    requeue = subparsers.add_parser(
        "requeue-in-progress",
        help="Move all in-progress work items back to pending after interruption.",
    )
    requeue.add_argument("run_dir", help="Native batch run directory")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        run_dir = Path(args.run_dir)
        if args.command == "claim-next":
            claimed = claim_next_native_work_item(run_dir)
            if claimed is None:
                payload = {
                    "status": "empty",
                    "progress": summarize_native_batch_run(run_dir),
                }
            else:
                payload = {
                    "status": "claimed",
                    **claimed,
                }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        if args.command == "complete":
            translation_result = _load_optional_json(
                file_path=args.result_file,
                inline_json=args.result_json,
                label="result",
            )
            if translation_result is None:
                raise ValueError("Provide one of --result-file or --result-json.")
            payload = complete_native_work_item(run_dir, Path(args.work_item), translation_result)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        if args.command == "fail":
            details = _load_optional_json(
                file_path=args.details_file,
                inline_json=args.details_json,
                label="details",
            )
            payload = fail_native_work_item(
                run_dir,
                Path(args.work_item),
                args.message,
                details=details,
            )
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        if args.command == "status":
            payload = summarize_native_batch_run(run_dir)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        if args.command == "requeue-in-progress":
            payload = requeue_in_progress_native_work_items(run_dir)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        raise ValueError(f"Unsupported command {args.command!r}")
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
