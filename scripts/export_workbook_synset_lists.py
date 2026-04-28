#!/usr/bin/env python3
"""Extract English synset IDs from a workbook/CSV and export grouped lists."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Dict, List

from wordnet_autotranslate.workflows.sheet_translation_workflow import (
    _read_csv_rows,
    _read_xlsx_candidate_rows,
    detect_column_mapping,
    group_candidate_records_by_sheet_header,
    render_grouped_candidate_text,
    sort_candidate_records_by_sheet_column,
    validate_sheet_row,
)


def _load_candidates(path: Path) -> List[Dict[str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        _, rows = _read_xlsx_candidate_rows(path)
        return rows
    _, rows = _read_csv_rows(path)
    return rows


def _default_output_dir(source: Path) -> Path:
    return Path("data") / "workbook_imports" / source.stem.replace(" ", "_")


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract English synset candidates from a local workbook/CSV and "
            "export flat and grouped lists."
        )
    )
    parser.add_argument("source", help="Local .xlsx or .csv file")
    parser.add_argument(
        "--output-dir",
        help="Directory for copied source and generated exports",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        parser.error(f"Source file not found: {source}")

    output_dir = Path(args.output_dir) if args.output_dir else _default_output_dir(source)
    output_dir.mkdir(parents=True, exist_ok=True)

    copied_source = output_dir / source.name
    if source.resolve() != copied_source.resolve():
        shutil.copy2(source, copied_source)

    rows = _load_candidates(copied_source)
    if not rows:
        raise ValueError(f"No candidate rows were extracted from {copied_source}")

    mapping = detect_column_mapping(list(rows[0].keys()))
    validated: List[Dict[str, str]] = []
    for index, row in enumerate(rows, start=2):
        result = validate_sheet_row(index, row, mapping, default_pipeline="all")
        validated.append(
            {
                "row_number": str(result["row_number"]),
                "status": _clean_text(result["status"]),
                "selector_kind": _clean_text(result.get("selector_kind")),
                "selector_value": _clean_text(result.get("selector_value")),
                "resolved_english_id": _clean_text(
                    result.get("synset_payload", {}).get("english_id")
                ),
                "message": _clean_text(result.get("message")),
                "note": _clean_text(result.get("note")),
                "sheet_name": _clean_text(row.get("sheet_name")),
                "source_row": _clean_text(row.get("source_row")),
                "source_column": _clean_text(row.get("source_column")),
                "source_cell": _clean_text(row.get("source_cell")),
                "source_header": _clean_text(row.get("source_header")),
                "source_value": _clean_text(row.get("source_value")),
            }
        )

    sorted_rows = sort_candidate_records_by_sheet_column(validated)
    grouped_rows = group_candidate_records_by_sheet_header(
        [row for row in sorted_rows if row["status"] == "valid"]
    )

    flat_csv_path = output_dir / "english_synset_candidates_by_sheet_header.csv"
    with flat_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(sorted_rows[0].keys()))
        writer.writeheader()
        writer.writerows(sorted_rows)

    grouped_json_path = output_dir / "pipeline_ready_by_sheet_and_header.json"
    grouped_json_path.write_text(
        json.dumps(grouped_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    grouped_txt_path = output_dir / "pipeline_ready_by_sheet_and_header.txt"
    grouped_txt_path.write_text(
        render_grouped_candidate_text(grouped_rows),
        encoding="utf-8",
    )

    summary = {
        "source": str(copied_source),
        "total_candidates": len(validated),
        "valid_candidates": sum(1 for row in validated if row["status"] == "valid"),
        "invalid_candidates": sum(1 for row in validated if row["status"] != "valid"),
        "grouped_json": str(grouped_json_path),
        "grouped_txt": str(grouped_txt_path),
        "flat_csv": str(flat_csv_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
