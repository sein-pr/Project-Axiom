from __future__ import annotations

from pathlib import Path
from typing import Any, NotRequired, TypedDict

import pandas as pd


class AxiomState(TypedDict):
    input_paths: list[Path]
    output_dir: Path
    run_id: str
    run_dir: Path
    title: str
    approved: bool
    use_llm: bool
    logo_path: NotRequired[Path]
    brand_guideline_path: NotRequired[Path]
    brand_guideline: NotRequired[str]
    raw_frame: NotRequired[pd.DataFrame]
    raw_tables: NotRequired[dict[str, pd.DataFrame]]
    cleaned_tables: NotRequired[dict[str, pd.DataFrame]]
    cleaned_frame: NotRequired[pd.DataFrame]
    manifesto: NotRequired[dict[str, Any]]
    relationships: NotRequired[list[dict[str, Any]]]
    derived_measures: NotRequired[list[dict[str, Any]]]
    analysis_plan: NotRequired[dict[str, Any]]
    analysis: NotRequired[dict[str, Any]]
    artifacts: NotRequired[dict[str, Path]]
    audit: NotRequired[dict[str, Any]]
