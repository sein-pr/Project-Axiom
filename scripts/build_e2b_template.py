from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from e2b import Template, default_build_logger


TEMPLATE_NAME = "axiom-bi-python"
PACKAGES = [
    "pandas>=2.2.0",
    "numpy",
    "duckdb>=1.0.0",
    "openpyxl>=3.1.2",
    "XlsxWriter>=3.2.0",
    "matplotlib>=3.8.0",
    "seaborn>=0.13.2",
    "statsmodels",
    "scipy",
    "plotly",
    "pyarrow",
    "polars",
]


def main() -> None:
    load_dotenv()
    enable_system_cert_store()
    if not os.getenv("E2B_API_KEY"):
        raise SystemExit("E2B_API_KEY is not set. Add it to .env, then rerun this script.")

    template = (
        Template()
        .from_base_image()
        .pip_install(PACKAGES)
        .run_cmd(
            "python - <<'PY'\n"
            "import duckdb, matplotlib, numpy, openpyxl, pandas, plotly, polars, scipy, seaborn, statsmodels, xlsxwriter\n"
            "print('axiom-bi-python dependencies ready')\n"
            "PY"
        )
    )

    build_info = Template.build(
        template,
        name=TEMPLATE_NAME,
        alias=TEMPLATE_NAME,
        cpu_count=2,
        memory_mb=4096,
        on_build_logs=default_build_logger(),
    )

    print(f"Template built: {build_info}")
    update_env_template_name(Path(".env"), TEMPLATE_NAME)


def update_env_template_name(path: Path, template_name: str) -> None:
    if not path.exists():
        return

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    updated = []
    found = False
    for line in lines:
        if line.strip().startswith("AXIOM_E2B_TEMPLATE="):
            updated.append(f"AXIOM_E2B_TEMPLATE={template_name}")
            found = True
        else:
            updated.append(line)

    if not found:
        updated.append(f"AXIOM_E2B_TEMPLATE={template_name}")

    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def enable_system_cert_store() -> None:
    value = os.getenv("AXIOM_USE_SYSTEM_CERTS", "true").strip().lower()
    if value not in {"1", "true", "yes", "y", "on"}:
        return
    try:
        import truststore
    except ImportError:
        return
    try:
        truststore.inject_into_ssl()
    except Exception:
        pass


if __name__ == "__main__":
    main()
