from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from axiom.analysis import analyze_dataset
from axiom.pipeline import create_plan, run_pipeline
from axiom.profiling import profile_dataset


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = ROOT / "sample_data" / "sales_sample.csv"
LOGO = ROOT / "Axiom Logo.png"
BRAND_GUIDELINE = ROOT / "sample_data" / "axiom_brand_guideline.md"


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
    assert result.manifesto["schema"][1]["type"] == "numeric"


def test_analysis_generates_summary_and_insights() -> None:
    frame = pd.read_csv(SAMPLE_DATA)
    profile = profile_dataset(frame, source_name=SAMPLE_DATA.name)

    analysis = analyze_dataset(profile.cleaned_frame)

    assert analysis["row_count"] == 20
    assert "revenue" in analysis["numeric_columns"]
    assert analysis["insight_candidates"]


def test_plan_command_path_writes_analysis_plan(tmp_path: Path) -> None:
    result = create_plan(
        input_path=SAMPLE_DATA,
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
    assert not result.artifacts


def test_graph_run_creates_expected_artifacts(tmp_path: Path) -> None:
    result = run_pipeline(
        input_path=SAMPLE_DATA,
        output_dir=tmp_path,
        run_id="run_test",
        title="Run Test",
        use_llm=False,
        logo_path=LOGO,
        brand_guideline_path=BRAND_GUIDELINE,
    )

    expected = {"manifesto", "summary", "pdf", "pptx", "xlsx", "analysis_trace", "analysis_plan", "audit"}

    assert expected.issubset(result.artifacts)
    assert result.audit is not None
    assert result.audit["status"] == "passed"
    for path in result.artifacts.values():
        assert path.exists()

