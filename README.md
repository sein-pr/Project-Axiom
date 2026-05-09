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

For development and tests:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
```

To generate only the human-reviewable analysis plan:

```powershell
axiom plan .\sample_data\sales_sample.csv
```

By default, planning uses Groq when a key is present in `.env`. To force the
deterministic fallback:

```powershell
axiom plan .\sample_data\sales_sample.csv --no-llm
```

To force an approval checkpoint before rendering outputs:

```powershell
axiom run .\sample_data\sales_sample.csv --require-approval
```

The MVP creates:

- `analysis_plan.json` with recommended questions and planned outputs
- `data_manifesto.json` with schema, nulls, semantic hints, and anomaly warnings
- `summary_stats.json` with numeric/categorical summaries and correlations
- `report.pdf` with executive summary and charts
- `slide_deck.pptx` with one insight per slide
- `raw_data_dashboard.xlsx` with data, summaries, and charts
- `audit.json` with basic cross-checks
- `sandbox_logs/analysis_trace.py` containing the generated analysis trace

## Current MVP Scope

This version uses LangGraph to orchestrate deterministic local nodes:

- Orchestrator
- Data Engineer
- Analysis Planner
- Analyst
- Document Architect
- Auditor

It creates the analytical surface that the future sandboxed ReAct loop will use.

Next milestones:

1. Replace local analysis execution with E2B or a locked-down Docker sandbox.
2. Add stronger auditor checks for KPI consistency across generated files.
3. Add SQL ingestion through read-only DuckDB connections.
4. Add optional LLM-backed planning and narrative generation.

## Environment

Copy `.env.example` to `.env` and fill in local secrets as needed. `.env` is
ignored by git.

Supported Groq settings:

- `GROQ_API_KEY`
- `groq_api_key_1`
- `groq_api_key_2`
- `AXIOM_GROQ_MODEL`, defaulting to `llama-3.3-70b-versatile`

## Branding

Generated PDF, PPTX, chart, and Excel outputs use the AXIOM logo and brand colors
from `sample_data/axiom_brand_guideline.md`:

- dark enterprise backgrounds
- electric blue and AI purple highlights
- professional AXIOM naming and tagline
- logo placement in reports and slide decks
