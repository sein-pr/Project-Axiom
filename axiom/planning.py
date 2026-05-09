from __future__ import annotations

from typing import Any


def create_analysis_plan(manifesto: dict[str, Any], title: str) -> dict[str, Any]:
    schema = manifesto.get("schema", [])
    numeric_columns = [column["column"] for column in schema if column.get("type") == "numeric"]
    categorical_columns = [column["column"] for column in schema if column.get("type") == "categorical"]
    datetime_columns = [column["column"] for column in schema if column.get("type") == "datetime"]

    questions = _analysis_questions(numeric_columns, categorical_columns, datetime_columns)
    render_targets = ["data_manifesto.json", "summary_stats.json", "report.pdf", "slide_deck.pptx", "raw_data_dashboard.xlsx"]

    return {
        "title": title,
        "source": manifesto.get("source"),
        "row_count": manifesto.get("row_count"),
        "column_count": manifesto.get("column_count"),
        "recommended_questions": questions,
        "data_quality_focus": manifesto.get("anomaly_warnings", []),
        "planned_outputs": render_targets,
        "approval_required": True,
        "status": "awaiting_approval",
    }


def mark_plan_approved(plan: dict[str, Any]) -> dict[str, Any]:
    approved = dict(plan)
    approved["status"] = "approved"
    return approved


def _analysis_questions(
    numeric_columns: list[str],
    categorical_columns: list[str],
    datetime_columns: list[str],
) -> list[str]:
    questions: list[str] = []

    if numeric_columns:
        questions.append(f"What are the main ranges, averages, and outliers for {', '.join(numeric_columns[:4])}?")

    if numeric_columns and categorical_columns:
        questions.append(
            f"How do {numeric_columns[0]} values vary across {categorical_columns[0]}?"
        )

    if len(numeric_columns) >= 2:
        questions.append("Which numeric metrics move together most strongly?")

    if datetime_columns and numeric_columns:
        questions.append(f"How does {numeric_columns[0]} trend over {datetime_columns[0]}?")

    if not questions:
        questions.append("What are the most frequent categories and notable data quality issues?")

    return questions

