from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import warnings

import pandas as pd


@dataclass(frozen=True)
class ProfileResult:
    cleaned_frame: pd.DataFrame
    manifesto: dict[str, Any]


def profile_dataset(
    frame: pd.DataFrame,
    source_name: str,
    source_metadata: dict[str, Any] | None = None,
) -> ProfileResult:
    cleaned = frame.copy()
    cleaned.columns = [_normalize_column_name(column) for column in cleaned.columns]

    schema: list[dict[str, Any]] = []
    warnings: list[str] = []
    semantic_metadata: dict[str, str] = {}

    for column in cleaned.columns:
        series = cleaned[column]
        inferred_type = _infer_column_type(series)
        cleaned[column] = _cast_series(series, inferred_type)
        casted = cleaned[column]

        null_count = int(casted.isna().sum())
        null_ratio = float(null_count / max(len(casted), 1))
        unique_count = int(casted.nunique(dropna=True))

        if null_ratio > 0.3:
            warnings.append(f"{column} has {null_ratio:.0%} missing values.")

        if inferred_type == "numeric":
            outlier_count = _count_iqr_outliers(casted)
            if outlier_count:
                warnings.append(f"{column} has {outlier_count} potential outliers by IQR.")

        semantic_hint = _semantic_hint(column)
        if semantic_hint:
            semantic_metadata[column] = semantic_hint

        schema.append(
            {
                "column": column,
                "type": inferred_type,
                "pandas_dtype": str(casted.dtype),
                "null_count": null_count,
                "null_ratio": round(null_ratio, 4),
                "unique_count": unique_count,
            }
        )

    metadata = source_metadata or {}
    total_rows = int(metadata.get("total_rows", len(cleaned)))
    manifesto = {
        "source": source_name,
        "row_count": total_rows,
        "profiled_row_count": int(len(cleaned)),
        "column_count": int(len(cleaned.columns)),
        "schema": schema,
        "semantic_metadata": semantic_metadata,
        "anomaly_warnings": warnings,
        "source_metadata": metadata,
    }
    return ProfileResult(cleaned_frame=cleaned, manifesto=manifesto)


def _normalize_column_name(column: object) -> str:
    name = str(column).strip().lower()
    normalized = "".join(character if character.isalnum() else "_" for character in name)
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_") or "unnamed_column"


def _infer_column_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    non_null = series.dropna()
    if non_null.empty:
        return "text"

    numeric = pd.to_numeric(non_null, errors="coerce")
    if numeric.notna().mean() >= 0.9:
        return "numeric"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        dates = pd.to_datetime(non_null, errors="coerce")
    if dates.notna().mean() >= 0.9:
        return "datetime"

    if non_null.nunique() <= max(20, len(non_null) * 0.1):
        return "categorical"

    return "text"


def _cast_series(series: pd.Series, inferred_type: str) -> pd.Series:
    if inferred_type == "numeric":
        return pd.to_numeric(series, errors="coerce")
    if inferred_type == "datetime":
        return pd.to_datetime(series, errors="coerce")
    if inferred_type == "boolean":
        return series.astype("boolean")
    return series.astype("string")


def _count_iqr_outliers(series: pd.Series) -> int:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if len(numeric) < 4:
        return 0
    q1 = numeric.quantile(0.25)
    q3 = numeric.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return 0
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return int(((numeric < lower) | (numeric > upper)).sum())


def _semantic_hint(column: str) -> str | None:
    lowered = column.lower()
    if any(token in lowered for token in ("revenue", "sales", "amount", "price", "cost", "profit")):
        return "Likely monetary value. Confirm currency with the user."
    if "date" in lowered or lowered.endswith("_at"):
        return "Likely date/time field."
    if any(token in lowered for token in ("customer", "client", "account")):
        return "Likely customer/account identifier or segment."
    if any(token in lowered for token in ("region", "country", "city", "state")):
        return "Likely geographic dimension."
    return None
