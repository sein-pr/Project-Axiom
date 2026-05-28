from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from axiom.analysis import analyze_dataset
from axiom.llm import GroqPlanner
from axiom.sandbox import AnalystSandbox, SandboxBackend


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
    sandbox_backend: SandboxBackend = "auto",
    max_attempts: int = MAX_ATTEMPTS,
    initial_code: str | None = None,
) -> SelfHealingResult:
    workspace.mkdir(parents=True, exist_ok=True)
    _write_workspace_inputs(frame, manifesto, analysis_plan, workspace)

    attempts: list[dict[str, Any]] = []
    code = initial_code or _initial_analyst_code(manifesto, analysis_plan)
    repairer = GroqPlanner() if use_llm else None
    sandbox = AnalystSandbox(sandbox_backend)

    try:
        for attempt_number in range(1, max_attempts + 1):
            attempt_path = workspace / f"attempt_{attempt_number}.py"
            attempt_path.write_text(code, encoding="utf-8")

            run = sandbox.run_attempt(attempt_path, workspace)
            attempt_record = {
                "attempt": attempt_number,
                "script": attempt_path.name,
                "backend": run.backend,
                "sandbox_id": run.sandbox_id,
                "returncode": run.returncode,
                "stdout": run.stdout[-4000:],
                "stderr": run.stderr[-4000:],
                "metadata": run.metadata,
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
    finally:
        sandbox.close()

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
    numeric_columns = [
        item["column"]
        for item in manifesto.get("schema", [])
        if item.get("type") == "numeric"
    ]
    categorical_columns = [
        item["column"]
        for item in manifesto.get("schema", [])
        if item.get("type") in {"categorical", "text", "string"}
    ]
    datetime_columns = [
        item["column"]
        for item in manifesto.get("schema", [])
        if item.get("type") == "datetime"
    ]
    return f'''from __future__ import annotations

import csv
import json
import math
from collections import Counter
from statistics import median


def round_value(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), 4)


def to_float(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def summarize(values):
    clean = [value for value in values if value is not None]
    if not clean:
        return {{"count": 0, "mean": None, "median": None, "min": None, "max": None, "std": None}}
    mean = sum(clean) / len(clean)
    std = None
    if len(clean) > 1:
        std = math.sqrt(sum((value - mean) ** 2 for value in clean) / (len(clean) - 1))
    return {{
        "count": len(clean),
        "mean": round_value(mean),
        "median": round_value(median(clean)),
        "min": round_value(min(clean)),
        "max": round_value(max(clean)),
        "std": round_value(std),
    }}


def pearson(left, right):
    pairs = [(x, y) for x, y in zip(left, right) if x is not None and y is not None]
    if len(pairs) < 2:
        return None
    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    denominator_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denominator_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denominator_x == 0 or denominator_y == 0:
        return None
    return round_value(numerator / (denominator_x * denominator_y))


def main():
    with open("analysis_input.csv", newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))

    numeric_columns = [column for column in {numeric_columns!r} if rows and column in rows[0]]
    categorical_columns = [column for column in {categorical_columns!r} if rows and column in rows[0]]
    datetime_columns = [column for column in {datetime_columns!r} if rows and column in rows[0]]

    numeric_summary = {{}}
    numeric_values = {{}}
    for column in numeric_columns:
        values = [to_float(row.get(column)) for row in rows]
        numeric_values[column] = values
        numeric_summary[column] = summarize(values)

    categorical_summary = {{}}
    for column in categorical_columns[:12]:
        values = [str(row.get(column, "")).strip() for row in rows if str(row.get(column, "")).strip()]
        categorical_summary[column] = dict(Counter(values).most_common(8))

    correlations = {{}}
    if len(numeric_columns) >= 2:
        for left in numeric_columns:
            correlations[left] = {{}}
            for right in numeric_columns:
                correlations[left][right] = 1.0 if left == right else pearson(numeric_values[left], numeric_values[right])

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
        "row_count": int(len(rows)),
        "analysis_row_count": int(len(rows)),
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
                "backend": attempt.get("backend"),
                "sandbox_id": attempt.get("sandbox_id"),
                "status": attempt["status"],
                "returncode": attempt["returncode"],
            }
            for attempt in attempts
        ],
    }


def _write_trace(workspace: Path, attempts: list[dict[str, Any]], used_fallback: bool) -> None:
    payload = {"used_fallback": used_fallback, "attempts": attempts}
    (workspace / "self_healing_trace.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
