"""Queue management helpers for native-agent translation batches."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .sheet_translation_workflow import _build_result_path, _write_json

_WORK_ITEM_STATES: Tuple[str, ...] = ("pending", "in_progress", "completed", "failed")
_RESULT_STATES: Tuple[str, ...] = ("success", "error", "invalid_format", "not_found")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _work_items_root(run_dir: Path) -> Path:
    return Path(run_dir) / "work_items"


def _work_item_state_dir(run_dir: Path, state: str) -> Path:
    if state not in _WORK_ITEM_STATES:
        raise ValueError(f"Unsupported work item state {state!r}.")
    return _work_items_root(run_dir) / state


def _ensure_queue_dirs(run_dir: Path) -> None:
    run_dir = Path(run_dir)
    for state in _WORK_ITEM_STATES:
        (_work_items_root(run_dir) / state).mkdir(parents=True, exist_ok=True)
    for result_state in _RESULT_STATES:
        (run_dir / "results" / result_state).mkdir(parents=True, exist_ok=True)
    (run_dir / "summary").mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _work_item_sort_key(path: Path) -> Tuple[int, str]:
    try:
        payload = _load_json(path)
        return int(payload.get("row_number", 10**9)), str(path)
    except Exception:
        return 10**9, str(path)


def list_native_work_items(run_dir: Path, state: str = "pending") -> List[Path]:
    """List native-agent work items for the given queue state."""
    _ensure_queue_dirs(Path(run_dir))
    return sorted(_work_item_state_dir(Path(run_dir), state).rglob("row_*.json"), key=_work_item_sort_key)


def _resolve_work_item_location(run_dir: Path, work_item_path: Path) -> Tuple[str, Path]:
    run_dir = Path(run_dir)
    work_item_path = Path(work_item_path)
    for state in _WORK_ITEM_STATES:
        state_dir = _work_item_state_dir(run_dir, state)
        try:
            relative_path = work_item_path.relative_to(state_dir)
            return state, relative_path
        except ValueError:
            continue
    raise ValueError(
        f"Work item path {str(work_item_path)!r} is not inside {str(_work_items_root(run_dir))!r}."
    )


def summarize_native_batch_run(run_dir: Path) -> Dict[str, Any]:
    """Compute and persist queue progress for a native-agent batch run."""
    run_dir = Path(run_dir)
    _ensure_queue_dirs(run_dir)

    work_item_counts = {
        state: len(list_native_work_items(run_dir, state))
        for state in _WORK_ITEM_STATES
    }
    result_counts = {
        state: len(list((run_dir / "results" / state).rglob("row_*.json")))
        for state in _RESULT_STATES
    }

    base_summary_path = run_dir / "summary" / "run_summary.json"
    base_summary: Dict[str, Any] = {}
    if base_summary_path.exists():
        try:
            base_summary = _load_json(base_summary_path)
        except Exception:
            base_summary = {}

    progress = {
        "run_dir": str(run_dir),
        "updated_at": _utc_now_iso(),
        "translation_mode": base_summary.get("translation_mode", "native_agent"),
        "row_count": base_summary.get("row_count"),
        "source": base_summary.get("source"),
        "source_kind": base_summary.get("source_kind"),
        "default_pipeline": base_summary.get("default_pipeline"),
        "retranslate_existing_allowed": base_summary.get("retranslate_existing_allowed", True),
        "work_item_counts": work_item_counts,
        "result_counts": result_counts,
        "all_finished": work_item_counts["pending"] == 0 and work_item_counts["in_progress"] == 0,
    }

    _write_json(run_dir / "summary" / "native_progress.json", progress)
    return progress


def claim_next_native_work_item(run_dir: Path) -> Optional[Dict[str, Any]]:
    """Claim the next pending work item and move it into the in-progress queue."""
    run_dir = Path(run_dir)
    _ensure_queue_dirs(run_dir)
    pending_items = list_native_work_items(run_dir, "pending")
    if not pending_items:
        summarize_native_batch_run(run_dir)
        return None

    pending_root = _work_item_state_dir(run_dir, "pending")
    in_progress_root = _work_item_state_dir(run_dir, "in_progress")
    for pending_path in pending_items:
        relative_path = pending_path.relative_to(pending_root)
        in_progress_path = in_progress_root / relative_path
        in_progress_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            pending_path.rename(in_progress_path)
        except FileNotFoundError:
            # Another worker claimed this item first. Try the next pending item.
            continue
        break
    else:
        summarize_native_batch_run(run_dir)
        return None

    work_item = _load_json(in_progress_path)
    work_item["status"] = "in_progress"
    work_item["claimed_at"] = _utc_now_iso()
    _write_json(in_progress_path, work_item)

    progress = summarize_native_batch_run(run_dir)
    return {
        "work_item_path": str(in_progress_path),
        "work_item": work_item,
        "progress": progress,
    }


def complete_native_work_item(
    run_dir: Path,
    work_item_path: Path,
    translation_result: Mapping[str, Any],
    *,
    translation_mode: str = "native_agent",
) -> Dict[str, Any]:
    """Mark an in-progress work item as completed and write its success artifact."""
    run_dir = Path(run_dir)
    work_item_path = Path(work_item_path)
    _ensure_queue_dirs(run_dir)
    state, relative_path = _resolve_work_item_location(run_dir, work_item_path)
    if state not in {"pending", "in_progress"}:
        raise ValueError(
            f"Cannot complete work item in state {state!r}; expected pending or in_progress."
        )

    work_item = _load_json(work_item_path)
    success_payload = {
        "row_number": work_item["row_number"],
        "status": "success",
        "selector_kind": work_item.get("selector_kind"),
        "selector_value": work_item.get("selector_value"),
        "pipeline": work_item.get("pipeline"),
        "note": work_item.get("note"),
        "message": "",
        "synset_payload": work_item.get("synset_payload"),
        "source_row": work_item.get("source_row"),
        "translation_result": dict(translation_result),
        "translation_mode": translation_mode,
        "completed_at": _utc_now_iso(),
    }
    result_path = _build_result_path(run_dir, "success", work_item)
    _write_json(result_path, success_payload)

    completed_path = _work_item_state_dir(run_dir, "completed") / relative_path
    completed_path.parent.mkdir(parents=True, exist_ok=True)
    work_item["status"] = "completed"
    work_item["completed_at"] = success_payload["completed_at"]
    work_item["translation_result"] = dict(translation_result)
    work_item["translation_mode"] = translation_mode
    work_item["result_path"] = str(result_path)
    _write_json(completed_path, work_item)
    work_item_path.unlink()

    progress = summarize_native_batch_run(run_dir)
    return {
        "status": "completed",
        "work_item_path": str(completed_path),
        "result_path": str(result_path),
        "progress": progress,
    }


def fail_native_work_item(
    run_dir: Path,
    work_item_path: Path,
    message: str,
    details: Optional[Mapping[str, Any]] = None,
    *,
    translation_mode: str = "native_agent",
) -> Dict[str, Any]:
    """Mark an in-progress work item as failed and write its error artifact."""
    run_dir = Path(run_dir)
    work_item_path = Path(work_item_path)
    _ensure_queue_dirs(run_dir)
    state, relative_path = _resolve_work_item_location(run_dir, work_item_path)
    if state not in {"pending", "in_progress"}:
        raise ValueError(
            f"Cannot fail work item in state {state!r}; expected pending or in_progress."
        )

    work_item = _load_json(work_item_path)
    error_payload = {
        "row_number": work_item["row_number"],
        "status": "error",
        "selector_kind": work_item.get("selector_kind"),
        "selector_value": work_item.get("selector_value"),
        "pipeline": work_item.get("pipeline"),
        "note": work_item.get("note"),
        "message": str(message),
        "synset_payload": work_item.get("synset_payload"),
        "source_row": work_item.get("source_row"),
        "translation_mode": translation_mode,
        "failed_at": _utc_now_iso(),
    }
    if details is not None:
        error_payload["error_details"] = dict(details)

    result_path = _build_result_path(run_dir, "error", work_item)
    _write_json(result_path, error_payload)

    failed_path = _work_item_state_dir(run_dir, "failed") / relative_path
    failed_path.parent.mkdir(parents=True, exist_ok=True)
    work_item["status"] = "failed"
    work_item["failed_at"] = error_payload["failed_at"]
    work_item["message"] = str(message)
    work_item["translation_mode"] = translation_mode
    work_item["result_path"] = str(result_path)
    if details is not None:
        work_item["error_details"] = dict(details)
    _write_json(failed_path, work_item)
    work_item_path.unlink()

    progress = summarize_native_batch_run(run_dir)
    return {
        "status": "failed",
        "work_item_path": str(failed_path),
        "result_path": str(result_path),
        "progress": progress,
    }


def requeue_in_progress_native_work_items(run_dir: Path) -> Dict[str, Any]:
    """Move all in-progress work items back to pending after an interrupted worker."""
    run_dir = Path(run_dir)
    _ensure_queue_dirs(run_dir)

    moved: List[str] = []
    in_progress_dir = _work_item_state_dir(run_dir, "in_progress")
    pending_dir = _work_item_state_dir(run_dir, "pending")
    for work_item_path in list_native_work_items(run_dir, "in_progress"):
        relative_path = work_item_path.relative_to(in_progress_dir)
        pending_path = pending_dir / relative_path
        pending_path.parent.mkdir(parents=True, exist_ok=True)

        work_item = _load_json(work_item_path)
        work_item["status"] = "pending"
        work_item["requeued_at"] = _utc_now_iso()
        work_item.pop("claimed_at", None)
        _write_json(pending_path, work_item)
        work_item_path.unlink()
        moved.append(str(pending_path))

    progress = summarize_native_batch_run(run_dir)
    return {
        "status": "requeued",
        "count": len(moved),
        "work_item_paths": moved,
        "progress": progress,
    }
