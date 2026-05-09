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
- Added Groq-backed analysis planning with deterministic fallback.
- Added AXIOM branding helpers and applied brand colors/logo to generated PDF,
  PPTX, charts, and Excel outputs.
- Added automated tests for profiling, analysis, plan-only graph execution, and
  full artifact generation.

## Verification

The MVP was installed successfully in `.venv` using:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

The sample pipeline was tested successfully using:

```powershell
.\.venv\Scripts\axiom.exe run .\sample_data\sales_sample.csv --run-id smoke_test --title "Axiom Sales Sample"
```

The automated test suite was tested successfully using:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Result:

```text
4 passed
```

Groq-backed planning was tested successfully using:

```powershell
.\.venv\Scripts\axiom.exe plan .\sample_data\sales_sample.csv --run-id groq_plan_smoke --title "Axiom Sales Sample"
```

Result:

```text
Planner source: groq
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
|   |-- branding.py
|   |-- cli.py
|   |-- graph.py
|   |-- io.py
|   |-- llm.py
|   |-- pipeline.py
|   |-- planning.py
|   |-- profiling.py
|   |-- rendering.py
|   `-- state.py
|-- sample_data/
|   |-- axiom_brand_guideline.md
|   `-- sales_sample.csv
|-- tests/
|   `-- test_pipeline.py
|-- .env.example
|-- .gitignore
|-- Axiom Logo.png
|-- Project Axiom Updated Spec.md
|-- README.md
|-- PROJECT_TRACKER.md
`-- pyproject.toml
```

## Next Milestones

1. Commit and push the Groq, branding, and tests milestone.
2. Replace the local deterministic analysis path with a sandboxed ReAct-style
   analysis loop.
3. Add support for SQL sources through read-only DuckDB/database connections.
4. Add richer anomaly detection and business metric inference.
5. Add stronger auditor checks for KPI consistency across generated files.

## Notes

- Generated outputs are intentionally ignored by git through `axiom_output/`.
- Local secrets are ignored through `.env`.
- The current implementation now has the graph architecture described in the
  v2.0 spec, but the analyst is still deterministic and local rather than a
  sandboxed self-correcting ReAct loop.
