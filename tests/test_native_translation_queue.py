import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

from wordnet_autotranslate.workflows import sheet_translation_workflow as sheet_mod
from wordnet_autotranslate.workflows.native_translation_queue import (
    claim_next_native_work_item,
    complete_native_work_item,
    fail_native_work_item,
    requeue_in_progress_native_work_items,
    summarize_native_batch_run,
)
from wordnet_autotranslate.workflows.sheet_translation_workflow import (
    SheetBatchConfig,
    prepare_native_sheet_translation_batch,
)
from wordnet_autotranslate.workflows.synset_translation_workflow import WorkflowConfig

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "manage_native_translation_batch.py"

_spec = importlib.util.spec_from_file_location("manage_native_translation_batch", SCRIPT_PATH)
cli = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(cli)


def _prepare_native_run(monkeypatch, scratch_dir: Path) -> Path:
    source_csv = scratch_dir / "input.csv"
    source_csv.write_text(
        "ili,pipeline\n"
        "i35545,conceptual\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(sheet_mod, "ensure_wordnet_available", lambda: None)
    monkeypatch.setattr(
        sheet_mod,
        "resolve_wordnet_synset",
        lambda **kwargs: {
            "ili_id": kwargs.get("ili"),
            "english_id": "ENG30-00001740-n",
            "id": "ENG30-00001740-n",
            "pos": "n",
            "lemmas": ["entity"],
            "definition": "something that exists",
            "examples": [],
            "hypernyms": [{"name": "thing.n.01"}],
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
    return Path(summary["run_dir"])


def test_native_queue_claim_and_complete_lifecycle(monkeypatch):
    artifacts_root = Path.cwd() / ".test_artifacts"
    artifacts_root.mkdir(exist_ok=True)
    scratch_dir = Path(tempfile.mkdtemp(prefix="native_queue_complete_", dir=str(artifacts_root)))

    try:
        run_dir = _prepare_native_run(monkeypatch, scratch_dir)
        assert (run_dir / "summary" / "native_progress.json").exists()

        claimed = claim_next_native_work_item(run_dir)
        assert claimed is not None
        work_item_path = Path(claimed["work_item_path"])
        assert "in_progress" in str(work_item_path)
        assert claimed["work_item"]["status"] == "in_progress"

        translation_result = {
            "selector_id": "ENG30-00001740-n",
            "source_synset": claimed["work_item"]["synset_payload"],
            "pipelines": {
                "conceptual": {
                    "translation": "entitet",
                    "selected_literals_sr": ["entitet"],
                    "final_gloss_sr": "ono što postoji kao zasebna celina",
                }
            },
        }
        completed = complete_native_work_item(
            run_dir,
            work_item_path,
            translation_result,
            translation_mode="repo_ollama",
        )

        result_path = Path(completed["result_path"])
        assert result_path.exists()
        result_payload = json.loads(result_path.read_text(encoding="utf-8"))
        assert result_payload["translation_mode"] == "repo_ollama"
        assert "results" in str(result_path)
        progress = completed["progress"]
        assert progress["work_item_counts"]["pending"] == 0
        assert progress["work_item_counts"]["in_progress"] == 0
        assert progress["work_item_counts"]["completed"] == 1
        assert progress["result_counts"]["success"] == 1
        assert progress["all_finished"] is True
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


def test_native_queue_claim_and_fail_lifecycle(monkeypatch):
    artifacts_root = Path.cwd() / ".test_artifacts"
    artifacts_root.mkdir(exist_ok=True)
    scratch_dir = Path(tempfile.mkdtemp(prefix="native_queue_fail_", dir=str(artifacts_root)))

    try:
        run_dir = _prepare_native_run(monkeypatch, scratch_dir)

        claimed = claim_next_native_work_item(run_dir)
        assert claimed is not None
        failed = fail_native_work_item(
            run_dir,
            Path(claimed["work_item_path"]),
            "native translation stalled",
            details={"stage": "conceptual"},
        )

        result_path = Path(failed["result_path"])
        assert result_path.exists()
        result_payload = json.loads(result_path.read_text(encoding="utf-8"))
        assert result_payload["status"] == "error"
        assert result_payload["message"] == "native translation stalled"
        assert failed["progress"]["work_item_counts"]["failed"] == 1
        assert failed["progress"]["result_counts"]["error"] == 1
        assert failed["progress"]["all_finished"] is True
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


def test_native_queue_requeues_in_progress_items(monkeypatch):
    artifacts_root = Path.cwd() / ".test_artifacts"
    artifacts_root.mkdir(exist_ok=True)
    scratch_dir = Path(tempfile.mkdtemp(prefix="native_queue_requeue_", dir=str(artifacts_root)))

    try:
        run_dir = _prepare_native_run(monkeypatch, scratch_dir)
        claimed = claim_next_native_work_item(run_dir)
        assert claimed is not None

        requeued = requeue_in_progress_native_work_items(run_dir)
        assert requeued["count"] == 1
        assert requeued["progress"]["work_item_counts"]["pending"] == 1
        assert requeued["progress"]["work_item_counts"]["in_progress"] == 0
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


def test_manage_native_translation_batch_cli_claim_complete_and_status(monkeypatch, capsys):
    artifacts_root = Path.cwd() / ".test_artifacts"
    artifacts_root.mkdir(exist_ok=True)
    scratch_dir = Path(tempfile.mkdtemp(prefix="native_queue_cli_", dir=str(artifacts_root)))

    try:
        run_dir = _prepare_native_run(monkeypatch, scratch_dir)

        monkeypatch.setattr("sys.argv", ["prog", "claim-next", str(run_dir)])
        assert cli.main() == 0
        claim_payload = json.loads(capsys.readouterr().out)
        assert claim_payload["status"] == "claimed"
        work_item_path = claim_payload["work_item_path"]

        translation_result = {
            "selector_id": "ENG30-00001740-n",
            "source_synset": claim_payload["work_item"]["synset_payload"],
            "pipelines": {"baseline": {"translation": "entitet"}},
        }
        monkeypatch.setattr(
            "sys.argv",
            [
                "prog",
                "complete",
                str(run_dir),
                work_item_path,
                "--result-json",
                json.dumps(translation_result, ensure_ascii=False),
            ],
        )
        assert cli.main() == 0
        complete_payload = json.loads(capsys.readouterr().out)
        assert complete_payload["status"] == "completed"

        monkeypatch.setattr("sys.argv", ["prog", "status", str(run_dir)])
        assert cli.main() == 0
        status_payload = json.loads(capsys.readouterr().out)
        assert status_payload["all_finished"] is True
        assert status_payload["result_counts"]["success"] == 1
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)
