from __future__ import annotations

import json
from pathlib import Path
from typing import Any


HISTORY_FILENAME = "_visual_history.json"


def load_visual_history(output_dir: Path, limit: int = 8) -> list[dict[str, Any]]:
    path = output_dir / HISTORY_FILENAME
    if not path.exists():
        return []
    try:
        history = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(history, list):
        return []
    return [entry for entry in history if isinstance(entry, dict)][-limit:]


def append_visual_history(
    output_dir: Path,
    run_id: str,
    title: str,
    analysis_plan: dict[str, Any],
    limit: int = 20,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    history = load_visual_history(output_dir, limit=limit)
    entry = {
        "run_id": run_id,
        "title": title,
        "planner_source": analysis_plan.get("planner_source"),
        "visual_signatures": [
            _visual_signature(spec)
            for spec in analysis_plan.get("recommended_visualizations", [])
            if isinstance(spec, dict)
        ],
    }
    history = [item for item in history if item.get("run_id") != run_id]
    history.append(entry)
    (output_dir / HISTORY_FILENAME).write_text(
        json.dumps(history[-limit:], indent=2, default=str),
        encoding="utf-8",
    )


def compact_visual_history(history: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    compacted = []
    for entry in history[-limit:]:
        compacted.append(
            {
                "run_id": entry.get("run_id"),
                "title": entry.get("title"),
                "visual_signatures": entry.get("visual_signatures", [])[:6],
            }
        )
    return compacted


def _visual_signature(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "chart_type": spec.get("chart_type"),
        "angle": spec.get("angle"),
        "story_role": spec.get("story_role"),
        "x": spec.get("x"),
        "y": spec.get("y"),
        "columns": spec.get("columns", []),
        "title": spec.get("title"),
    }
