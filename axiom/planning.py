from __future__ import annotations

import ast
from typing import Any

import pandas as pd

from axiom.document_plan import deterministic_document_blueprint, normalize_document_blueprint
from axiom.llm import GroqPlanner
from axiom.visualizations import deterministic_visualizations, validate_visualizations


def create_analysis_plan(
    manifesto: dict[str, Any],
    title: str,
    analysis_frame,
    derived_measures: list[dict[str, Any]],
    brand_guideline: str = "",
    use_llm: bool = True,
    visual_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    schema = manifesto.get("schema", [])
    numeric_columns = [column["column"] for column in schema if column.get("type") == "numeric"]
    categorical_columns = [column["column"] for column in schema if column.get("type") == "categorical"]
    datetime_columns = [column["column"] for column in schema if column.get("type") == "datetime"]

    questions = _analysis_questions(numeric_columns, categorical_columns, datetime_columns)
    questions.extend(_measure_questions(manifesto, categorical_columns, datetime_columns))
    visualizations = deterministic_visualizations(analysis_frame, derived_measures)
    fallback_blueprint = deterministic_document_blueprint(title, manifesto, visualizations)
    document_blueprint = fallback_blueprint
    render_targets = ["data_manifesto.json", "summary_stats.json", "report.pdf", "slide_deck.pptx", "raw_data_dashboard.xlsx"]
    data_quality_focus = manifesto.get("anomaly_warnings", [])
    planner_source = "deterministic"
    assumptions: list[str] = []
    additional_measures: list[dict[str, Any]] = []

    if use_llm:
        planner = GroqPlanner()
        llm_plan = planner.create_plan(
            manifesto=manifesto,
            title=title,
            deterministic_questions=questions,
            deterministic_visualizations=visualizations,
            derived_measures=derived_measures,
            brand_guideline=brand_guideline,
            visual_history=visual_history or [],
        )
        if llm_plan:
            questions = llm_plan["recommended_questions"] or questions
            data_quality_focus = llm_plan["data_quality_focus"] or data_quality_focus
            assumptions = llm_plan["business_context_assumptions"]
            additional_measures = _validate_additional_measures(
                llm_plan["additional_measures_to_create"],
                analysis_frame,
            )
            visualizations = validate_visualizations(
                analysis_frame,
                llm_plan["recommended_visualizations"] or visualizations,
            ) or visualizations
            fallback_blueprint = deterministic_document_blueprint(title, manifesto, visualizations)
            llm_blueprint = llm_plan.get("document_blueprint")
            if not llm_blueprint:
                draft_plan = {
                    "recommended_questions": questions,
                    "recommended_visualizations": visualizations,
                    "derived_measures": derived_measures,
                    "data_quality_focus": data_quality_focus,
                    "visual_diversity_policy": _visual_diversity_policy(manifesto),
                    "recent_visual_history": visual_history or [],
                }
                llm_blueprint = planner.create_document_blueprint(title, manifesto, draft_plan, brand_guideline)
            document_blueprint = normalize_document_blueprint(
                llm_blueprint,
                fallback_blueprint,
                chart_count=len(visualizations),
            )
            render_targets = llm_plan["planned_outputs"] or render_targets
            planner_source = planner.provider_name

    return {
        "title": title,
        "source": manifesto.get("source"),
        "row_count": manifesto.get("row_count"),
        "column_count": manifesto.get("column_count"),
        "recommended_questions": questions,
        "data_quality_focus": data_quality_focus,
        "business_context_assumptions": assumptions,
        "derived_measures": derived_measures,
        "additional_measures_to_create": additional_measures,
        "recommended_visualizations": visualizations,
        "visual_diversity_policy": _visual_diversity_policy(manifesto),
        "recent_visual_history": visual_history or [],
        "document_blueprint": document_blueprint,
        "planned_outputs": render_targets,
        "planner_source": planner_source,
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


def _measure_questions(
    manifesto: dict[str, Any],
    categorical_columns: list[str],
    datetime_columns: list[str],
) -> list[str]:
    questions: list[str] = []
    measure_names = [measure["name"] for measure in manifesto.get("derived_measures", [])]

    if "gross_profit" in measure_names and categorical_columns:
        questions.append(f"Which {categorical_columns[0]} contributes the most gross profit?")

    if "gross_margin_pct" in measure_names and categorical_columns:
        questions.append(f"Which {categorical_columns[0]} has the strongest gross margin percentage?")

    if "avg_revenue_per_unit" in measure_names and categorical_columns:
        questions.append(f"Where is average revenue per unit strongest across {categorical_columns[0]}?")

    if datetime_columns and "gross_margin_pct" in measure_names:
        questions.append(f"Is gross margin percentage improving or declining over {datetime_columns[0]}?")

    for relationship in manifesto.get("relationships", [])[:2]:
        right_table = relationship.get("right_table")
        right_column = relationship.get("right_column")
        questions.append(f"What extra business context does {right_table}.{right_column} add to the analysis?")

    return questions[:5]


def _visual_diversity_policy(manifesto: dict[str, Any]) -> dict[str, Any]:
    columns = {item.get("column", "").lower() for item in manifesto.get("schema", [])}
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
    if any("country" in column or "region" in column for column in columns):
        angles.append("geography")

    return {
        "goal": "Tell a coherent story and avoid repeating the same chart set.",
        "available_angles": angles or ["relationship_diagnostics"],
        "preferred_story_sequence": ["context", "driver", "segment_compare", "behavior", "risk_or_opportunity"],
    }


def _validate_additional_measures(
    measures: list[dict[str, Any]],
    analysis_frame,
) -> list[dict[str, Any]]:
    numeric_columns = set(analysis_frame.select_dtypes(include="number").columns)
    valid: list[dict[str, Any]] = []

    for measure in measures:
        formula = str(measure.get("formula", ""))
        referenced_names = _formula_names(formula)
        if not referenced_names or not referenced_names.issubset(numeric_columns):
            continue

        clean_measure = {
            "name": str(measure.get("name", "")).strip(),
            "formula": formula,
            "description": str(measure.get("description", "")).strip(),
            "source": "llm_proposed",
            "status": "validated_formula_ready",
        }
        if clean_measure["name"]:
            valid.append(clean_measure)

    return valid[:6]


def _formula_names(formula: str) -> set[str]:
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError:
        return set()

    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Name,
        ast.Load,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.Mod,
        ast.USub,
        ast.Constant,
    )
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, allowed_nodes):
            return set()
        if isinstance(node, ast.Name):
            names.add(node.id)
    return names


def materialize_additional_measures(
    frame: pd.DataFrame,
    manifesto: dict[str, Any],
    measures: list[dict[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any], list[dict[str, Any]]]:
    if not measures:
        return frame, manifesto, measures

    enriched = frame.copy()
    updated_measures: list[dict[str, Any]] = []
    for measure in measures:
        name = str(measure["name"])
        formula = str(measure["formula"])
        if name in enriched.columns:
            continue
        try:
            enriched[name] = _evaluate_formula(enriched, formula)
        except Exception:
            failed = dict(measure)
            failed["status"] = "formula_execution_failed"
            updated_measures.append(failed)
            continue

        executed = dict(measure)
        executed["status"] = "created"
        updated_measures.append(executed)

    updated_manifesto = dict(manifesto)
    derived_measures = list(updated_manifesto.get("derived_measures", []))
    derived_measures.extend(measure for measure in updated_measures if measure.get("status") == "created")
    updated_manifesto["derived_measures"] = derived_measures
    updated_manifesto["schema"] = _update_schema(updated_manifesto.get("schema", []), enriched)
    updated_manifesto["column_count"] = int(len(enriched.columns))

    return enriched, updated_manifesto, updated_measures


def _evaluate_formula(frame: pd.DataFrame, formula: str) -> pd.Series:
    names = _formula_names(formula)
    local_dict = {name: frame[name] for name in names}
    return pd.eval(formula, local_dict=local_dict, engine="python")


def _update_schema(existing_schema: list[dict[str, Any]], frame: pd.DataFrame) -> list[dict[str, Any]]:
    by_column = {item["column"]: item for item in existing_schema}
    for column in frame.columns:
        if column in by_column:
            continue
        series = frame[column]
        by_column[column] = {
            "column": column,
            "type": "numeric" if pd.api.types.is_numeric_dtype(series) else "text",
            "pandas_dtype": str(series.dtype),
            "null_count": int(series.isna().sum()),
            "null_ratio": round(float(series.isna().sum() / max(len(series), 1)), 4),
            "unique_count": int(series.nunique(dropna=True)),
        }
    return list(by_column.values())
