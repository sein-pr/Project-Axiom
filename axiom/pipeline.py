from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from axiom.analysis import analyze_dataset
from axiom.io import read_dataset
from axiom.profiling import profile_dataset
from axiom.rendering import render_artifacts


@dataclass(frozen=True)
class PipelineResult:
    run_dir: Path
    artifacts: dict[str, Path]


def run_pipeline(
    input_path: Path,
    output_dir: Path = Path("axiom_output"),
    run_id: str | None = None,
    title: str = "Project Axiom Analysis",
) -> PipelineResult:
    resolved_input = input_path.resolve()
    run_name = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_dir.resolve() / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    raw_frame = read_dataset(resolved_input)
    profile = profile_dataset(raw_frame, source_name=resolved_input.name)
    analysis = analyze_dataset(profile.cleaned_frame)
    artifacts = render_artifacts(profile.cleaned_frame, profile.manifesto, analysis, run_dir, title)

    return PipelineResult(run_dir=run_dir, artifacts=artifacts)

