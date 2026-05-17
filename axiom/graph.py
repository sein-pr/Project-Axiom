from __future__ import annotations

import json
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core._api.deprecation import LangChainPendingDeprecationWarning

warnings.filterwarnings("ignore", message="The default value of `allowed_objects`.*")
warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)

from langgraph.graph import END, START, StateGraph

from axiom.branding import read_brand_guideline
from axiom.io import dataset_name, read_dataset_profile
from axiom.planning import create_analysis_plan, mark_plan_approved, materialize_additional_measures
from axiom.profiling import profile_dataset
from axiom.rendering import render_artifacts
from axiom.semantics import build_semantic_model
from axiom.self_healing import run_self_healing_analysis
from axiom.state import AxiomState
from axiom.visual_history import append_visual_history, compact_visual_history, load_visual_history


def build_axiom_graph():
    graph = StateGraph(AxiomState)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("data_engineer", data_engineer_node)
    graph.add_node("analysis_planner", analysis_planner_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("document_architect", document_architect_node)
    graph.add_node("auditor", auditor_node)

    graph.add_edge(START, "orchestrator")
    graph.add_edge("orchestrator", "data_engineer")
    graph.add_edge("data_engineer", "analysis_planner")
    graph.add_conditional_edges(
        "analysis_planner",
        approval_route,
        {
            "approved": "analyst",
            "awaiting_approval": END,
        },
    )
    graph.add_edge("analyst", "document_architect")
    graph.add_edge("document_architect", "auditor")
    graph.add_edge("auditor", END)
    return graph.compile()


def initial_state(
    input_paths: list[Path],
    output_dir: Path = Path("axiom_output"),
    run_id: str | None = None,
    title: str = "Project Axiom Analysis",
    approved: bool = True,
    use_llm: bool = True,
    logo_path: Path | None = None,
    brand_guideline_path: Path | None = None,
) -> AxiomState:
    run_name = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    return {
        "input_paths": [path.resolve() for path in input_paths],
        "output_dir": output_dir.resolve(),
        "run_id": run_name,
        "run_dir": output_dir.resolve() / run_name,
        "title": title,
        "approved": approved,
        "use_llm": use_llm,
        "logo_path": logo_path.resolve() if logo_path else Path("Axiom Logo.png").resolve(),
        "brand_guideline_path": brand_guideline_path.resolve()
        if brand_guideline_path
        else Path("axiom_brand_guideline.md").resolve(),
    }


def orchestrator_node(state: AxiomState) -> dict[str, Any]:
    run_dir = state["run_dir"]
    run_dir.mkdir(parents=True, exist_ok=True)
    return {
        "run_dir": run_dir,
        "brand_guideline": read_brand_guideline(state.get("brand_guideline_path")),
    }


def data_engineer_node(state: AxiomState) -> dict[str, Any]:
    raw_tables = {}
    profiles = {}
    for path in state["input_paths"]:
        name = dataset_name(path)
        frame, metadata = read_dataset_profile(path)
        raw_tables[name] = frame
        profiles[name] = profile_dataset(frame, source_name=path.name, source_metadata=metadata)
    semantic_model = build_semantic_model(profiles)
    return {
        "raw_frame": next(iter(raw_tables.values())),
        "raw_tables": raw_tables,
        "cleaned_tables": semantic_model.tables,
        "cleaned_frame": semantic_model.analysis_frame,
        "manifesto": semantic_model.manifesto,
        "relationships": semantic_model.relationships,
        "derived_measures": semantic_model.derived_measures,
    }


def analysis_planner_node(state: AxiomState) -> dict[str, Any]:
    plan = create_analysis_plan(
        state["manifesto"],
        state["title"],
        state["cleaned_frame"],
        state.get("derived_measures", []),
        brand_guideline=state.get("brand_guideline", ""),
        use_llm=state["use_llm"],
        visual_history=compact_visual_history(load_visual_history(state["output_dir"])),
    )
    cleaned_frame, manifesto, additional_measures = materialize_additional_measures(
        state["cleaned_frame"],
        state["manifesto"],
        plan.get("additional_measures_to_create", []),
    )
    if additional_measures:
        plan["additional_measures_to_create"] = additional_measures
        plan["derived_measures"] = manifesto.get("derived_measures", plan.get("derived_measures", []))

    if state["approved"]:
        plan = mark_plan_approved(plan)

    plan_path = state["run_dir"] / "analysis_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, default=str), encoding="utf-8")
    append_visual_history(state["output_dir"], state["run_id"], state["title"], plan)
    return {"analysis_plan": plan, "cleaned_frame": cleaned_frame, "manifesto": manifesto}


def approval_route(state: AxiomState) -> str:
    return "approved" if state["approved"] else "awaiting_approval"


def analyst_node(state: AxiomState) -> dict[str, Any]:
    result = run_self_healing_analysis(
        frame=state["cleaned_frame"],
        manifesto=state["manifesto"],
        analysis_plan=state["analysis_plan"],
        workspace=state["run_dir"] / "analyst_workspace",
        use_llm=state["use_llm"],
    )
    return {"analysis": result.analysis}


def document_architect_node(state: AxiomState) -> dict[str, Any]:
    artifacts = render_artifacts(
        state["cleaned_frame"],
        state["manifesto"],
        state["analysis"],
        state["analysis_plan"],
        state["run_dir"],
        state["title"],
        logo_path=state.get("logo_path"),
        brand_guideline=state.get("brand_guideline", ""),
    )
    artifacts["analysis_plan"] = state["run_dir"] / "analysis_plan.json"
    artifacts["analyst_workspace"] = state["run_dir"] / "analyst_workspace"
    return {"artifacts": artifacts}


def auditor_node(state: AxiomState) -> dict[str, Any]:
    artifacts = state.get("artifacts", {})
    missing = [name for name, path in artifacts.items() if not Path(path).exists()]

    summary_rows = state["analysis"].get("row_count")
    manifesto_rows = state["manifesto"].get("analysis_row_count", state["manifesto"].get("row_count"))
    row_counts_match = summary_rows == manifesto_rows

    audit = {
        "status": "passed" if not missing and row_counts_match else "failed",
        "missing_artifacts": missing,
        "checks": {
            "summary_rows_match_manifesto": row_counts_match,
            "artifact_count": len(artifacts),
        },
    }
    audit_path = state["run_dir"] / "audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")

    artifacts["audit"] = audit_path
    return {"audit": audit, "artifacts": artifacts}
