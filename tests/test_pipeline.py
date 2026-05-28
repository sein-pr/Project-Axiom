from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from axiom.analysis import analyze_dataset
from axiom.pipeline import create_plan, run_pipeline
from axiom.profiling import profile_dataset
from axiom.self_healing import run_self_healing_analysis


ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "Axiom Logo.png"
BRAND_GUIDELINE = ROOT / "axiom_brand_guideline.md"


def test_profile_dataset_normalizes_schema() -> None:
    frame = pd.DataFrame(
        {
            "Sale Date": ["2026-01-01", "2026-01-02"],
            "Revenue ($)": ["100", "250"],
            "Region": ["North", "South"],
        }
    )

    result = profile_dataset(frame, source_name="inline.csv")

    assert list(result.cleaned_frame.columns) == ["sale_date", "revenue", "region"]
    assert result.manifesto["row_count"] == 2
    assert result.manifesto["profiled_row_count"] == 2
    assert result.manifesto["schema"][1]["type"] == "numeric"


def test_analysis_generates_summary_and_insights() -> None:
    frame = _sales_frame()
    profile = profile_dataset(frame, source_name="sales_sample.csv")

    analysis = analyze_dataset(profile.cleaned_frame)

    assert analysis["row_count"] == 3
    assert "revenue" in analysis["numeric_columns"]
    assert analysis["insight_candidates"]


def test_plan_command_path_writes_analysis_plan(tmp_path: Path) -> None:
    sample_data = tmp_path / "sales_sample.csv"
    _sales_frame().to_csv(sample_data, index=False)

    result = create_plan(
        input_path=sample_data,
        output_dir=tmp_path,
        run_id="plan_test",
        title="Plan Test",
        use_llm=False,
        logo_path=LOGO,
        brand_guideline_path=BRAND_GUIDELINE,
    )

    plan_path = result.run_dir / "analysis_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    assert plan["status"] == "awaiting_approval"
    assert plan["planner_source"] == "deterministic"
    assert plan["recommended_questions"]
    assert plan["document_blueprint"]["report_sections"]
    assert plan["document_blueprint"]["deck_slides"]
    assert not result.artifacts


def test_graph_run_creates_expected_artifacts(tmp_path: Path) -> None:
    sample_data = tmp_path / "sales_sample.csv"
    _sales_frame().to_csv(sample_data, index=False)

    result = run_pipeline(
        input_path=sample_data,
        output_dir=tmp_path,
        run_id="run_test",
        title="Run Test",
        use_llm=False,
        sandbox_backend="local",
        logo_path=LOGO,
        brand_guideline_path=BRAND_GUIDELINE,
    )

    expected = {"manifesto", "summary", "pdf", "pptx", "xlsx", "analysis_trace", "analysis_plan", "document_blueprint", "audit"}

    assert expected.issubset(result.artifacts)
    assert result.audit is not None
    assert result.audit["status"] == "passed"
    for path in result.artifacts.values():
        assert path.exists()

    blueprint = json.loads((result.run_dir / "document_blueprint.json").read_text(encoding="utf-8"))
    assert blueprint["report_sections"]
    assert blueprint["deck_slides"]


def test_multi_file_run_infers_relationships_and_kpis(tmp_path: Path) -> None:
    sales_path = tmp_path / "sales.csv"
    products_path = tmp_path / "products.csv"
    pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "product_id": [1, 2, 1],
            "revenue": [1000, 1400, 700],
            "cost": [600, 900, 300],
            "units_sold": [10, 14, 7],
        }
    ).to_csv(sales_path, index=False)
    pd.DataFrame(
        {
            "product_id": [1, 2],
            "product_name": ["Atlas", "Nova"],
            "category": ["Platform", "Insight"],
        }
    ).to_csv(products_path, index=False)

    result = run_pipeline(
        input_path=[sales_path, products_path],
        output_dir=tmp_path,
        run_id="multi_file_test",
        title="Multi File Test",
        use_llm=False,
        sandbox_backend="local",
        logo_path=LOGO,
        brand_guideline_path=BRAND_GUIDELINE,
    )

    plan = json.loads((result.run_dir / "analysis_plan.json").read_text(encoding="utf-8"))
    manifesto = json.loads((result.run_dir / "data_manifesto.json").read_text(encoding="utf-8"))

    assert manifesto["dataset_count"] == 2
    assert manifesto["analysis_row_count"] == 3
    assert manifesto["relationships"]
    assert {measure["name"] for measure in manifesto["derived_measures"]} >= {
        "gross_profit",
        "gross_margin_pct",
        "avg_revenue_per_unit",
        "cost_per_unit",
    }
    assert len({visual["chart_type"] for visual in plan["recommended_visualizations"]}) >= 2
    assert result.audit is not None
    assert result.audit["status"] == "passed"


def test_self_healing_analyst_recovers_from_broken_generated_code(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02"],
            "revenue": [1000, 1250],
            "cost": [600, 700],
        }
    )
    profile = profile_dataset(frame, source_name="broken.csv")
    manifesto = profile.manifesto
    plan = {
        "recommended_questions": ["What happened to revenue?"],
        "recommended_visualizations": [],
    }
    broken_code = 'raise KeyError("missing uploaded field")\n'

    result = run_self_healing_analysis(
        frame=profile.cleaned_frame,
        manifesto=manifesto,
        analysis_plan=plan,
        workspace=tmp_path / "analyst_workspace",
        use_llm=False,
        sandbox_backend="local",
        initial_code=broken_code,
    )

    assert not result.used_fallback
    assert len(result.attempts) == 2
    assert result.attempts[1]["backend"] == "local"
    assert result.attempts[0]["status"] == "failed"
    assert result.attempts[1]["status"] == "succeeded"
    assert result.analysis["row_count"] == 2
    assert (tmp_path / "analyst_workspace" / "attempt_1_error.txt").exists()
    assert (tmp_path / "analyst_workspace" / "final_analysis.py").exists()


def _sales_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "region": ["North", "South", "North"],
            "product": ["Atlas", "Nova", "Atlas"],
            "revenue": [1000, 1400, 700],
            "cost": [600, 900, 300],
            "units_sold": [10, 14, 7],
            "customer_segment": ["Enterprise", "SMB", "Enterprise"],
        }
    )
