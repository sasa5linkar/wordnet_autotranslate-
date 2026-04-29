#!/usr/bin/env python3
"""Export clean curator-facing translation review workbooks from batch results.

This exporter intentionally keeps only lookup/source data and the three pipeline
literal/gloss outputs. Full model logs stay in the batch run directory.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

CLEAN_COLUMNS = [
    "source_row",
    "source_cell",
    "english_id",
    "synset_name",
    "english_definition",
    "english_literals",
    "baseline_definition_sr",
    "baseline_literals_sr",
    "langgraph_definition_sr",
    "langgraph_literals_sr",
    "conceptual_definition_sr",
    "conceptual_literals_sr",
]

RUN_METADATA_COLUMNS = [
    "run_provider",
    "run_model",
    "run_reasoning",
]

COLUMN_WIDTHS = {
    "run_provider": 14,
    "run_model": 18,
    "run_reasoning": 14,
    "source_row": 12,
    "source_cell": 12,
    "english_id": 18,
    "synset_name": 24,
    "english_definition": 48,
    "english_literals": 36,
    "baseline_definition_sr": 48,
    "baseline_literals_sr": 36,
    "langgraph_definition_sr": 48,
    "langgraph_literals_sr": 36,
    "conceptual_definition_sr": 48,
    "conceptual_literals_sr": 36,
}


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_list(value: Any) -> List[str]:
    items: List[str]
    if value is None:
        items = []
    elif isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value if str(item).strip()]
    else:
        text = str(value).strip()
        items = [text] if text else []

    deduplicated: List[str] = []
    seen: set[str] = set()
    for item in items:
        key = item.casefold()
        if key not in seen:
            seen.add(key)
            deduplicated.append(item)
    return deduplicated


def _join(value: Any) -> str:
    return "; ".join(_as_list(value))


def _source_payload(record: Mapping[str, Any]) -> Dict[str, Any]:
    payload = record.get("synset_payload") or {}
    if isinstance(payload, dict) and payload:
        return payload
    translation_result = record.get("translation_result") or {}
    if isinstance(translation_result, dict):
        source_synset = translation_result.get("source_synset") or {}
        if isinstance(source_synset, dict):
            return source_synset
    return {}


def _pipeline_payload(record: Mapping[str, Any], name: str) -> Dict[str, Any]:
    translation_result = record.get("translation_result") or {}
    if not isinstance(translation_result, dict):
        return {}
    pipelines = translation_result.get("pipelines") or {}
    if not isinstance(pipelines, dict):
        return {}
    payload = pipelines.get(name) or {}
    return payload if isinstance(payload, dict) else {}


def _run_metadata(record: Mapping[str, Any]) -> Dict[str, Any]:
    translation_result = record.get("translation_result") or {}
    if isinstance(translation_result, dict):
        metadata = translation_result.get("run_metadata") or {}
        if isinstance(metadata, dict):
            return metadata
    metadata = record.get("run_metadata") or {}
    return metadata if isinstance(metadata, dict) else {}


def _clean_row(record: Mapping[str, Any], *, include_run_metadata: bool = False) -> Dict[str, str]:
    source = _source_payload(record)
    source_row = record.get("source_row") or {}
    if not isinstance(source_row, dict):
        source_row = {}

    baseline = _pipeline_payload(record, "baseline")
    langgraph = _pipeline_payload(record, "langgraph")
    conceptual = _pipeline_payload(record, "conceptual")

    row = {
        "source_row": str(source_row.get("source_row") or record.get("row_number") or ""),
        "source_cell": str(source_row.get("source_cell") or ""),
        "english_id": str(
            source.get("english_id")
            or source.get("id")
            or record.get("selector_value")
            or ""
        ),
        "synset_name": str(source.get("name") or ""),
        "english_definition": str(source.get("definition") or source.get("gloss") or ""),
        "english_literals": _join(source.get("lemmas") or source.get("literals")),
        "baseline_definition_sr": str(baseline.get("definition_translation") or ""),
        "baseline_literals_sr": _join(baseline.get("translated_synonyms")),
        "langgraph_definition_sr": str(langgraph.get("definition_translation") or ""),
        "langgraph_literals_sr": _join(langgraph.get("translated_synonyms")),
        "conceptual_definition_sr": str(conceptual.get("final_gloss_sr") or ""),
        "conceptual_literals_sr": _join(conceptual.get("selected_literals_sr")),
    }
    if include_run_metadata:
        metadata = _run_metadata(record)
        row.update(
            {
                "run_provider": str(metadata.get("provider") or ""),
                "run_model": str(metadata.get("model") or ""),
                "run_reasoning": str(metadata.get("reasoning") or ""),
            }
        )
    return row


def _row_sort_key(row: Mapping[str, str]) -> tuple[int, str]:
    try:
        return int(row.get("source_row") or 10**9), row.get("english_id", "")
    except ValueError:
        return 10**9, row.get("english_id", "")


def load_clean_rows(run_dir: Path, *, include_run_metadata: bool = False) -> List[Dict[str, str]]:
    """Load clean rows from a native/repo batch run directory."""
    result_root = run_dir / "results" / "success"
    if not result_root.exists():
        raise FileNotFoundError(f"No success results found under {result_root}")

    rows: List[Dict[str, str]] = []
    for result_path in sorted(result_root.rglob("row_*.json")):
        record = _load_json(result_path)
        rows.append(_clean_row(record, include_run_metadata=include_run_metadata))
    return sorted(rows, key=_row_sort_key)


def write_csv(path: Path, rows: Sequence[Mapping[str, str]], columns: Sequence[str] = CLEAN_COLUMNS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _column_letter(index: int) -> str:
    label = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        label = chr(65 + remainder) + label
    return label


def _xlsx_cell(row_idx: int, col_idx: int, value: Any) -> str:
    ref = f"{_column_letter(col_idx)}{row_idx}"
    text = "" if value is None else str(value)
    escaped = escape(text, {'"': '&quot;'})
    style = ' s="1"' if row_idx == 1 else ""
    return f'<c r="{ref}" t="inlineStr"{style}><is><t xml:space="preserve">{escaped}</t></is></c>'


def write_xlsx(path: Path, rows: Sequence[Mapping[str, str]], columns: Sequence[str] = CLEAN_COLUMNS) -> None:
    """Write a simple one-sheet XLSX using only the Python standard library."""
    path.parent.mkdir(parents=True, exist_ok=True)
    all_rows: List[List[str]] = [list(columns)]
    all_rows.extend([[str(row.get(column, "")) for column in columns] for row in rows])

    sheet_rows = []
    for row_idx, row_values in enumerate(all_rows, start=1):
        cells = "".join(
            _xlsx_cell(row_idx, col_idx, value)
            for col_idx, value in enumerate(row_values, start=1)
        )
        sheet_rows.append(f'<row r="{row_idx}">{cells}</row>')

    last_column = _column_letter(len(columns))
    dimension = f"A1:{last_column}{len(all_rows)}"
    cols = "".join(
        f'<col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>'
        for idx, width in enumerate([COLUMN_WIDTHS.get(column, 18) for column in columns], start=1)
    )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="{dimension}"/>'
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        f'<cols>{cols}</cols>'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        f'<autoFilter ref="A1:{last_column}1"/>'
        '</worksheet>'
    )

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="translations" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '</Relationships>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
        '</styleSheet>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '</Types>'
    )

    with ZipFile(path, "w", ZIP_DEFLATED) as workbook:
        workbook.writestr("[Content_Types].xml", content_types)
        workbook.writestr("_rels/.rels", root_rels)
        workbook.writestr("xl/workbook.xml", workbook_xml)
        workbook.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        workbook.writestr("xl/styles.xml", styles_xml)
        workbook.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export clean all-pipeline translation rows from a batch run."
    )
    parser.add_argument("run_dir", help="Batch run directory containing results/success")
    parser.add_argument("--output", help="Output XLSX path")
    parser.add_argument("--csv-output", help="Optional CSV output path")
    parser.add_argument(
        "--include-run-metadata",
        action="store_true",
        help="Prefix output with provider/model/reasoning columns from each result.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    output = Path(args.output) if args.output else run_dir / "exports" / "clean_translation_review.xlsx"
    csv_output = Path(args.csv_output) if args.csv_output else run_dir / "exports" / "clean_translation_review.csv"

    columns = RUN_METADATA_COLUMNS + CLEAN_COLUMNS if args.include_run_metadata else CLEAN_COLUMNS
    rows = load_clean_rows(run_dir, include_run_metadata=args.include_run_metadata)
    write_xlsx(output, rows, columns=columns)
    write_csv(csv_output, rows, columns=columns)
    print(
        json.dumps(
            {"row_count": len(rows), "column_count": len(columns), "xlsx": str(output), "csv": str(csv_output)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
