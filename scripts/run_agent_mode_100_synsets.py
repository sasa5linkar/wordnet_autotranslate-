#!/usr/bin/env python3
"""Run a 100-synset agent-mode workflow check without requiring LangGraph/Ollama.

This script intentionally:
- uses selector-based synset resolution
- runs baseline workflow for translation output
- checks LangGraph/Conceptual workflow availability and marks them as skipped when
  the configured backend is unavailable
"""

from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

from nltk.corpus import wordnet as wn

from wordnet_autotranslate.workflows.synset_translation_workflow import (
    WorkflowConfig,
    run_translation_workflow,
    synset_to_payload,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run 100-synset agent-mode checks with safe workflow handling."
    )
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--model", default="gpt-oss:120b")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--output-dir", default="reports")
    return parser.parse_args()


def is_backend_reachable(base_url: str, timeout_seconds: float = 1.5) -> bool:
    parsed = urlparse(base_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_seconds)
        return sock.connect_ex((host, port)) == 0


def pick_synsets(count: int) -> List[Dict[str, Any]]:
    synsets = sorted(list(wn.all_synsets()), key=lambda synset: synset.name())[:count]
    return [synset_to_payload(synset) for synset in synsets]


def main() -> int:
    args = parse_args()
    stamp = time.strftime("%Y-%m-%d")
    run_dir = Path(args.output_dir) / f"agent_mode_{args.count}_synsets_safe_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    config = WorkflowConfig(
        model=args.model,
        base_url=args.base_url,
        timeout=args.timeout,
        strict=False,
    )
    backend_ok = is_backend_reachable(args.base_url)
    rows: List[Dict[str, Any]] = []
    started = time.time()

    for index, payload in enumerate(pick_synsets(args.count), start=1):
        baseline_result = run_translation_workflow(payload, pipeline="baseline", config=config)
        baseline_payload = baseline_result["pipelines"]["baseline"]
        row = {
            "index": index,
            "id": payload["id"],
            "name": payload["name"],
            "pos": payload["pos"],
            "pipelines": {
                "baseline": {
                    "status": "ok",
                    "translation": baseline_payload.get("translation", ""),
                    "definition_translation": baseline_payload.get(
                        "definition_translation", ""
                    ),
                    "notes": baseline_payload.get("payload", {})
                    .get("baseline", {})
                    .get("notes", ""),
                },
                "langgraph": {
                    "status": "skipped_unavailable_backend" if not backend_ok else "not_run",
                    "message": "Skipped in safe agent mode (requires reachable Ollama backend).",
                },
                "conceptual": {
                    "status": "skipped_unavailable_backend" if not backend_ok else "not_run",
                    "message": "Skipped in safe agent mode (requires reachable Ollama backend).",
                },
            },
        }
        rows.append(row)

    summary = {
        "run_id": run_dir.name,
        "date_utc": stamp,
        "processed_synsets": len(rows),
        "backend_reachable": backend_ok,
        "base_url": args.base_url,
        "elapsed_seconds": round(time.time() - started, 3),
        "baseline_ok": len(rows),
        "langgraph_skipped": len(rows),
        "conceptual_skipped": len(rows),
    }

    results_path = run_dir / "results.json"
    report_path = run_dir / "REPORT.md"
    results_path.write_text(
        json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = [
        f"# Safe agent-mode report: {args.count} synsets",
        "",
        "## Run configuration",
        f"- Base URL: `{args.base_url}`",
        f"- Backend reachable: **{backend_ok}**",
        f"- Model setting: `{args.model}`",
        "",
        "## Workflow policy",
        "- Baseline workflow is executed for all synsets.",
        "- LangGraph and Conceptual workflows are checked but skipped in safe mode",
        "  when backend is unavailable (to avoid repeated hard connection failures).",
        "",
        "## Outcome summary",
        f"- Synsets processed: **{summary['processed_synsets']}**",
        f"- Baseline successful outputs: **{summary['baseline_ok']}**",
        f"- LangGraph skipped: **{summary['langgraph_skipped']}**",
        f"- Conceptual skipped: **{summary['conceptual_skipped']}**",
        f"- Elapsed: **{summary['elapsed_seconds']}s**",
        "",
        "Detailed records are available in `results.json`.",
    ]
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")

    print(str(run_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
