#!/usr/bin/env python3
"""Prepare a sheet/xlsx/csv batch for native-agent translation without invoking model backends."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from wordnet_autotranslate.workflows.sheet_translation_workflow import (
    SheetBatchConfig,
    SheetColumnOverrides,
    prepare_native_sheet_translation_batch,
    WorkflowConfig,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare a public Google Sheet or local CSV/XLSX snapshot for native-agent Serbian translation."
        )
    )
    parser.add_argument(
        "source",
        help="Public Google Sheet URL or local CSV/XLSX path",
    )
    parser.add_argument(
        "--gid",
        help="Google Sheet gid/tab identifier when the source URL should export a non-default tab",
    )
    parser.add_argument(
        "--output-dir",
        default="native_batch_runs",
        help="Base directory under which a timestamped native-agent batch run folder will be created",
    )
    parser.add_argument(
        "--pipeline",
        default="all",
        choices=["baseline", "langgraph", "conceptual", "all", "dspy"],
        help="Default reasoning mode when a row does not define its own pipeline column",
    )
    parser.add_argument(
        "--download-timeout",
        type=int,
        default=30,
        help="Timeout in seconds for downloading the input sheet snapshot",
    )
    parser.add_argument("--ili-column", help="Exact header name for ILI selectors")
    parser.add_argument("--english-id-column", help="Exact header name for ENG30 selectors")
    parser.add_argument("--synset-name-column", help="Exact header name for synset names")
    parser.add_argument("--lemma-column", help="Exact header name for lemma lookup")
    parser.add_argument("--pos-column", help="Exact header name for POS lookup")
    parser.add_argument("--sense-index-column", help="Exact header name for sense index lookup")
    parser.add_argument("--pipeline-column", help="Exact header name for row-level pipeline override")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = SheetBatchConfig(
        source=args.source,
        output_dir=Path(args.output_dir),
        workflow=WorkflowConfig(),
        default_pipeline=args.pipeline,
        gid=args.gid,
        columns=SheetColumnOverrides(
            ili=args.ili_column,
            english_id=args.english_id_column,
            synset_name=args.synset_name_column,
            lemma=args.lemma_column,
            pos=args.pos_column,
            sense_index=args.sense_index_column,
            pipeline=args.pipeline_column,
        ),
        download_timeout=args.download_timeout,
    )

    try:
        summary = prepare_native_sheet_translation_batch(config)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
