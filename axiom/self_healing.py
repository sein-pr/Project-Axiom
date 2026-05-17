from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from axiom.analysis import analyze_dataset
from axiom.llm import GroqPlanner


MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class SelfHealingResult:
    analysis: dict[str, Any]
    used_fallback: bool
    workspace: Path
    attempts: list[dict[str, Any]]


def run_self_healing_analysis(
    frame: pd.DataFrame,
    manifesto: dict[str, Any],
    analysis_plan: dict[str, Any],
    workspace: Path,
    use_llm: bool = True,
    max_attempts: int = MAX_ATTEMPTS,
    initial_code: str | None = None,
) -> SelfHealingResult:
    workspace.mkdir(parents=True, exist_ok=True)
    _write_workspace_inputs(frame, manifesto, analysis_plan, workspace)

    attempts: list[dict[str, Any]] = []
    code = initial_code or _initial_analyst_code(manifesto, analysis_plan)
    repairer = GroqPlanner() if use_llm else None

    for attempt_number in range(1, max_attempts + 1):
        attempt_path = workspace / f"attempt_{attempt_number}.py"
        attempt_path.write_text(code, encoding="utf-8")

        run = _run_attempt(attempt_path, workspace)
        attempt_record = {
            "attempt": attempt_number,
            "script": attempt_path.name,
            "returncode": run.returncode,
            "stdout": run.stdout[-4000:],
            "stderr": run.stderr[-4000:],
        }

        if run.returncode == 0 and (workspace / "result.json").exists():
            analysis = json.loads((workspace / "result.json").read_text(encoding="utf-8"))
            attempt_record["status"] = "succeeded"
            attempts.append(attempt_record)
            final_path = workspace / "final_analysis.py"
            final_path.write_text(code, encoding="utf-8")
            _write_trace(workspace, attempts, used_fallback=False)
            analysis["self_healing"] = _analysis_metadata(workspace, attempts, used_fallback=False)
            return SelfHealingResult(analysis=analysis, used_fallback=False, workspace=workspace, attempts=attempts)

        attempt_record["status"] = "failed"
        attempts.append(attempt_record)
        (workspace / f"attempt_{attempt_number}_error.txt").write_text(run.stderr, encoding="utf-8")

        repaired = None
        if repairer:
            repaired = repairer.repair_code(code, run.stderr, manifesto, analysis_plan)
        code = _safe_repaired_code(repaired) or _deterministic_repair_code(manifesto, analysis_plan)

    fallback = analyze_dataset(frame)
    fallback["self_healing"] = _analysis_metadata(workspace, attempts, used_fallback=True)
    (workspace / "fallback_result.json").write_text(json.dumps(fallback, indent=2, default=str), encoding="utf-8")
    _write_trace(workspace, attempts, used_fallback=True)
    return SelfHealingResult(analysis=fallback, used_fallback=True, workspace=workspace, attempts=attempts)


def _write_workspace_inputs(
    frame: pd.DataFrame,
    manifesto: dict[str, Any],
    analysis_plan: dict[str, Any],
    workspace: Path,
) -> None:
    serializable = frame.copy()
    for column in serializable.columns:
        if pd.api.types.is_datetime64_any_dtype(serializable[column]):
            serializable[column] = serializable[column].dt.strftime("%Y-%m-%dT%H:%M:%S")

    serializable.to_csv(workspace / "analysis_input.csv", index=False)
    (workspace / "manifesto.json").write_text(json.dumps(manifesto, indent=2, default=str), encoding="utf-8")
    (workspace / "analysis_plan.json").write_text(json.dumps(analysis_plan, indent=2, default=str), encoding="utf-8")


def _run_attempt(script_path: Path, workspace: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONNOUSERSITE"] = "1"
    try:
        return subprocess.run(
            [sys.executable, script_path.name],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
            shell=False,
        )
    except subprocess.TimeoutExpired as error:
        return subprocess.CompletedProcess(
            args=[sys.executable, script_path.name],
            returncode=124,
            stdout=error.stdout or "",
            stderr=error.stderr or "Analyst attempt timed out.",
        )


def _safe_repaired_code(code: str | None) -> str | None:
    if not code:
        return None
    forbidden = ("subprocess", "socket", "requests", "urllib", "shutil", "os.system", "open('../", "open('..")
    if any(token in code for token in forbidden):
        return None
    if "result.json" not in code or "analysis_input.csv" not in code:
        return None
    return code


def _deterministic_repair_code(manifesto: dict[str, Any], analysis_plan: dict[str, Any]) -> str:
    return _initial_analyst_code(manifesto, analysis_plan)


def _initial_analyst_code(manifesto: dict[str, Any], analysis_plan: dict[str, Any]) -> str:
    datetime_columns = [
        item["column"]
        for item in manifesto.get("schema", [])
        if item.get("type") == "datetime"
    ]
    return f'''from __future__ import annotations

import json
import pandas as pd


def round_value(value):
    if pd.isna(value):
        return None
    return round(float(value), 4)


def main():
    frame = pd.read_csv("analysis_input.csv")
    for column in {datetime_columns!r}:
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")

    numeric_columns = frame.select_dtypes(include="number").columns.tolist()
    categorical_columns = frame.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    datetime_columns = [
        column for column in frame.columns if pd.api.types.is_datetime64_any_dtype(frame[column])
    ]

    numeric_summary = {{}}
    for column in numeric_columns:
        description = frame[column].describe()
        numeric_summary[column] = {{
            "count": int(description.get("count", 0)),
            "mean": round_value(description.get("mean")),
            "median": round_value(frame[column].median()),
            "min": round_value(description.get("min")),
            "max": round_value(description.get("max")),
            "std": round_value(description.get("std")),
        }}

    categorical_summary = {{}}
    for column in categorical_columns[:12]:
        categorical_summary[column] = frame[column].dropna().astype(str).value_counts().head(8).to_dict()

    correlations = {{}}
    if len(numeric_columns) >= 2:
        corr = frame[numeric_columns].corr(numeric_only=True).round(4)
        correlations = corr.where(pd.notna(corr), None).to_dict()

    insights = []
    for column, summary in numeric_summary.items():
        if summary["count"]:
            insights.append(
                f"{{column}} ranges from {{summary['min']}} to {{summary['max']}} with an average of {{summary['mean']}}."
            )
    for column, counts in categorical_summary.items():
        if counts:
            insights.append(f"{{column}} is led by '{{next(iter(counts))}}' among observed categories.")

    result = {{
        "row_count": int(len(frame)),
        "analysis_row_count": int(len(frame)),
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "datetime_columns": datetime_columns,
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
        "correlations": correlations,
        "insight_candidates": insights[:8],
    }}

    with open("result.json", "w", encoding="utf-8") as output:
        json.dump(result, output, indent=2, default=str)


if __name__ == "__main__":
    main()
'''


def _analysis_metadata(workspace: Path, attempts: list[dict[str, Any]], used_fallback: bool) -> dict[str, Any]:
    return {
        "enabled": True,
        "used_fallback": used_fallback,
        "workspace": str(workspace),
        "attempt_count": len(attempts),
        "attempts": [
            {
                "attempt": attempt["attempt"],
                "script": attempt["script"],
                "status": attempt["status"],
                "returncode": attempt["returncode"],
            }
            for attempt in attempts
        ],
    }


def _write_trace(workspace: Path, attempts: list[dict[str, Any]], used_fallback: bool) -> None:
    payload = {"used_fallback": used_fallback, "attempts": attempts}
    (workspace / "self_healing_trace.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
