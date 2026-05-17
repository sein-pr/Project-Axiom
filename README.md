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

You can pass multiple related files. Axiom will profile each file, infer likely
relationships, build an analysis table, and derive KPI measures where the column
patterns support it:

```powershell
axiom run .\sample_data\sales_sample.csv .\sample_data\product_catalog_sample.csv
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
- `analyst_workspace/` with generated analyst scripts, retry traces, and result JSON
- `sandbox_logs/analysis_trace.py` containing the generated analysis trace

The analysis plan can include:

- inferred relationships across files
- derived measures such as `gross_profit`, `gross_margin_pct`,
  `avg_revenue_per_unit`, and `cost_per_unit`
- Groq-proposed additional measures when the formula can be validated against
  numeric columns
- Groq-recommended visualizations such as bar, line, scatter, histogram, and
  heatmap charts
- a dynamic `document_blueprint` that controls report sections and slide order
- a visual diversity policy that uses recent run history to avoid repeating the
  same chart set across reruns
- LLM-selected presentation themes that stay within AXIOM brand colors while
  preferring lighter executive PowerPoint backgrounds

The renderer writes `document_blueprint.json` beside the generated artifacts. If
the LLM returns an invalid document structure, Axiom normalizes or repairs the
blueprint before rendering.

## Self-Healing Analyst

The Analyst node runs generated Python inside the run-specific
`axiom_output/<run_id>/analyst_workspace/` folder. Axiom core files are not
rewritten at runtime.

Each run writes:

- `analysis_input.csv`
- `manifesto.json`
- `analysis_plan.json`
- `attempt_1.py`, `attempt_2.py`, and later retry scripts when needed
- `attempt_<n>_error.txt` for failed attempts
- `final_analysis.py` when an attempt succeeds
- `result.json`
- `self_healing_trace.json`

If generated analyst code fails, Axiom captures the traceback, asks Groq to
repair only the temporary analyst script when LLM mode is enabled, validates the
repaired script, and retries. If all attempts fail, it falls back to the
deterministic analyzer so report generation can continue.

## Current MVP Scope

This version uses LangGraph to orchestrate local nodes:

- Orchestrator
- Data Engineer
- Analysis Planner
- Analyst
- Document Architect
- Auditor

The current self-healing analyst loop is local and workspace-scoped. A future
production version should run the generated analyst scripts in E2B or a
locked-down Docker sandbox.

Next milestones:

1. Move self-healing analyst execution into E2B or a locked-down Docker sandbox.
2. Add stronger auditor checks for KPI consistency across generated files.
3. Add SQL ingestion through read-only DuckDB connections.
4. Expand the KPI inference catalog for SaaS, finance, operations, and marketing data.

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
from `axiom_brand_guideline.md`:

- lighter executive PowerPoint backgrounds by default
- electric blue, AI purple, cyan, and deep blue highlights
- professional AXIOM naming and tagline
- logo placement in reports and slide decks
