from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from axiom.graph import build_axiom_graph, initial_state


@dataclass(frozen=True)
class PipelineResult:
    run_dir: Path
    artifacts: dict[str, Path]
    analysis_plan: dict
    audit: dict | None = None


def run_pipeline(
    input_path: Path,
    output_dir: Path = Path("axiom_output"),
    run_id: str | None = None,
    title: str = "Project Axiom Analysis",
    approved: bool = True,
) -> PipelineResult:
    graph = build_axiom_graph()
    result = graph.invoke(
        initial_state(
            input_path=input_path,
            output_dir=output_dir,
            run_id=run_id,
            title=title,
            approved=approved,
        )
    )

    return PipelineResult(
        run_dir=result["run_dir"],
        artifacts=result.get("artifacts", {}),
        analysis_plan=result["analysis_plan"],
        audit=result.get("audit"),
    )


def create_plan(
    input_path: Path,
    output_dir: Path = Path("axiom_output"),
    run_id: str | None = None,
    title: str = "Project Axiom Analysis",
) -> PipelineResult:
    return run_pipeline(
        input_path=input_path,
        output_dir=output_dir,
        run_id=run_id,
        title=title,
        approved=False,
    )
