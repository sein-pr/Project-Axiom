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
- Added multi-file ingestion through repeated CLI input paths.
- Added relationship inference across uploaded data files using shared keys and
  high-overlap unique dimensions.
- Added a semantic model layer that builds an analysis table from related files.
- Added KPI inference for common business measures:
  - `gross_profit`
  - `gross_margin_pct`
  - `avg_revenue_per_unit`
  - `cost_per_unit`
- Added LLM-recommended visualization specs with validation before rendering.
- Added support for validated LLM-proposed measures, which are materialized into
  the analysis frame before analysis.
- Added a self-healing analyst workspace that generates temporary analyst code,
  captures failures, repairs/retries generated scripts, and falls back to the
  deterministic analyzer if all attempts fail.
- Added dynamic document blueprints so the PDF/PPTX structure can vary by
  dataset, planner source, chart recommendations, and data model context.
- Added document blueprint normalization so unsupported sections, invalid chart
  references, and one-based chart references are repaired before rendering.
- Added a visual diversity policy with recent-run history in
  `axiom_output/_visual_history.json` so reruns can avoid repeating the same
  chart signatures.
- Added ecommerce-aware visual candidates for category mix, geography, payment
  behavior, inventory health, and review/rating views when matching columns are
  available.
- Added LLM-normalized presentation themes so PowerPoint decks can use lighter
  AXIOM-branded backgrounds and varied chart palettes.

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
5 passed
```

Groq-backed planning was tested successfully using:

```powershell
.\.venv\Scripts\axiom.exe plan .\sample_data\sales_sample.csv --run-id groq_plan_smoke --title "Axiom Sales Sample"
```

Result:

```text
Planner source: groq
```

The multi-file KPI and visualization workflow was tested successfully using:

```powershell
.\.venv\Scripts\axiom.exe run .\sample_data\sales_sample.csv .\sample_data\product_catalog_sample.csv --run-id groq_full_kpi_smoke --title "Axiom Multi File Sample"
```

Result:

```text
Audit status: passed
```

The self-healing analyst loop was tested with intentionally broken generated
code. The first attempt failed, the temporary analyst script was replaced, and
the second attempt completed successfully.

The full graph run was also tested with:

```powershell
.\.venv\Scripts\axiom.exe run .\sample_data\sales_sample.csv .\sample_data\product_catalog_sample.csv --run-id self_healing_smoke --title "Axiom Self Healing Smoke" --no-llm
```

Result:

```text
Audit status: passed
```

The run generated outputs in:

```text
axiom_output/smoke_test/
```

Expected files were produced:

- `analysis_plan.json`
- `document_blueprint.json`
- `data_manifesto.json`
- `summary_stats.json`
- `report.pdf`
- `slide_deck.pptx`
- `raw_data_dashboard.xlsx`
- `audit.json`
- `analyst_workspace/`
- chart PNG files under `assets/`
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
|   |-- document_plan.py
|   |-- graph.py
|   |-- io.py
|   |-- llm.py
|   |-- pipeline.py
|   |-- planning.py
|   |-- profiling.py
|   |-- rendering.py
|   |-- semantics.py
|   |-- self_healing.py
|   |-- state.py
|   |-- visual_history.py
|   `-- visualizations.py
|-- sample_data/
|   |-- customers.csv
|   |-- order_items.csv
|   |-- orders.csv
|   |-- product_reviews.csv
|   `-- products.csv
|-- tests/
|   `-- test_pipeline.py
|-- .env.example
|-- .gitignore
|-- Axiom Logo.png
|-- axiom_brand_guideline.md
|-- Project Axiom Updated Spec.md
|-- README.md
|-- PROJECT_TRACKER.md
`-- pyproject.toml
```

## Next Milestones

1. Move the self-healing analyst loop into E2B or a locked-down Docker sandbox.
2. Commit and push the self-healing, KPI, multi-file, visualization-planning,
   chunked-processing, dynamic-document, and visual-diversity work.
   milestone.
3. Add support for SQL sources through read-only DuckDB/database connections.
4. Add richer anomaly detection and domain-specific KPI catalogs.
5. Add stronger auditor checks for KPI consistency across generated files.

## Notes

- Generated outputs are intentionally ignored by git through `axiom_output/`.
- Local secrets are ignored through `.env`.
- The current implementation now has a workspace-scoped self-healing analyst
  loop. It repairs generated run scripts, not Axiom core source files.
