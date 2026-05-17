from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from axiom.profiling import ProfileResult


@dataclass(frozen=True)
class SemanticModel:
    analysis_frame: pd.DataFrame
    manifesto: dict[str, Any]
    tables: dict[str, pd.DataFrame]
    relationships: list[dict[str, Any]]
    derived_measures: list[dict[str, Any]]


def build_semantic_model(profiles: dict[str, ProfileResult]) -> SemanticModel:
    tables = {name: profile.cleaned_frame.copy() for name, profile in profiles.items()}
    relationships = infer_relationships(tables)
    analysis_frame = build_analysis_frame(tables, relationships)
    derived_measures = add_derived_measures(analysis_frame)
    manifesto = build_combined_manifesto(profiles, relationships, derived_measures, analysis_frame)

    return SemanticModel(
        analysis_frame=analysis_frame,
        manifesto=manifesto,
        tables=tables,
        relationships=relationships,
        derived_measures=derived_measures,
    )


def infer_relationships(tables: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    relationships: list[dict[str, Any]] = []
    names = list(tables)

    for left_index, left_name in enumerate(names):
        for right_name in names[left_index + 1 :]:
            left = tables[left_name]
            right = tables[right_name]
            common_columns = sorted(set(left.columns) & set(right.columns))

            for column in common_columns:
                left_unique = left[column].dropna().is_unique
                right_unique = right[column].dropna().is_unique
                overlap = _overlap_ratio(left[column], right[column])
                if overlap == 0:
                    continue
                if not _looks_like_key(column) and not ((left_unique or right_unique) and overlap >= 0.5):
                    continue

                relationship = {
                    "left_table": left_name,
                    "right_table": right_name,
                    "left_column": column,
                    "right_column": column,
                    "overlap_ratio": round(overlap, 4),
                    "relationship_type": _relationship_type(left_unique, right_unique),
                }
                relationships.append(relationship)

    return relationships


def build_analysis_frame(tables: dict[str, pd.DataFrame], relationships: list[dict[str, Any]]) -> pd.DataFrame:
    if not tables:
        return pd.DataFrame()

    base_name = _select_base_table(tables)
    analysis = tables[base_name].copy()
    used_tables = {base_name}

    for relationship in relationships:
        left_name = relationship["left_table"]
        right_name = relationship["right_table"]
        left_column = relationship["left_column"]
        right_column = relationship["right_column"]

        if left_name in used_tables and right_name not in used_tables and tables[right_name][right_column].dropna().is_unique:
            analysis = analysis.merge(
                tables[right_name],
                how="left",
                left_on=left_column,
                right_on=right_column,
                suffixes=("", f"_{right_name}"),
            )
            used_tables.add(right_name)
        elif right_name in used_tables and left_name not in used_tables and tables[left_name][left_column].dropna().is_unique:
            analysis = analysis.merge(
                tables[left_name],
                how="left",
                left_on=right_column,
                right_on=left_column,
                suffixes=("", f"_{left_name}"),
            )
            used_tables.add(left_name)

    analysis.attrs["base_table"] = base_name
    return analysis


def add_derived_measures(frame: pd.DataFrame) -> list[dict[str, Any]]:
    measures: list[dict[str, Any]] = []
    columns = set(frame.columns)

    if {"revenue", "cost"}.issubset(columns):
        frame["gross_profit"] = frame["revenue"] - frame["cost"]
        measures.append(
            {
                "name": "gross_profit",
                "formula": "revenue - cost",
                "description": "Revenue retained after cost.",
                "source": "inferred",
            }
        )

    if {"gross_profit", "revenue"}.issubset(frame.columns):
        frame["gross_margin_pct"] = _safe_divide(frame["gross_profit"], frame["revenue"])
        measures.append(
            {
                "name": "gross_margin_pct",
                "formula": "gross_profit / revenue",
                "description": "Gross profit as a share of revenue.",
                "source": "inferred",
            }
        )

    units_column = _first_existing(frame, ["units_sold", "quantity", "qty", "units"])
    if {"quantity", "unit_price"}.issubset(columns) and "line_item_revenue" not in frame.columns:
        frame["line_item_revenue"] = frame["quantity"] * frame["unit_price"]
        measures.append(
            {
                "name": "line_item_revenue",
                "formula": "quantity * unit_price",
                "description": "Revenue estimated at the order-line level.",
                "source": "inferred",
            }
        )

    if {"price", "stock_quantity"}.issubset(columns) and "inventory_value" not in frame.columns:
        frame["inventory_value"] = frame["price"] * frame["stock_quantity"]
        measures.append(
            {
                "name": "inventory_value",
                "formula": "price * stock_quantity",
                "description": "Estimated value of current stock on hand.",
                "source": "inferred",
            }
        )

    if units_column and "revenue" in frame.columns:
        frame["avg_revenue_per_unit"] = _safe_divide(frame["revenue"], frame[units_column])
        measures.append(
            {
                "name": "avg_revenue_per_unit",
                "formula": f"revenue / {units_column}",
                "description": "Average revenue earned per unit.",
                "source": "inferred",
            }
        )

    if units_column and "cost" in frame.columns:
        frame["cost_per_unit"] = _safe_divide(frame["cost"], frame[units_column])
        measures.append(
            {
                "name": "cost_per_unit",
                "formula": f"cost / {units_column}",
                "description": "Average cost per unit.",
                "source": "inferred",
            }
        )

    if {"revenue", "customer_id"}.issubset(frame.columns):
        frame["revenue_per_customer_record"] = frame["revenue"]
        measures.append(
            {
                "name": "revenue_per_customer_record",
                "formula": "revenue grouped by customer_id",
                "description": "Revenue available for customer-level aggregation.",
                "source": "inferred",
            }
        )

    return measures


def build_combined_manifesto(
    profiles: dict[str, ProfileResult],
    relationships: list[dict[str, Any]],
    derived_measures: list[dict[str, Any]],
    analysis_frame: pd.DataFrame,
) -> dict[str, Any]:
    if len(profiles) == 1:
        table_name, profile = next(iter(profiles.items()))
        manifesto = dict(profile.manifesto)
        manifesto["dataset_count"] = 1
        manifesto["tables"] = {table_name: profile.manifesto}
    else:
        manifesto = {
            "source": "multiple_files",
            "dataset_count": len(profiles),
            "row_count": int(sum(profile.manifesto.get("row_count", 0) for profile in profiles.values())),
            "analysis_row_count": int(len(analysis_frame)),
            "column_count": int(len(analysis_frame.columns)),
            "schema": _schema_from_frame(analysis_frame),
            "semantic_metadata": {},
            "anomaly_warnings": [],
            "tables": {name: profile.manifesto for name, profile in profiles.items()},
        }

        for name, profile in profiles.items():
            for column, hint in profile.manifesto.get("semantic_metadata", {}).items():
                manifesto["semantic_metadata"][f"{name}.{column}"] = hint
            manifesto["anomaly_warnings"].extend(profile.manifesto.get("anomaly_warnings", []))

    manifesto["relationships"] = relationships
    manifesto["derived_measures"] = derived_measures
    manifesto["analysis_base_table"] = analysis_frame.attrs.get("base_table")
    manifesto["row_count"] = int(sum(profile.manifesto.get("row_count", 0) for profile in profiles.values()))
    manifesto["analysis_row_count"] = int(len(analysis_frame))
    manifesto["column_count"] = int(len(analysis_frame.columns))
    manifesto["schema"] = _schema_from_frame(analysis_frame)
    return manifesto


def _schema_from_frame(frame: pd.DataFrame) -> list[dict[str, Any]]:
    schema = []
    for column in frame.columns:
        series = frame[column]
        schema.append(
            {
                "column": column,
                "type": _semantic_type(series),
                "pandas_dtype": str(series.dtype),
                "null_count": int(series.isna().sum()),
                "null_ratio": round(float(series.isna().sum() / max(len(series), 1)), 4),
                "unique_count": int(series.nunique(dropna=True)),
            }
        )
    return schema


def _select_base_table(tables: dict[str, pd.DataFrame]) -> str:
    def score(item: tuple[str, pd.DataFrame]) -> tuple[int, int, int]:
        _, frame = item
        numeric_count = len(frame.select_dtypes(include="number").columns)
        date_count = sum(pd.api.types.is_datetime64_any_dtype(frame[column]) for column in frame.columns)
        return (numeric_count, date_count, len(frame))

    return max(tables.items(), key=score)[0]


def _relationship_type(left_unique: bool, right_unique: bool) -> str:
    if left_unique and right_unique:
        return "one_to_one"
    if left_unique:
        return "one_to_many"
    if right_unique:
        return "many_to_one"
    return "many_to_many_candidate"


def _overlap_ratio(left: pd.Series, right: pd.Series) -> float:
    left_values = set(left.dropna().astype(str))
    right_values = set(right.dropna().astype(str))
    if not left_values or not right_values:
        return 0.0
    return len(left_values & right_values) / min(len(left_values), len(right_values))


def _looks_like_key(column: str) -> bool:
    lowered = column.lower()
    return lowered == "id" or lowered.endswith("_id") or lowered.endswith("id") or "key" in lowered


def _semantic_type(series: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if series.nunique(dropna=True) <= max(20, len(series) * 0.1):
        return "categorical"
    return "text"


def _first_existing(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    return None


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    clean_denominator = denominator.where(denominator != 0)
    return numerator / clean_denominator
