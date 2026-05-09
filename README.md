# Project Axiom

Project Axiom is an MVP autonomous BI engine. It ingests a CSV or Excel file,
profiles the dataset, generates a compact analysis bundle, and renders starter
business artifacts into `axiom_output/<run_id>/`.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
axiom run .\sample_data\sales_sample.csv
```

The first MVP creates:

- `data_manifesto.json` with schema, nulls, semantic hints, and anomaly warnings
- `summary_stats.json` with numeric/categorical summaries and correlations
- `report.pdf` with executive summary and charts
- `slide_deck.pptx` with one insight per slide
- `raw_data_dashboard.xlsx` with data, summaries, and charts
- `sandbox_logs/analysis_trace.py` containing the generated analysis trace

## Current MVP Scope

This version is intentionally local and deterministic. It creates the analytical
surface that the future LangGraph orchestrator and sandboxed ReAct loop will use.

Next milestones:

1. Add LangGraph state and nodes for orchestrator, data engineer, analyst, auditor,
   and document architect.
2. Replace local analysis execution with E2B or a locked-down Docker sandbox.
3. Add human-in-the-loop checkpoints before heavy analysis and final rendering.
4. Add SQL ingestion through read-only DuckDB connections.

