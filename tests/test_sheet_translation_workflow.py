import shutil
import tempfile
from textwrap import dedent
from pathlib import Path
from zipfile import ZipFile

from wordnet_autotranslate.workflows import sheet_translation_workflow as sheet_mod
from wordnet_autotranslate.workflows.sheet_translation_workflow import (
    SheetBatchConfig,
    SheetColumnOverrides,
    build_google_sheet_csv_export_url,
    detect_column_mapping,
    group_candidate_records_by_sheet_header,
    prepare_native_sheet_translation_batch,
    render_grouped_candidate_text,
    sort_candidate_records_by_sheet_column,
    validate_sheet_row,
    run_sheet_translation_batch,
)
from wordnet_autotranslate.workflows.synset_translation_workflow import WorkflowConfig


def _write_test_xlsx(path: Path) -> None:
    workbook_xml = dedent(
        """\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
                  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
          <sheets>
            <sheet name="20.4.2026" sheetId="1" r:id="rId1"/>
            <sheet name="emo-dopuna" sheetId="2" r:id="rId2"/>
          </sheets>
        </workbook>
        """
    )
    rels_xml = dedent(
        """\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rId1"
                        Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
                        Target="worksheets/sheet1.xml"/>
          <Relationship Id="rId2"
                        Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
                        Target="worksheets/sheet2.xml"/>
        </Relationships>
        """
    )
    shared_strings_xml = dedent(
        """\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="3" uniqueCount="3">
          <si><t>Category A</t></si>
          <si><t>Category B</t></si>
          <si><t>ID</t></si>
        </sst>
        """
    )
    sheet1_xml = dedent(
        """\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
          <sheetData>
            <row r="1">
              <c r="A1" t="s"><v>0</v></c>
              <c r="B1" t="s"><v>1</v></c>
            </row>
            <row r="2">
              <c r="A2" t="inlineStr"><is><t>ENG30-00001740-n</t></is></c>
              <c r="B2" t="inlineStr"><is><t>ENG20-13058435-n</t></is></c>
            </row>
          </sheetData>
        </worksheet>
        """
    )
    sheet2_xml = dedent(
        """\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
          <sheetData>
            <row r="1">
              <c r="A1" t="s"><v>2</v></c>
            </row>
            <row r="2">
              <c r="A2" t="inlineStr"><is><t>ENG30-00001930-n</t></is></c>
              <c r="B2" t="inlineStr"><is><t>This note should be ignored.</t></is></c>
            </row>
          </sheetData>
        </worksheet>
        """
    )

    with ZipFile(path, "w") as workbook_zip:
        workbook_zip.writestr("xl/workbook.xml", workbook_xml)
        workbook_zip.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        workbook_zip.writestr("xl/sharedStrings.xml", shared_strings_xml)
        workbook_zip.writestr("xl/worksheets/sheet1.xml", sheet1_xml)
        workbook_zip.writestr("xl/worksheets/sheet2.xml", sheet2_xml)


def test_build_google_sheet_csv_export_url_uses_gid_from_url():
    url = (
        "https://docs.google.com/spreadsheets/d/abc123DEF456/edit?"
        "gid=987654321&usp=sharing"
    )

    result = build_google_sheet_csv_export_url(url)

    assert result == (
        "https://docs.google.com/spreadsheets/d/abc123DEF456/export?"
        "format=csv&gid=987654321"
    )


def test_build_google_sheet_csv_export_url_prefers_explicit_gid():
    url = "https://docs.google.com/spreadsheets/d/abc123DEF456/edit?gid=111"

    result = build_google_sheet_csv_export_url(url, gid="222")

    assert result.endswith("format=csv&gid=222")


def test_detect_column_mapping_auto_detects_common_aliases():
    headers = ["ILI ID", "ENG30 ID", "WordNet Synset Name", "English Lemma", "Part of Speech", "Workflow"]

    mapping = detect_column_mapping(headers)

    assert mapping.ili == "ILI ID"
    assert mapping.english_id == "ENG30 ID"
    assert mapping.synset_name == "WordNet Synset Name"
    assert mapping.lemma == "English Lemma"
    assert mapping.pos == "Part of Speech"
    assert mapping.pipeline == "Workflow"


def test_detect_column_mapping_respects_explicit_override():
    headers = ["Selector", "POS", "Pipeline"]

    mapping = detect_column_mapping(
        headers,
        SheetColumnOverrides(english_id="Selector", pos="POS", pipeline="Pipeline"),
    )

    assert mapping.english_id == "Selector"
    assert mapping.pos == "POS"
    assert mapping.pipeline == "Pipeline"


def test_validate_sheet_row_prefers_english_id_when_multiple_selectors_are_filled(monkeypatch):
    monkeypatch.setattr(
        sheet_mod,
        "resolve_wordnet_synset",
        lambda **kwargs: {
            "english_id": kwargs["english_id"],
            "id": kwargs["english_id"],
            "pos": "n",
        },
    )

    mapping = detect_column_mapping(["english_id", "ili", "lemma", "pos", "pipeline"])
    row = {
        "english_id": "ENG30-00001740-n",
        "ili": "i35545",
        "lemma": "entity",
        "pos": "n",
        "pipeline": "langgraph",
    }

    result = validate_sheet_row(2, row, mapping, default_pipeline="all")

    assert result["status"] == "valid"
    assert result["selector_kind"] == "english_id"
    assert result["pipeline"] == "langgraph"
    assert "Multiple selector columns" in result["note"]


def test_validate_sheet_row_accepts_ili_selector(monkeypatch):
    monkeypatch.setattr(
        sheet_mod,
        "resolve_wordnet_synset",
        lambda **kwargs: {
            "ili_id": kwargs["ili"],
            "english_id": "ENG30-00001740-n",
            "id": "ENG30-00001740-n",
            "pos": "n",
        },
    )

    mapping = detect_column_mapping(["ili"])
    row = {"ili": "i35545"}

    result = validate_sheet_row(2, row, mapping, default_pipeline="all")

    assert result["status"] == "valid"
    assert result["selector_kind"] == "ili"
    assert result["synset_payload"]["ili_id"] == "i35545"


def test_validate_sheet_row_rejects_bad_eng30_format():
    mapping = detect_column_mapping(["english_id"])
    row = {"english_id": "wrong-format"}

    result = validate_sheet_row(2, row, mapping)

    assert result["status"] == "invalid_format"
    assert result["selector_kind"] == "english_id"


def test_validate_sheet_row_reports_not_found_for_missing_synset_name(monkeypatch):
    def _raise_missing(**kwargs):
        raise LookupError("missing synset")

    monkeypatch.setattr(sheet_mod, "resolve_wordnet_synset", _raise_missing)
    mapping = detect_column_mapping(["synset_name"])
    row = {"synset_name": "entity.n.99"}

    result = validate_sheet_row(2, row, mapping)

    assert result["status"] == "not_found"
    assert result["selector_kind"] == "synset_name"


def test_run_sheet_translation_batch_writes_nested_outputs(monkeypatch):
    artifacts_root = Path.cwd() / ".test_artifacts"
    artifacts_root.mkdir(exist_ok=True)
    scratch_dir = Path(tempfile.mkdtemp(prefix="sheet_batch_", dir=str(artifacts_root)))

    try:
        source_csv = scratch_dir / "input.csv"
        source_csv.write_text(
            "english_id,pipeline\n"
            "ENG30-00001740-n,langgraph\n"
            "ENG30-99999999-n,\n"
            "bad-selector,\n",
            encoding="utf-8",
        )

        monkeypatch.setattr(sheet_mod, "ensure_wordnet_available", lambda: None)

        def _resolve(**kwargs):
            english_id = kwargs["english_id"]
            if english_id == "ENG30-99999999-n":
                raise LookupError("missing offset")
            return {"english_id": english_id, "id": english_id, "pos": "n"}

        monkeypatch.setattr(sheet_mod, "resolve_wordnet_synset", _resolve)
        monkeypatch.setattr(
            sheet_mod,
            "run_translation_workflow",
            lambda payload, pipeline, config: {
                "selector_id": payload["english_id"],
                "source_synset": payload,
                "pipelines": {pipeline: {"translation": "entitet"}},
            },
        )

        summary = run_sheet_translation_batch(
            SheetBatchConfig(
                source=str(source_csv),
                output_dir=scratch_dir / "runs",
                workflow=WorkflowConfig(strict=False),
                default_pipeline="all",
            )
        )

        run_dir = Path(summary["run_dir"])
        assert summary["counts"] == {
            "success": 1,
            "invalid_format": 1,
            "not_found": 1,
            "error": 0,
        }
        assert (run_dir / "input" / "input.csv").exists()
        assert (run_dir / "summary" / "run_summary.json").exists()
        assert list((run_dir / "results" / "success").rglob("row_00002.json"))
        assert list((run_dir / "results" / "not_found").rglob("row_00003.json"))
        assert list((run_dir / "results" / "invalid_format").rglob("row_00004.json"))
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


def test_run_sheet_translation_batch_accepts_local_xlsx(monkeypatch):
    artifacts_root = Path.cwd() / ".test_artifacts"
    artifacts_root.mkdir(exist_ok=True)
    scratch_dir = Path(tempfile.mkdtemp(prefix="sheet_batch_xlsx_", dir=str(artifacts_root)))

    try:
        source_xlsx = scratch_dir / "input.xlsx"
        _write_test_xlsx(source_xlsx)

        monkeypatch.setattr(sheet_mod, "ensure_wordnet_available", lambda: None)
        monkeypatch.setattr(
            sheet_mod,
            "resolve_wordnet_synset",
            lambda **kwargs: {
                "english_id": kwargs["english_id"],
                "id": kwargs["english_id"],
                "pos": "n",
            },
        )
        monkeypatch.setattr(
            sheet_mod,
            "run_translation_workflow",
            lambda payload, pipeline, config: {
                "selector_id": payload["english_id"],
                "source_synset": payload,
                "pipelines": {pipeline: {"translation": "entitet"}},
            },
        )

        summary = run_sheet_translation_batch(
            SheetBatchConfig(
                source=str(source_xlsx),
                output_dir=scratch_dir / "runs",
                workflow=WorkflowConfig(strict=False),
                default_pipeline="all",
            )
        )

        run_dir = Path(summary["run_dir"])
        assert summary["source_kind"] == "local_xlsx"
        assert summary["row_count"] == 3
        assert summary["counts"] == {
            "success": 2,
            "invalid_format": 1,
            "not_found": 0,
            "error": 0,
        }
        assert (run_dir / "input" / "input.xlsx").exists()
        assert (run_dir / "input" / "sheet_snapshot.csv").exists()
        assert list((run_dir / "results" / "success").rglob("row_00002.json"))
        assert list((run_dir / "results" / "invalid_format").rglob("row_00003.json"))
        assert list((run_dir / "results" / "success").rglob("row_00004.json"))
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


def test_run_sheet_translation_batch_accepts_ili_only_input(monkeypatch):
    artifacts_root = Path.cwd() / ".test_artifacts"
    artifacts_root.mkdir(exist_ok=True)
    scratch_dir = Path(tempfile.mkdtemp(prefix="sheet_batch_ili_", dir=str(artifacts_root)))

    try:
        source_csv = scratch_dir / "input.csv"
        source_csv.write_text(
            "ili,pipeline\n"
            "i35545,baseline\n",
            encoding="utf-8",
        )

        monkeypatch.setattr(sheet_mod, "ensure_wordnet_available", lambda: None)
        monkeypatch.setattr(
            sheet_mod,
            "resolve_wordnet_synset",
            lambda **kwargs: {
                "ili_id": kwargs["ili"],
                "english_id": "ENG30-00001740-n",
                "id": "ENG30-00001740-n",
                "pos": "n",
                "lemmas": ["entity"],
                "definition": "something that exists",
                "examples": [],
            },
        )
        monkeypatch.setattr(
            sheet_mod,
            "run_translation_workflow",
            lambda *args, **kwargs: {"selector_id": "ENG30-00001740-n", "pipelines": {"baseline": {"translation": "entitet"}}},
        )

        summary = run_sheet_translation_batch(
            SheetBatchConfig(
                source=str(source_csv),
                output_dir=scratch_dir / "runs",
                workflow=WorkflowConfig(strict=False),
                default_pipeline="all",
            )
        )

        assert summary["counts"] == {
            "success": 1,
            "invalid_format": 0,
            "not_found": 0,
            "error": 0,
        }
        assert summary["column_mapping"]["ili"] == "ili"
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


def test_prepare_native_sheet_translation_batch_writes_pending_items(monkeypatch):
    artifacts_root = Path.cwd() / ".test_artifacts"
    artifacts_root.mkdir(exist_ok=True)
    scratch_dir = Path(tempfile.mkdtemp(prefix="native_sheet_batch_", dir=str(artifacts_root)))

    try:
        source_csv = scratch_dir / "input.csv"
        source_csv.write_text(
            "ili,pipeline\n"
            "i35545,conceptual\n"
            "bad-ili,\n",
            encoding="utf-8",
        )

        monkeypatch.setattr(sheet_mod, "ensure_wordnet_available", lambda: None)
        monkeypatch.setattr(
            sheet_mod,
            "resolve_wordnet_synset",
            lambda **kwargs: {
                "ili_id": kwargs["ili"],
                "english_id": "ENG30-00001740-n",
                "id": "ENG30-00001740-n",
                "pos": "n",
                "lemmas": ["entity"],
                "definition": "something that exists",
                "examples": [],
            },
        )

        summary = prepare_native_sheet_translation_batch(
            SheetBatchConfig(
                source=str(source_csv),
                output_dir=scratch_dir / "runs",
                workflow=WorkflowConfig(strict=False),
                default_pipeline="all",
            )
        )

        run_dir = Path(summary["run_dir"])
        assert summary["translation_mode"] == "native_agent"
        assert summary["counts"] == {
            "pending": 1,
            "invalid_format": 1,
            "not_found": 0,
            "error": 0,
        }
        assert list((run_dir / "work_items" / "pending").rglob("row_00002.json"))
        assert list((run_dir / "results" / "invalid_format").rglob("row_00003.json"))
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


def test_sort_and_group_candidate_records_by_sheet_header():
    records = [
        {
            "row_number": "12",
            "status": "valid",
            "resolved_english_id": "ENG30-00020090-n",
            "sheet_name": "20.4.2026",
            "source_row": "4",
            "source_column": "6",
            "source_header": "Relations",
        },
        {
            "row_number": "10",
            "status": "valid",
            "resolved_english_id": "ENG30-00006238-v",
            "sheet_name": "20.4.2026",
            "source_row": "2",
            "source_column": "1",
            "source_header": "Literals",
        },
        {
            "row_number": "11",
            "status": "valid",
            "resolved_english_id": "ENG30-01873850-n",
            "sheet_name": "20.4.2026",
            "source_row": "2",
            "source_column": "3",
            "source_header": "Definitions",
        },
        {
            "row_number": "20",
            "status": "valid",
            "resolved_english_id": "ENG30-07480356-n",
            "sheet_name": "emo-dopuna",
            "source_row": "2",
            "source_column": "1",
            "source_header": "ID",
        },
    ]

    sorted_records = sort_candidate_records_by_sheet_column(records)
    grouped_records = group_candidate_records_by_sheet_header(sorted_records)
    rendered = render_grouped_candidate_text(grouped_records)

    assert [row["resolved_english_id"] for row in sorted_records] == [
        "ENG30-00006238-v",
        "ENG30-01873850-n",
        "ENG30-00020090-n",
        "ENG30-07480356-n",
    ]
    assert grouped_records[0]["sheet_name"] == "20.4.2026"
    assert [group["header"] for group in grouped_records[0]["groups"]] == [
        "Literals",
        "Definitions",
        "Relations",
    ]
    assert grouped_records[0]["groups"][0]["english_ids"] == ["ENG30-00006238-v"]
    assert "# 20.4.2026" in rendered
    assert "## Definitions" in rendered
    assert "ENG30-07480356-n" in rendered
