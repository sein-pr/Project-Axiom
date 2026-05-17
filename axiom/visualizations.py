from __future__ import annotations

from typing import Any

import pandas as pd


SUPPORTED_CHART_TYPES = {"bar", "line", "scatter", "histogram", "heatmap"}
VISUAL_ANGLES = (
    "revenue_growth",
    "customer_behavior",
    "product_mix",
    "inventory_health",
    "review_quality",
    "payment_behavior",
    "geography",
    "relationship_diagnostics",
)


def deterministic_visualizations(frame: pd.DataFrame, measures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    numeric_columns = [
        column
        for column in frame.select_dtypes(include="number").columns.tolist()
        if not _looks_like_identifier(column)
    ]
    categorical_columns = frame.select_dtypes(include=["string", "object", "category"]).columns.tolist()
    datetime_columns = [
        column for column in frame.columns if pd.api.types.is_datetime64_any_dtype(frame[column])
    ]
    measure_names = [measure["name"] for measure in measures if measure["name"] in frame.columns]
    primary_measure = _first_existing(
        measure_names,
        _preferred_business_measures(numeric_columns),
    )

    specs: list[dict[str, Any]] = []
    available_angles = _available_angles(frame)
    story_arc = _story_arc(available_angles)

    if datetime_columns and primary_measure:
        specs.append(
            {
                "chart_type": "line",
                "title": f"{primary_measure} trend over {datetime_columns[0]}",
                "x": datetime_columns[0],
                "y": primary_measure,
                "aggregation": "sum",
                "story_role": "trend",
                "angle": "revenue_growth",
                "rationale": "Time trends are often the first executive view of business performance.",
            }
        )

    if categorical_columns and primary_measure:
        specs.append(
            {
                "chart_type": "bar",
                "title": f"{primary_measure} by {categorical_columns[0]}",
                "x": categorical_columns[0],
                "y": primary_measure,
                "aggregation": "sum",
                "story_role": "segment_compare",
                "angle": _category_angle(categorical_columns[0]),
                "rationale": "Category comparison reveals performance concentration.",
            }
        )

    category_column = _first_present(frame.columns.tolist(), ["category", "product_category", "department"])
    brand_column = _first_present(frame.columns.tolist(), ["brand", "vendor", "manufacturer"])
    country_column = _first_present(frame.columns.tolist(), ["shipping_country", "country", "region", "state"])
    payment_column = _first_present(frame.columns.tolist(), ["payment_method", "payment_type"])
    stock_measure = _first_present(frame.columns.tolist(), ["stock_quantity", "inventory_value"])
    rating_measure = _first_present(frame.columns.tolist(), ["rating", "review_score", "stars"])

    if category_column and primary_measure:
        specs.append(
            {
                "chart_type": "bar",
                "title": f"{primary_measure} category mix",
                "x": category_column,
                "y": primary_measure,
                "aggregation": "sum",
                "story_role": "driver",
                "angle": "product_mix",
                "rationale": "Category mix shows where business value is concentrated.",
            }
        )

    if country_column and primary_measure:
        specs.append(
            {
                "chart_type": "bar",
                "title": f"{primary_measure} by geography",
                "x": country_column,
                "y": primary_measure,
                "aggregation": "sum",
                "story_role": "behavior",
                "angle": "geography",
                "rationale": "Geographic views expose market concentration and expansion opportunities.",
            }
        )

    if payment_column and primary_measure:
        specs.append(
            {
                "chart_type": "bar",
                "title": f"{primary_measure} by payment behavior",
                "x": payment_column,
                "y": primary_measure,
                "aggregation": "sum",
                "story_role": "behavior",
                "angle": "payment_behavior",
                "rationale": "Payment behavior can reveal channel preferences and checkout risk.",
            }
        )

    if stock_measure and (category_column or brand_column):
        specs.append(
            {
                "chart_type": "bar",
                "title": f"Average {stock_measure} by {category_column or brand_column}",
                "x": category_column or brand_column,
                "y": stock_measure,
                "aggregation": "mean",
                "story_role": "risk",
                "angle": "inventory_health",
                "rationale": "Inventory health highlights categories that may be overstocked or constrained.",
            }
        )

    if rating_measure and (category_column or brand_column):
        specs.append(
            {
                "chart_type": "bar",
                "title": f"Average {rating_measure} by {category_column or brand_column}",
                "x": category_column or brand_column,
                "y": rating_measure,
                "aggregation": "mean",
                "story_role": "opportunity",
                "angle": "review_quality",
                "rationale": "Review quality views connect customer sentiment to product segments.",
            }
        )

    margin_measure = _first_existing(["gross_margin_pct", "cost_per_unit", "avg_revenue_per_unit"], numeric_columns)
    if categorical_columns and margin_measure and margin_measure != primary_measure:
        specs.append(
            {
                "chart_type": "bar",
                "title": f"Average {margin_measure} by {categorical_columns[0]}",
                "x": categorical_columns[0],
                "y": margin_measure,
                "aggregation": "mean",
                "story_role": "efficiency",
                "angle": "profitability",
                "rationale": "Efficiency and margin measures need average comparisons.",
            }
        )

    scatter_columns = _preferred_business_measures(numeric_columns)
    if len(scatter_columns) >= 2:
        specs.append(
            {
                "chart_type": "scatter",
                "title": f"{scatter_columns[0]} vs {scatter_columns[1]}",
                "x": scatter_columns[0],
                "y": scatter_columns[1],
                "aggregation": "none",
                "story_role": "relationship",
                "angle": "relationship_diagnostics",
                "rationale": "Scatter plots expose metric relationships and outliers.",
            }
        )

    if numeric_columns:
        specs.append(
            {
                "chart_type": "histogram",
                "title": f"{numeric_columns[0]} distribution",
                "x": numeric_columns[0],
                "aggregation": "none",
                "story_role": "distribution",
                "angle": "distribution",
                "rationale": "Distribution views surface skew and outliers.",
            }
        )

    if len(numeric_columns) >= 3:
        specs.append(
            {
                "chart_type": "heatmap",
                "title": "Metric correlation heatmap",
                "columns": numeric_columns[:8],
                "aggregation": "correlation",
                "story_role": "drivers",
                "angle": "relationship_diagnostics",
                "rationale": "Correlation heatmaps summarize how measures move together.",
            }
        )

    return diversify_visualizations(dedupe_visualizations(specs), story_arc=story_arc, limit=5)


def validate_visualizations(frame: pd.DataFrame, specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    for spec in specs:
        chart_type = str(spec.get("chart_type", "")).lower()
        if chart_type not in SUPPORTED_CHART_TYPES:
            continue

        normalized = dict(spec)
        normalized["chart_type"] = chart_type
        normalized["aggregation"] = str(spec.get("aggregation", "sum")).lower()
        normalized["story_role"] = str(spec.get("story_role", chart_type))
        normalized["angle"] = str(spec.get("angle", "general"))

        if chart_type == "heatmap":
            columns = [column for column in spec.get("columns", []) if column in frame.columns]
            if len(columns) >= 2:
                normalized["columns"] = columns
                valid.append(normalized)
            continue

        x = spec.get("x")
        y = spec.get("y")
        if chart_type == "histogram" and x in frame.columns:
            valid.append(normalized)
        elif chart_type in {"bar", "line", "scatter"} and x in frame.columns and y in frame.columns:
            valid.append(normalized)

    return diversify_visualizations(dedupe_visualizations(valid), limit=6)


def diversify_visualizations(
    specs: list[dict[str, Any]],
    story_arc: list[str] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    if not specs:
        return []

    selected: list[dict[str, Any]] = []
    used_types: set[str] = set()
    used_angles: set[str] = set()
    story_arc = story_arc or [
        "trend",
        "driver",
        "segment_compare",
        "behavior",
        "risk",
        "opportunity",
        "efficiency",
        "relationship",
        "distribution",
        "drivers",
    ]

    for role in story_arc:
        for spec in specs:
            if spec in selected:
                continue
            if spec.get("story_role") == role:
                selected.append(spec)
                used_types.add(spec.get("chart_type", ""))
                used_angles.add(spec.get("angle", ""))
                break
        if len(selected) >= limit:
            return selected

    for spec in specs:
        if spec in selected:
            continue
        chart_type = spec.get("chart_type", "")
        angle = spec.get("angle", "")
        if chart_type in used_types and angle in used_angles and len(selected) >= 3:
            continue
        selected.append(spec)
        used_types.add(chart_type)
        used_angles.add(angle)
        if len(selected) >= limit:
            break

    for spec in specs:
        if len(selected) >= limit:
            break
        if spec not in selected:
            selected.append(spec)

    return selected[:limit]


def dedupe_visualizations(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    unique: list[dict[str, Any]] = []
    for spec in specs:
        key = (
            spec.get("chart_type"),
            spec.get("x"),
            spec.get("y"),
            tuple(spec.get("columns", [])),
            spec.get("aggregation"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(spec)
    return unique


def _first_existing(candidates: list[str], fallback: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in fallback:
            return candidate
    return fallback[0] if fallback else None


def _first_present(columns: list[str], candidates: list[str]) -> str | None:
    columns_by_lower = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate in columns_by_lower:
            return columns_by_lower[candidate]
    return None


def _preferred_business_measures(columns: list[str]) -> list[str]:
    priority_tokens = (
        "revenue",
        "amount",
        "total",
        "profit",
        "margin",
        "price",
        "quantity",
        "rating",
        "stock",
        "cost",
        "unit",
    )
    preferred = [
        column
        for column in columns
        if any(token in column.lower() for token in priority_tokens)
    ]
    remaining = [column for column in columns if column not in preferred]
    return preferred + remaining


def _looks_like_identifier(column: str) -> bool:
    lowered = column.lower()
    return lowered == "id" or lowered.endswith("_id") or lowered.endswith("id")


def _available_angles(frame: pd.DataFrame) -> list[str]:
    columns = {column.lower() for column in frame.columns}
    angles = []
    if any("revenue" in column or "amount" in column for column in columns):
        angles.append("revenue_growth")
    if any("customer" in column for column in columns):
        angles.append("customer_behavior")
    if any("product" in column or "category" in column or "brand" in column for column in columns):
        angles.append("product_mix")
    if any("stock" in column or "inventory" in column for column in columns):
        angles.append("inventory_health")
    if any("rating" in column or "review" in column for column in columns):
        angles.append("review_quality")
    if any("payment" in column for column in columns):
        angles.append("payment_behavior")
    if any("country" in column or "region" in column or "city" in column for column in columns):
        angles.append("geography")
    return angles or ["relationship_diagnostics"]


def _story_arc(available_angles: list[str]) -> list[str]:
    if "customer_behavior" in available_angles:
        return ["trend", "driver", "segment_compare", "behavior", "risk", "opportunity", "relationship", "distribution", "drivers"]
    if "inventory_health" in available_angles:
        return ["segment_compare", "driver", "risk", "efficiency", "drivers", "distribution", "relationship"]
    return ["trend", "driver", "segment_compare", "behavior", "risk", "opportunity", "efficiency", "relationship", "distribution", "drivers"]


def _category_angle(column: str) -> str:
    lowered = column.lower()
    if "customer" in lowered:
        return "customer_behavior"
    if "product" in lowered or "category" in lowered or "brand" in lowered:
        return "product_mix"
    if "payment" in lowered:
        return "payment_behavior"
    if "country" in lowered or "region" in lowered:
        return "geography"
    return "segment_performance"
