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

from axiom.analysis import analyze_dataset
from axiom.io import read_dataset
from axiom.planning import create_analysis_plan, mark_plan_approved
from axiom.profiling import profile_dataset
from axiom.rendering import render_artifacts
from axiom.state import AxiomState


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
    input_path: Path,
    output_dir: Path = Path("axiom_output"),
    run_id: str | None = None,
    title: str = "Project Axiom Analysis",
    approved: bool = True,
) -> AxiomState:
    run_name = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    return {
        "input_path": input_path.resolve(),
        "output_dir": output_dir.resolve(),
        "run_id": run_name,
        "run_dir": output_dir.resolve() / run_name,
        "title": title,
        "approved": approved,
    }


def orchestrator_node(state: AxiomState) -> dict[str, Any]:
    run_dir = state["run_dir"]
    run_dir.mkdir(parents=True, exist_ok=True)
    return {"run_dir": run_dir}


def data_engineer_node(state: AxiomState) -> dict[str, Any]:
    raw_frame = read_dataset(state["input_path"])
    profile = profile_dataset(raw_frame, source_name=state["input_path"].name)
    return {
        "raw_frame": raw_frame,
        "cleaned_frame": profile.cleaned_frame,
        "manifesto": profile.manifesto,
    }


def analysis_planner_node(state: AxiomState) -> dict[str, Any]:
    plan = create_analysis_plan(state["manifesto"], state["title"])
    if state["approved"]:
        plan = mark_plan_approved(plan)

    plan_path = state["run_dir"] / "analysis_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, default=str), encoding="utf-8")
    return {"analysis_plan": plan}


def approval_route(state: AxiomState) -> str:
    return "approved" if state["approved"] else "awaiting_approval"


def analyst_node(state: AxiomState) -> dict[str, Any]:
    analysis = analyze_dataset(state["cleaned_frame"])
    return {"analysis": analysis}


def document_architect_node(state: AxiomState) -> dict[str, Any]:
    artifacts = render_artifacts(
        state["cleaned_frame"],
        state["manifesto"],
        state["analysis"],
        state["run_dir"],
        state["title"],
    )
    artifacts["analysis_plan"] = state["run_dir"] / "analysis_plan.json"
    return {"artifacts": artifacts}


def auditor_node(state: AxiomState) -> dict[str, Any]:
    artifacts = state.get("artifacts", {})
    missing = [name for name, path in artifacts.items() if not Path(path).exists()]

    summary_rows = state["analysis"].get("row_count")
    manifesto_rows = state["manifesto"].get("row_count")
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
