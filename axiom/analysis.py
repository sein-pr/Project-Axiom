from __future__ import annotations

from typing import Any

import pandas as pd


def analyze_dataset(frame: pd.DataFrame) -> dict[str, Any]:
    numeric_columns = frame.select_dtypes(include="number").columns.tolist()
    categorical_columns = frame.select_dtypes(include=["string", "object", "category"]).columns.tolist()
    datetime_columns = frame.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns.tolist()

    numeric_summary = {}
    for column in numeric_columns:
        description = frame[column].describe()
        numeric_summary[column] = {
            "count": int(description.get("count", 0)),
            "mean": _round(description.get("mean")),
            "median": _round(frame[column].median()),
            "min": _round(description.get("min")),
            "max": _round(description.get("max")),
            "std": _round(description.get("std")),
        }

    categorical_summary = {}
    for column in categorical_columns[:12]:
        values = frame[column].dropna().astype(str)
        categorical_summary[column] = values.value_counts().head(8).to_dict()

    correlations = {}
    if len(numeric_columns) >= 2:
        corr = frame[numeric_columns].corr(numeric_only=True).round(4)
        correlations = corr.where(pd.notna(corr), None).to_dict()

    insight_candidates = _build_insights(numeric_summary, categorical_summary, correlations)

    return {
        "row_count": int(len(frame)),
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "datetime_columns": datetime_columns,
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
        "correlations": correlations,
        "insight_candidates": insight_candidates,
    }


def _round(value: object) -> float | None:
    if pd.isna(value):
        return None
    return round(float(value), 4)


def _build_insights(
    numeric_summary: dict[str, Any],
    categorical_summary: dict[str, Any],
    correlations: dict[str, Any],
) -> list[str]:
    insights: list[str] = []

    for column, summary in numeric_summary.items():
        if summary["count"]:
            insights.append(
                f"{column} ranges from {summary['min']} to {summary['max']} with an average of {summary['mean']}."
            )

    for column, counts in categorical_summary.items():
        if counts:
            top_value = next(iter(counts))
            insights.append(f"{column} is led by '{top_value}' among observed categories.")

    strongest = _strongest_correlation(correlations)
    if strongest:
        left, right, value = strongest
        insights.append(f"{left} and {right} show the strongest numeric correlation at {value}.")

    return insights[:8]


def _strongest_correlation(correlations: dict[str, Any]) -> tuple[str, str, float] | None:
    strongest: tuple[str, str, float] | None = None
    for left, row in correlations.items():
        for right, value in row.items():
            if left == right or value is None:
                continue
            absolute = abs(float(value))
            if strongest is None or absolute > abs(strongest[2]):
                strongest = (left, right, float(value))
    return strongest

