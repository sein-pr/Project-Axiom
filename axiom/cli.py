from __future__ import annotations

import argparse
from pathlib import Path

from axiom.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="axiom",
        description="Run the Project Axiom MVP BI pipeline on a CSV or Excel dataset.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Profile, analyze, and render report artifacts.")
    run_parser.add_argument("input_path", type=Path, help="Path to a CSV, XLSX, or XLS file.")
    run_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("axiom_output"),
        help="Directory where run artifacts are written.",
    )
    run_parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run id. Defaults to a timestamped id.",
    )
    run_parser.add_argument(
        "--title",
        default="Project Axiom Analysis",
        help="Report/deck title.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "run":
        result = run_pipeline(
            input_path=args.input_path,
            output_dir=args.output_dir,
            run_id=args.run_id,
            title=args.title,
        )
        print(f"Axiom run complete: {result.run_dir}")
        for name, path in result.artifacts.items():
            print(f"- {name}: {path}")


if __name__ == "__main__":
    main()

