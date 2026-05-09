# Project Axiom Tracker

## Current Status

Project Axiom now has a working local MVP pipeline. The project can ingest a CSV
or Excel file, profile the dataset, generate summary analysis, create charts, and
render starter PDF, PPTX, and Excel outputs.

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

- `data_manifesto.json`
- `summary_stats.json`
- `report.pdf`
- `slide_deck.pptx`
- `raw_data_dashboard.xlsx`
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
├── axiom/
│   ├── __init__.py
│   ├── analysis.py
│   ├── cli.py
│   ├── io.py
│   ├── pipeline.py
│   ├── profiling.py
│   └── rendering.py
├── sample_data/
│   └── sales_sample.csv
├── .gitignore
├── Axiom Logo.png
├── Project Axiom Updated Spec.md
├── README.md
├── PROJECT_TRACKER.md
└── pyproject.toml
```

## Next Milestones

1. Add LangGraph orchestration with stateful nodes:
   - Orchestrator
   - Data Engineer
   - Analyst
   - Auditor
   - Document Architect
2. Add a formal human-in-the-loop analysis plan checkpoint before heavy analysis.
3. Replace the local deterministic analysis path with a sandboxed ReAct-style
   analysis loop.
4. Add support for SQL sources through read-only DuckDB/database connections.
5. Improve PDF/PPTX branding with the Axiom logo and visual style.
6. Add automated tests for ingestion, profiling, analysis, and rendering.
7. Add richer anomaly detection and business metric inference.

## Notes

- Generated outputs are intentionally ignored by git through `axiom_output/`.
- Local secrets are ignored through `.env`.
- The current implementation is a strong local foundation, not yet the full
  autonomous multi-agent architecture described in the v2.0 spec.

