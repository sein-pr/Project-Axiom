# Project Axiom Tracker

## Current Status

Project Axiom now has a working LangGraph-orchestrated local MVP pipeline. The
project can ingest a CSV or Excel file, profile the dataset, generate an
approval-ready analysis plan, create summary analysis, create charts, and render
starter PDF, PPTX, and Excel outputs.

## Completed

- Read and interpreted `Project Axiom Updated Spec.md`.
- Inspected `Axiom Logo.png` to understand the project identity and branding.
- Created an installable Python package under `axiom/`.
- Added a command-line interface:

```powershell
axiom run <input-file>
```

- Added CSV and Excel ingestion support.
- Added dataset profiling:
  - normalized column names
  - inferred column types
  - null counts and ratios
  - unique counts
  - semantic hints
  - basic anomaly warnings
- Added analysis generation:
  - numeric summaries
  - categorical summaries
  - correlation matrix
  - initial insight candidates
- Added artifact rendering:
  - `data_manifesto.json`
  - `summary_stats.json`
  - `report.pdf`
  - `slide_deck.pptx`
  - `raw_data_dashboard.xlsx`
  - chart PNG assets
  - `sandbox_logs/analysis_trace.py`
- Added sample dataset:
  - `sample_data/sales_sample.csv`
- Added project setup documentation in `README.md`.
- Added `.gitignore` for local environments, generated outputs, caches, and secrets.
- Created and tested a local virtual environment.
- Added LangGraph state and nodes:
  - Orchestrator
  - Data Engineer
  - Analysis Planner
  - Analyst
  - Document Architect
  - Auditor
- Added `axiom plan <input-file>` for the human approval checkpoint.
- Added `axiom run <input-file> --require-approval` for interactive approval
  before rendering outputs.
- Added `analysis_plan.json` and `audit.json` outputs.
- Added `.env.example` with redacted configuration names.

## Verification

The MVP was installed successfully in `.venv` using:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

The sample pipeline was tested successfully using:

```powershell
.\.venv\Scripts\axiom.exe run .\sample_data\sales_sample.csv --run-id smoke_test --title "Axiom Sales Sample"
```

The run generated outputs in:

```text
axiom_output/smoke_test/
```

Expected files were produced:

- `analysis_plan.json`
- `data_manifesto.json`
- `summary_stats.json`
- `report.pdf`
- `slide_deck.pptx`
- `raw_data_dashboard.xlsx`
- `audit.json`
- `assets/revenue_distribution.png`
- `assets/region_top_categories.png`
- `assets/correlation_heatmap.png`
- `sandbox_logs/analysis_trace.py`

## Important Fixes Made During Build

- Fixed setuptools package discovery by explicitly including only `axiom*` in
  `pyproject.toml`.
- Fixed an `fpdf2` layout issue by resetting the PDF cursor after `multi_cell`
  calls.
- Suppressed noisy date-inference warnings during profiling probes.

## Current File Map

```text
Project Axiom/
|-- axiom/
|   |-- __init__.py
|   |-- analysis.py
|   |-- cli.py
|   |-- graph.py
|   |-- io.py
|   |-- pipeline.py
|   |-- planning.py
|   |-- profiling.py
|   |-- rendering.py
|   `-- state.py
|-- sample_data/
|   `-- sales_sample.csv
|-- .env.example
|-- .gitignore
|-- Axiom Logo.png
|-- Project Axiom Updated Spec.md
|-- README.md
|-- PROJECT_TRACKER.md
`-- pyproject.toml
```

## Next Milestones

1. Replace the local deterministic analysis path with a sandboxed ReAct-style
   analysis loop.
2. Add support for SQL sources through read-only DuckDB/database connections.
3. Improve PDF/PPTX branding with the Axiom logo and visual style.
4. Add automated tests for ingestion, profiling, graph nodes, analysis, and rendering.
5. Add richer anomaly detection and business metric inference.
6. Add optional LLM-backed planning/narrative generation using local `.env`
   configuration.

## Notes

- Generated outputs are intentionally ignored by git through `axiom_output/`.
- Local secrets are ignored through `.env`.
- The current implementation now has the graph architecture described in the
  v2.0 spec, but the analyst is still deterministic and local rather than a
  sandboxed self-correcting ReAct loop.
