"""Batch workflow for translating synsets listed in a Google Sheet, CSV, or XLSX file."""

from __future__ import annotations

import csv
import json
import logging
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from ..utils.language_utils import LanguageUtils
from .synset_translation_workflow import (
    WorkflowConfig,
    parse_eng30_id,
    parse_ili_id,
    resolve_ili_to_payload,
    resolve_wordnet_synset,
    run_translation_workflow,
)

_GOOGLE_SHEET_PATH_RE = re.compile(r"^/spreadsheets/d/([a-zA-Z0-9-_]+)")
_SYNSET_NAME_RE = re.compile(r"^[^.]+\.[A-Za-z]\.\d{2}$")
_ID_LIKE_TOKEN_RE = re.compile(r"\bENG[0-9A-Za-z-]+\b", re.IGNORECASE)
_SUPPORTED_PIPELINES = {"baseline", "langgraph", "conceptual", "all", "dspy"}
_XLSX_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

_COLUMN_ALIASES: Dict[str, Tuple[str, ...]] = {
    "ili": (
        "ili",
        "ili_id",
        "ili id",
        "interlingual_index",
        "interlingual index",
    ),
    "english_id": (
        "english_id",
        "english id",
        "eng30",
        "eng30_id",
        "eng30 id",
        "synset_id",
        "synset id",
        "english_synset_id",
        "english synset id",
        "pwn_id",
        "pwn id",
        "wn_id",
        "wn id",
    ),
    "synset_name": (
        "synset_name",
        "synset name",
        "wordnet_synset_name",
        "wordnet synset name",
        "pwn_synset_name",
        "pwn synset name",
        "wordnet_name",
        "wordnet name",
    ),
    "lemma": (
        "lemma",
        "english_lemma",
        "english lemma",
        "source_lemma",
        "source lemma",
        "en_lemma",
        "en lemma",
    ),
    "pos": (
        "pos",
        "part_of_speech",
        "part of speech",
        "english_pos",
        "english pos",
        "source_pos",
        "source pos",
    ),
    "sense_index": (
        "sense_index",
        "sense index",
        "sense",
        "sense_number",
        "sense number",
        "sense_no",
        "sense no",
    ),
    "pipeline": (
        "pipeline",
        "workflow",
        "selected_pipeline",
        "selected pipeline",
        "run_pipeline",
        "run pipeline",
    ),
}


@dataclass(frozen=True)
class SheetColumnOverrides:
    """Explicit source-column names for row selectors and pipeline selection."""

    ili: Optional[str] = None
    english_id: Optional[str] = None
    synset_name: Optional[str] = None
    lemma: Optional[str] = None
    pos: Optional[str] = None
    sense_index: Optional[str] = None
    pipeline: Optional[str] = None


@dataclass(frozen=True)
class SheetColumnMapping:
    """Resolved input-column mapping against a concrete header row."""

    ili: Optional[str] = None
    english_id: Optional[str] = None
    synset_name: Optional[str] = None
    lemma: Optional[str] = None
    pos: Optional[str] = None
    sense_index: Optional[str] = None
    pipeline: Optional[str] = None


@dataclass(frozen=True)
class SheetBatchConfig:
    """Configuration for a sheet-driven translation batch."""

    source: str
    output_dir: Path
    workflow: WorkflowConfig = WorkflowConfig()
    default_pipeline: str = "all"
    gid: Optional[str] = None
    columns: SheetColumnOverrides = SheetColumnOverrides()
    download_timeout: int = 30


@dataclass(frozen=True)
class SheetInputSnapshot:
    """Details about the downloaded or copied batch input."""

    source: str
    source_kind: str
    downloaded_from: Optional[str]
    local_path: Path
    columns: List[str]
    row_count: int


def _safe_int(value: Any, default: int = 10**9) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def normalize_header(value: str) -> str:
    """Normalize a column header into a comparison-safe token."""
    token = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    return token.strip("_")


def safe_path_component(value: Optional[str]) -> str:
    """Sanitize arbitrary text for filesystem path usage."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip())
    cleaned = cleaned.strip("._")
    return cleaned or "unknown"


def build_google_sheet_csv_export_url(sheet_url: str, gid: Optional[str] = None) -> str:
    """Convert a shared Google Sheet URL into a CSV export URL."""
    parsed = urlparse(sheet_url)
    if parsed.scheme not in {"http", "https"} or "docs.google.com" not in parsed.netloc:
        raise ValueError(f"Not a supported Google Sheets URL: {sheet_url!r}")

    match = _GOOGLE_SHEET_PATH_RE.match(parsed.path)
    if not match:
        raise ValueError(f"Could not extract spreadsheet ID from URL: {sheet_url!r}")

    spreadsheet_id = match.group(1)
    query = parse_qs(parsed.query)
    selected_gid = gid or (query.get("gid", [None])[0])

    export_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv"
    if selected_gid:
        export_url += f"&gid={selected_gid}"
    return export_url


def detect_column_mapping(
    headers: Sequence[str],
    overrides: SheetColumnOverrides = SheetColumnOverrides(),
) -> SheetColumnMapping:
    """Resolve selector-related columns from a header row."""
    normalized_to_original: Dict[str, str] = {}
    for header in headers:
        normalized = normalize_header(header)
        if normalized and normalized not in normalized_to_original:
            normalized_to_original[normalized] = header

    def _resolve(field_name: str) -> Optional[str]:
        explicit = getattr(overrides, field_name)
        if explicit:
            explicit_key = normalize_header(explicit)
            resolved = normalized_to_original.get(explicit_key)
            if resolved is None:
                raise ValueError(
                    f"Configured column {explicit!r} for {field_name!r} was not found in sheet headers."
                )
            return resolved

        for alias in _COLUMN_ALIASES[field_name]:
            resolved = normalized_to_original.get(normalize_header(alias))
            if resolved is not None:
                return resolved
        return None

    return SheetColumnMapping(
        ili=_resolve("ili"),
        english_id=_resolve("english_id"),
        synset_name=_resolve("synset_name"),
        lemma=_resolve("lemma"),
        pos=_resolve("pos"),
        sense_index=_resolve("sense_index"),
        pipeline=_resolve("pipeline"),
    )


def ensure_wordnet_available() -> None:
    """Fail fast when NLTK Princeton WordNet is missing locally."""
    from nltk.corpus import wordnet as wn

    try:
        wn.ensure_loaded()
    except LookupError as exc:
        raise RuntimeError(
            "NLTK Princeton WordNet is not available locally. "
            "Install it with nltk.download('wordnet') before running sheet batches."
        ) from exc


def _read_csv_rows(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.get_dialect("excel")

        reader = csv.DictReader(handle, dialect=dialect)
        headers = [header or "" for header in (reader.fieldnames or [])]
        rows: List[Dict[str, str]] = []
        for raw_row in reader:
            row = {
                str(key or ""): (value if value is not None else "")
                for key, value in raw_row.items()
            }
            if any(str(value).strip() for value in row.values()):
                rows.append(row)
    return headers, rows


def _xlsx_column_number(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", str(cell_ref or "").upper())
    if not match:
        return 0
    column_label = match.group(1)
    value = 0
    for ch in column_label:
        value = value * 26 + (ord(ch) - ord("A") + 1)
    return value


def _extract_id_candidates(value: str) -> List[str]:
    text = str(value or "").strip()
    if not text:
        return []

    matches = _ID_LIKE_TOKEN_RE.findall(text)
    if matches:
        deduped: List[str] = []
        seen = set()
        for match in matches:
            normalized = match.strip()
            if normalized not in seen:
                seen.add(normalized)
                deduped.append(normalized)
        return deduped

    if text.upper().startswith("ENG"):
        return [text]
    return []


def _xlsx_cell_value(cell: ET.Element, shared_strings: Sequence[str]) -> str:
    cell_type = cell.attrib.get("t")
    value_node = cell.find("main:v", _XLSX_NS)
    if cell_type == "inlineStr":
        inline_node = cell.find("main:is", _XLSX_NS)
        if inline_node is None:
            return ""
        return "".join((node.text or "") for node in inline_node.iterfind(".//main:t", _XLSX_NS))

    if value_node is None:
        return ""

    raw_value = value_node.text or ""
    if cell_type == "s":
        return shared_strings[int(raw_value)]
    return raw_value


def _read_xlsx_candidate_rows(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    headers = [
        "english_id",
        "sheet_name",
        "source_row",
        "source_column",
        "source_cell",
        "source_header",
        "source_value",
    ]
    rows: List[Dict[str, str]] = []

    with ZipFile(path) as workbook_zip:
        shared_strings: List[str] = []
        if "xl/sharedStrings.xml" in workbook_zip.namelist():
            shared_root = ET.fromstring(workbook_zip.read("xl/sharedStrings.xml"))
            for string_item in shared_root.findall("main:si", _XLSX_NS):
                text_parts = [
                    node.text or ""
                    for node in string_item.iterfind(".//main:t", _XLSX_NS)
                ]
                shared_strings.append("".join(text_parts))

        workbook_root = ET.fromstring(workbook_zip.read("xl/workbook.xml"))
        rels_root = ET.fromstring(workbook_zip.read("xl/_rels/workbook.xml.rels"))
        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels_root.findall("pkgrel:Relationship", _XLSX_NS)
        }

        sheets_root = workbook_root.find("main:sheets", _XLSX_NS)
        if sheets_root is None:
            return headers, rows

        for sheet in sheets_root:
            sheet_name = sheet.attrib.get("name", "")
            rel_id = sheet.attrib[
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            ]
            target = rel_map[rel_id].lstrip("/")
            sheet_root = ET.fromstring(workbook_zip.read(f"xl/{target}"))
            sheet_data = sheet_root.find("main:sheetData", _XLSX_NS)
            if sheet_data is None:
                continue

            header_by_column: Dict[int, str] = {}
            first_nonempty_row_seen = False

            for row_node in sheet_data.findall("main:row", _XLSX_NS):
                row_index = str(row_node.attrib.get("r", ""))
                parsed_cells: List[Tuple[int, str, str]] = []
                for cell in row_node.findall("main:c", _XLSX_NS):
                    cell_ref = cell.attrib.get("r", "")
                    value = _xlsx_cell_value(cell, shared_strings).strip()
                    if not value:
                        continue
                    parsed_cells.append((_xlsx_column_number(cell_ref), cell_ref, value))

                if not parsed_cells:
                    continue

                if not first_nonempty_row_seen:
                    header_by_column = {
                        column_number: value
                        for column_number, _, value in parsed_cells
                    }
                    first_nonempty_row_seen = True

                for column_number, cell_ref, value in parsed_cells:
                    for candidate in _extract_id_candidates(value):
                        rows.append(
                            {
                                "english_id": candidate,
                                "sheet_name": sheet_name,
                                "source_row": row_index,
                                "source_column": str(column_number),
                                "source_cell": cell_ref,
                                "source_header": header_by_column.get(column_number, ""),
                                "source_value": value,
                            }
                        )

    return headers, rows


def _write_csv_rows(path: Path, headers: Sequence[str], rows: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(headers))
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _download_text(url: str, timeout: int) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8-sig")


def _materialize_sheet_input(
    source: str,
    *,
    output_dir: Path,
    gid: Optional[str],
    timeout: int,
) -> SheetInputSnapshot:
    input_dir = output_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    local_candidate = Path(source)
    downloaded_from: Optional[str] = None
    source_kind: str

    if local_candidate.exists():
        destination = input_dir / local_candidate.name
        shutil.copy2(local_candidate, destination)
        suffix = destination.suffix.lower()
        if suffix == ".xlsx":
            source_kind = "local_xlsx"
            extracted_headers, extracted_rows = _read_xlsx_candidate_rows(destination)
            prepared_csv = input_dir / "sheet_snapshot.csv"
            _write_csv_rows(prepared_csv, extracted_headers, extracted_rows)
            destination = prepared_csv
        else:
            source_kind = "local_file"
    else:
        parsed = urlparse(source)
        if parsed.scheme not in {"http", "https"}:
            raise FileNotFoundError(f"Input source does not exist: {source!r}")

        if "docs.google.com" in parsed.netloc and "/spreadsheets/" in parsed.path:
            source_kind = "google_sheet_url"
            downloaded_from = build_google_sheet_csv_export_url(source, gid=gid)
        else:
            source_kind = "remote_csv_url"
            downloaded_from = source

        destination = input_dir / "sheet_snapshot.csv"
        try:
            content = _download_text(downloaded_from, timeout)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to download batch input from {downloaded_from!r}. "
                "If the Google Sheet is not publicly exportable from this environment, "
                "download it as CSV locally and rerun the script with that file path."
            ) from exc
        destination.write_text(content, encoding="utf-8")

    headers, rows = _read_csv_rows(destination)
    if not headers:
        raise ValueError(f"Input file {destination} does not contain a header row.")

    return SheetInputSnapshot(
        source=source,
        source_kind=source_kind,
        downloaded_from=downloaded_from,
        local_path=destination,
        columns=headers,
        row_count=len(rows),
    )


def _setup_logger(log_path: Path) -> logging.Logger:
    logger = logging.getLogger(f"sheet_translation_batch.{safe_path_component(str(log_path))}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


def _create_run_dir(base_output_dir: Path, source: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"} and "docs.google.com" in parsed.netloc:
        label = "google_sheet"
    else:
        label = Path(source).stem or "sheet_batch"
    run_dir = base_output_dir / f"{safe_path_component(label)}_{timestamp}"
    for relative in [
        "input",
        "logs",
        "summary",
        "results/success",
        "results/error",
        "results/invalid_format",
        "results/not_found",
        "work_items/pending",
        "work_items/in_progress",
        "work_items/completed",
        "work_items/failed",
    ]:
        (run_dir / relative).mkdir(parents=True, exist_ok=True)
    return run_dir


def _value_from_row(row: Mapping[str, str], column_name: Optional[str]) -> str:
    if not column_name:
        return ""
    return str(row.get(column_name, "") or "").strip()


def _parse_sense_index(value: str) -> int:
    if not value:
        return 1
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid sense_index={value!r}; expected an integer.") from exc
    if parsed <= 0:
        raise ValueError(f"Invalid sense_index={value!r}; expected a positive integer.")
    return parsed


def _resolve_pipeline(row: Mapping[str, str], mapping: SheetColumnMapping, default_pipeline: str) -> str:
    candidate = _value_from_row(row, mapping.pipeline) or default_pipeline
    pipeline = candidate.strip().lower()
    if pipeline not in _SUPPORTED_PIPELINES:
        raise ValueError(
            f"Unsupported pipeline {candidate!r}. Use one of: "
            "baseline, langgraph, conceptual, all, dspy."
        )
    return pipeline


def _filled_selector_columns(row: Mapping[str, str], mapping: SheetColumnMapping) -> List[str]:
    selectors: List[str] = []
    if _value_from_row(row, mapping.english_id):
        selectors.append("english_id")
    if _value_from_row(row, mapping.ili):
        selectors.append("ili")
    if _value_from_row(row, mapping.synset_name):
        selectors.append("synset_name")
    if _value_from_row(row, mapping.lemma) or _value_from_row(row, mapping.pos):
        selectors.append("lemma_pos")
    return selectors


def validate_sheet_row(
    row_number: int,
    row: Mapping[str, str],
    mapping: SheetColumnMapping,
    *,
    default_pipeline: str = "all",
    include_relations: bool = False,
) -> Dict[str, Any]:
    """Validate one sheet row and resolve it into a canonical synset payload."""
    try:
        pipeline = _resolve_pipeline(row, mapping, default_pipeline)
    except ValueError as exc:
        return {
            "row_number": row_number,
            "status": "error",
            "selector_kind": "unknown",
            "selector_value": "",
            "pipeline": "",
            "message": str(exc),
            "note": None,
        }
    filled_selectors = _filled_selector_columns(row, mapping)
    note: Optional[str] = None
    if len(filled_selectors) > 1:
        note = (
            "Multiple selector columns were filled. "
            "The workflow used precedence english_id > ili > synset_name > lemma+pos."
        )

    ili = _value_from_row(row, mapping.ili)
    english_id = _value_from_row(row, mapping.english_id)
    synset_name = _value_from_row(row, mapping.synset_name)
    lemma = _value_from_row(row, mapping.lemma)
    pos = _value_from_row(row, mapping.pos)
    sense_index_raw = _value_from_row(row, mapping.sense_index)

    if english_id:
        selector_kind = "english_id"
        selector_value = english_id
        try:
            parse_eng30_id(english_id)
            synset_payload = resolve_wordnet_synset(
                english_id=english_id,
                include_relations=include_relations,
            )
        except ValueError as exc:
            return {
                "row_number": row_number,
                "status": "invalid_format",
                "selector_kind": selector_kind,
                "selector_value": selector_value,
                "pipeline": pipeline,
                "message": str(exc),
                "note": note,
            }
        except Exception as exc:
            return {
                "row_number": row_number,
                "status": "not_found",
                "selector_kind": selector_kind,
                "selector_value": selector_value,
                "pipeline": pipeline,
                "message": f"ENG30 selector was well-formed but not found in NLTK PWN: {exc}",
                "note": note,
            }
        return {
            "row_number": row_number,
            "status": "valid",
            "selector_kind": selector_kind,
            "selector_value": selector_value,
            "pipeline": pipeline,
            "synset_payload": synset_payload,
            "note": note,
        }

    if ili:
        selector_kind = "ili"
        selector_value = ili
        try:
            parse_ili_id(ili)
            synset_payload = resolve_wordnet_synset(
                ili=ili,
                include_relations=include_relations,
            )
        except ValueError as exc:
            return {
                "row_number": row_number,
                "status": "invalid_format",
                "selector_kind": selector_kind,
                "selector_value": selector_value,
                "pipeline": pipeline,
                "message": str(exc),
                "note": note,
            }
        except LookupError as exc:
            return {
                "row_number": row_number,
                "status": "not_found",
                "selector_kind": selector_kind,
                "selector_value": selector_value,
                "pipeline": pipeline,
                "message": str(exc),
                "note": note,
            }
        except Exception as exc:
            return {
                "row_number": row_number,
                "status": "error",
                "selector_kind": selector_kind,
                "selector_value": selector_value,
                "pipeline": pipeline,
                "message": str(exc),
                "note": note,
            }
        return {
            "row_number": row_number,
            "status": "valid",
            "selector_kind": selector_kind,
            "selector_value": selector_value,
            "pipeline": pipeline,
            "synset_payload": synset_payload,
            "note": note,
        }

    if synset_name:
        selector_kind = "synset_name"
        selector_value = synset_name
        if not _SYNSET_NAME_RE.match(synset_name):
            return {
                "row_number": row_number,
                "status": "invalid_format",
                "selector_kind": selector_kind,
                "selector_value": selector_value,
                "pipeline": pipeline,
                "message": (
                    "Synset name must look like lemma.pos.nn, for example entity.n.01."
                ),
                "note": note,
            }
        try:
            synset_payload = resolve_wordnet_synset(
                synset_name=synset_name,
                include_relations=include_relations,
            )
        except Exception as exc:
            return {
                "row_number": row_number,
                "status": "not_found",
                "selector_kind": selector_kind,
                "selector_value": selector_value,
                "pipeline": pipeline,
                "message": f"Synset name was well-formed but not found in NLTK PWN: {exc}",
                "note": note,
            }
        return {
            "row_number": row_number,
            "status": "valid",
            "selector_kind": selector_kind,
            "selector_value": selector_value,
            "pipeline": pipeline,
            "synset_payload": synset_payload,
            "note": note,
        }

    if lemma or pos:
        selector_kind = "lemma_pos"
        selector_value = f"{lemma}|{pos}|{sense_index_raw or '1'}"
        if not lemma or not pos:
            return {
                "row_number": row_number,
                "status": "invalid_format",
                "selector_kind": selector_kind,
                "selector_value": selector_value,
                "pipeline": pipeline,
                "message": "Lemma+POS lookup requires both lemma and pos columns to be filled.",
                "note": note,
            }

        normalized_pos = LanguageUtils.normalize_pos_for_english(pos)
        if normalized_pos not in {"n", "v", "a", "r"}:
            return {
                "row_number": row_number,
                "status": "invalid_format",
                "selector_kind": selector_kind,
                "selector_value": selector_value,
                "pipeline": pipeline,
                "message": f"Unsupported POS {pos!r}; expected one of n, v, a, r, s, b.",
                "note": note,
            }

        try:
            sense_index = _parse_sense_index(sense_index_raw)
            synset_payload = resolve_wordnet_synset(
                lemma=lemma,
                pos=pos,
                sense_index=sense_index,
                include_relations=include_relations,
            )
        except ValueError as exc:
            message = str(exc)
            status = "not_found" if "out of range" in message else "invalid_format"
            return {
                "row_number": row_number,
                "status": status,
                "selector_kind": selector_kind,
                "selector_value": selector_value,
                "pipeline": pipeline,
                "message": message,
                "note": note,
            }
        except LookupError as exc:
            return {
                "row_number": row_number,
                "status": "not_found",
                "selector_kind": selector_kind,
                "selector_value": selector_value,
                "pipeline": pipeline,
                "message": str(exc),
                "note": note,
            }
        except Exception as exc:
            return {
                "row_number": row_number,
                "status": "error",
                "selector_kind": selector_kind,
                "selector_value": selector_value,
                "pipeline": pipeline,
                "message": str(exc),
                "note": note,
            }
        return {
            "row_number": row_number,
            "status": "valid",
            "selector_kind": selector_kind,
            "selector_value": selector_value,
            "pipeline": pipeline,
            "synset_payload": synset_payload,
            "note": note,
        }

    return {
        "row_number": row_number,
        "status": "invalid_format",
        "selector_kind": "missing",
        "selector_value": "",
        "pipeline": pipeline,
        "message": (
            "Row does not contain a usable selector. Fill english_id, ili, synset_name, "
            "or lemma+pos."
        ),
        "note": note,
    }


def _build_result_path(run_dir: Path, status: str, record: Mapping[str, Any]) -> Path:
    selector_kind = safe_path_component(str(record.get("selector_kind")))
    row_name = f"row_{int(record['row_number']):05d}.json"

    if status == "success":
        synset_payload = record.get("synset_payload", {})
        pipeline = safe_path_component(str(record.get("pipeline")))
        pos = safe_path_component(str(synset_payload.get("pos", "unknown")))
        selector_id = safe_path_component(
            str(synset_payload.get("english_id") or record.get("selector_value"))
        )
        return (
            run_dir
            / "results"
            / "success"
            / pipeline
            / selector_kind
            / pos
            / selector_id
            / row_name
        )

    return run_dir / "results" / status / selector_kind / row_name


def _write_summary_files(run_dir: Path, records: Sequence[Mapping[str, Any]], summary: Mapping[str, Any]) -> None:
    summary_dir = run_dir / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    _write_json(summary_dir / "run_summary.json", summary)

    jsonl_path = summary_dir / "rows.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    csv_fields = [
        "row_number",
        "status",
        "selector_kind",
        "selector_value",
        "resolved_english_id",
        "pipeline",
        "message",
        "note",
        "output_path",
    ]
    with (summary_dir / "rows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for record in records:
            writer.writerow({field: record.get(field, "") for field in csv_fields})


def sort_candidate_records_by_sheet_column(
    records: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Sort candidate records by sheet order, then column, then row."""
    sheet_order: Dict[str, int] = {}
    for record in records:
        sheet_name = str(record.get("sheet_name", ""))
        if sheet_name not in sheet_order:
            sheet_order[sheet_name] = len(sheet_order)

    sorted_records = sorted(
        (dict(record) for record in records),
        key=lambda record: (
            sheet_order.get(str(record.get("sheet_name", "")), 10**9),
            _safe_int(record.get("source_column")),
            _safe_int(record.get("source_row")),
            _safe_int(record.get("row_number")),
        ),
    )
    return sorted_records


def group_candidate_records_by_sheet_header(
    records: Sequence[Mapping[str, Any]],
    *,
    id_field: str = "resolved_english_id",
) -> List[Dict[str, Any]]:
    """Group candidate records by sheet and source header in workbook order."""
    grouped_sheets: List[Dict[str, Any]] = []
    sheet_lookup: Dict[str, Dict[str, Any]] = {}

    for record in sort_candidate_records_by_sheet_column(records):
        sheet_name = str(record.get("sheet_name") or "unknown_sheet")
        header_name = str(record.get("source_header") or "").strip()
        if not header_name:
            header_name = f"Column {record.get('source_column', '?')}"

        sheet_group = sheet_lookup.get(sheet_name)
        if sheet_group is None:
            sheet_group = {
                "sheet_name": sheet_name,
                "groups": [],
                "_group_lookup": {},
            }
            sheet_lookup[sheet_name] = sheet_group
            grouped_sheets.append(sheet_group)

        header_key = f"{record.get('source_column', '')}::{header_name}"
        header_group = sheet_group["_group_lookup"].get(header_key)
        if header_group is None:
            header_group = {
                "header": header_name,
                "source_column": str(record.get("source_column", "")),
                "records": [],
                "english_ids": [],
            }
            sheet_group["_group_lookup"][header_key] = header_group
            sheet_group["groups"].append(header_group)

        header_group["records"].append(dict(record))

        english_id = (
            str(record.get(id_field) or "").strip()
            or str(record.get("selector_value") or "").strip()
            or str(record.get("english_id") or "").strip()
        )
        if english_id:
            header_group["english_ids"].append(english_id)

    for sheet_group in grouped_sheets:
        sheet_group.pop("_group_lookup", None)
        for header_group in sheet_group["groups"]:
            header_group["row_count"] = len(header_group["records"])
            header_group["unique_english_ids"] = list(
                dict.fromkeys(header_group["english_ids"])
            )

    return grouped_sheets


def render_grouped_candidate_text(groups: Sequence[Mapping[str, Any]]) -> str:
    """Render grouped candidate IDs as a simple text report."""
    lines: List[str] = []
    for sheet_group in groups:
        lines.append(f"# {sheet_group['sheet_name']}")
        for header_group in sheet_group.get("groups", []):
            lines.append("")
            lines.append(f"## {header_group['header']}")
            for english_id in header_group.get("english_ids", []):
                lines.append(str(english_id))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run_sheet_translation_batch(config: SheetBatchConfig) -> Dict[str, Any]:
    """Run a Google Sheet or CSV driven translation batch."""
    default_pipeline = config.default_pipeline.strip().lower()
    if default_pipeline not in _SUPPORTED_PIPELINES:
        raise ValueError(
            f"Unsupported default pipeline {config.default_pipeline!r}. "
            "Use one of: baseline, langgraph, conceptual, all, dspy."
        )

    ensure_wordnet_available()

    run_dir = _create_run_dir(config.output_dir, config.source)
    logger = _setup_logger(run_dir / "logs" / "batch.log")
    logger.info("Starting sheet batch from source=%s", config.source)

    snapshot = _materialize_sheet_input(
        config.source,
        output_dir=run_dir,
        gid=config.gid,
        timeout=config.download_timeout,
    )
    logger.info(
        "Prepared input snapshot at %s with %s data rows",
        snapshot.local_path,
        snapshot.row_count,
    )

    headers, rows = _read_csv_rows(snapshot.local_path)
    mapping = detect_column_mapping(headers, config.columns)
    if not (mapping.english_id or mapping.synset_name or (mapping.lemma and mapping.pos)):
        raise ValueError(
            "Could not find usable selector columns. Provide an english_id column, "
            "a synset_name column, or both lemma and pos columns."
        )

    logger.info("Resolved column mapping: %s", asdict(mapping))

    summary_records: List[Dict[str, Any]] = []
    counts = {"success": 0, "invalid_format": 0, "not_found": 0, "error": 0}

    for offset, row in enumerate(rows, start=2):
        try:
            validation = validate_sheet_row(
                offset,
                row,
                mapping,
                default_pipeline=default_pipeline,
            )
        except Exception as exc:
            validation = {
                "row_number": offset,
                "status": "error",
                "selector_kind": "unknown",
                "selector_value": "",
                "pipeline": "",
                "message": str(exc),
                "note": None,
            }
        status = str(validation["status"])

        if status == "valid":
            payload = validation["synset_payload"]
            try:
                translation = run_translation_workflow(
                    payload,
                    pipeline=str(validation["pipeline"]),
                    config=config.workflow,
                )
                validation["translation_result"] = translation
                status = "success"
                counts["success"] += 1
                logger.info(
                    "Row %s translated successfully via %s for %s",
                    offset,
                    validation["pipeline"],
                    payload.get("english_id"),
                )
            except Exception as exc:
                validation["message"] = str(exc)
                status = "error"
                counts["error"] += 1
                logger.exception("Row %s failed during pipeline execution", offset)
        else:
            counts[status] += 1
            logger.warning(
                "Row %s classified as %s: %s",
                offset,
                status,
                validation.get("message", ""),
            )

        validation["status"] = status
        result_path = _build_result_path(run_dir, status, validation)
        record_payload = {
            "row_number": validation["row_number"],
            "status": status,
            "selector_kind": validation.get("selector_kind"),
            "selector_value": validation.get("selector_value"),
            "pipeline": validation.get("pipeline"),
            "note": validation.get("note"),
            "message": validation.get("message"),
            "source_row": dict(row),
        }
        if validation.get("synset_payload"):
            record_payload["synset_payload"] = validation["synset_payload"]
        if validation.get("translation_result"):
            record_payload["translation_result"] = validation["translation_result"]

        _write_json(result_path, record_payload)

        summary_records.append(
            {
                "row_number": validation["row_number"],
                "status": status,
                "selector_kind": validation.get("selector_kind"),
                "selector_value": validation.get("selector_value"),
                "resolved_english_id": (
                    validation.get("synset_payload", {}).get("english_id")
                    if validation.get("synset_payload")
                    else ""
                ),
                "pipeline": validation.get("pipeline"),
                "message": validation.get("message", ""),
                "note": validation.get("note", ""),
                "output_path": str(result_path),
            }
        )

    summary = {
        "source": snapshot.source,
        "source_kind": snapshot.source_kind,
        "downloaded_from": snapshot.downloaded_from,
        "input_snapshot": str(snapshot.local_path),
        "run_dir": str(run_dir),
        "default_pipeline": default_pipeline,
        "workflow_config": {
            "source_lang": config.workflow.source_lang,
            "target_lang": config.workflow.target_lang,
            "model": config.workflow.model,
            "timeout": config.workflow.timeout,
            "base_url": config.workflow.base_url,
            "temperature": config.workflow.temperature,
            "strict": config.workflow.strict,
        },
        "column_mapping": asdict(mapping),
        "row_count": len(rows),
        "counts": counts,
    }
    _write_summary_files(run_dir, summary_records, summary)
    logger.info("Finished sheet batch. Summary counts: %s", counts)
    return summary


def _build_native_work_item_path(run_dir: Path, record: Mapping[str, Any]) -> Path:
    selector_kind = safe_path_component(str(record.get("selector_kind")))
    row_name = f"row_{int(record['row_number']):05d}.json"
    synset_payload = record.get("synset_payload", {})
    pipeline = safe_path_component(str(record.get("pipeline", "")))
    pos = safe_path_component(str(synset_payload.get("pos", "unknown")))
    selector_id = safe_path_component(
        str(
            synset_payload.get("english_id")
            or synset_payload.get("ili_id")
            or record.get("selector_value")
        )
    )
    return (
        run_dir
        / "work_items"
        / "pending"
        / pipeline
        / selector_kind
        / pos
        / selector_id
        / row_name
    )


def prepare_native_sheet_translation_batch(config: SheetBatchConfig) -> Dict[str, Any]:
    """Prepare a batch run for native-agent translation without invoking Ollama/LangChain."""
    default_pipeline = config.default_pipeline.strip().lower()
    if default_pipeline not in _SUPPORTED_PIPELINES:
        raise ValueError(
            f"Unsupported default pipeline {config.default_pipeline!r}. "
            "Use one of: baseline, langgraph, conceptual, all, dspy."
        )

    ensure_wordnet_available()

    run_dir = _create_run_dir(config.output_dir, config.source)
    logger = _setup_logger(run_dir / "logs" / "batch.log")
    logger.info("Starting native-agent sheet batch from source=%s", config.source)

    snapshot = _materialize_sheet_input(
        config.source,
        output_dir=run_dir,
        gid=config.gid,
        timeout=config.download_timeout,
    )
    logger.info(
        "Prepared input snapshot at %s with %s data rows",
        snapshot.local_path,
        snapshot.row_count,
    )

    headers, rows = _read_csv_rows(snapshot.local_path)
    mapping = detect_column_mapping(headers, config.columns)
    if not (
        mapping.english_id
        or mapping.ili
        or mapping.synset_name
        or (mapping.lemma and mapping.pos)
    ):
        raise ValueError(
            "Could not find usable selector columns. Provide an english_id column, "
            "an ili column, a synset_name column, or both lemma and pos columns."
        )

    logger.info("Resolved column mapping for native batch: %s", asdict(mapping))

    summary_records: List[Dict[str, Any]] = []
    counts = {"pending": 0, "invalid_format": 0, "not_found": 0, "error": 0}

    for offset, row in enumerate(rows, start=2):
        try:
            validation = validate_sheet_row(
                offset,
                row,
                mapping,
                default_pipeline=default_pipeline,
                include_relations=True,
            )
        except Exception as exc:
            validation = {
                "row_number": offset,
                "status": "error",
                "selector_kind": "unknown",
                "selector_value": "",
                "pipeline": "",
                "message": str(exc),
                "note": None,
            }

        status = str(validation["status"])
        if status == "valid":
            work_item_path = _build_native_work_item_path(run_dir, validation)
            work_item = {
                "row_number": validation["row_number"],
                "status": "pending",
                "selector_kind": validation.get("selector_kind"),
                "selector_value": validation.get("selector_value"),
                "pipeline": validation.get("pipeline"),
                "note": validation.get("note"),
                "synset_payload": validation.get("synset_payload"),
                "source_row": dict(row),
                "translation_mode": "native_agent",
                "retranslate_existing_allowed": True,
            }
            _write_json(work_item_path, work_item)
            counts["pending"] += 1
            logger.info(
                "Queued row %s for native-agent translation via %s",
                offset,
                validation.get("pipeline"),
            )
            output_path = work_item_path
            summary_status = "pending"
            message = "Queued for native-agent translation."
        else:
            counts[status] += 1
            logger.warning(
                "Row %s classified as %s during native batch prep: %s",
                offset,
                status,
                validation.get("message", ""),
            )
            output_path = _build_result_path(run_dir, status, validation)
            _write_json(
                output_path,
                {
                    "row_number": validation["row_number"],
                    "status": status,
                    "selector_kind": validation.get("selector_kind"),
                    "selector_value": validation.get("selector_value"),
                    "pipeline": validation.get("pipeline"),
                    "note": validation.get("note"),
                    "message": validation.get("message"),
                    "source_row": dict(row),
                },
            )
            summary_status = status
            message = validation.get("message", "")

        summary_records.append(
            {
                "row_number": validation["row_number"],
                "status": summary_status,
                "selector_kind": validation.get("selector_kind"),
                "selector_value": validation.get("selector_value"),
                "resolved_english_id": (
                    validation.get("synset_payload", {}).get("english_id")
                    if validation.get("synset_payload")
                    else ""
                ),
                "pipeline": validation.get("pipeline"),
                "message": message,
                "note": validation.get("note", ""),
                "output_path": str(output_path),
            }
        )

    summary = {
        "source": snapshot.source,
        "source_kind": snapshot.source_kind,
        "downloaded_from": snapshot.downloaded_from,
        "input_snapshot": str(snapshot.local_path),
        "run_dir": str(run_dir),
        "default_pipeline": default_pipeline,
        "translation_mode": "native_agent",
        "retranslate_existing_allowed": True,
        "column_mapping": asdict(mapping),
        "row_count": len(rows),
        "counts": counts,
    }
    _write_summary_files(run_dir, summary_records, summary)
    from .native_translation_queue import summarize_native_batch_run

    summarize_native_batch_run(run_dir)
    logger.info("Finished native-agent batch prep. Summary counts: %s", counts)
    return summary
