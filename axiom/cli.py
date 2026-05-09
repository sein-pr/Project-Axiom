from __future__ import annotations

import argparse
import warnings
from pathlib import Path

from langchain_core._api.deprecation import LangChainPendingDeprecationWarning

warnings.filterwarnings("ignore", message=".*allowed_objects.*")
warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="axiom",
        description="Run the Project Axiom MVP BI pipeline on a CSV or Excel dataset.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Profile a dataset and write an analysis plan for approval.")
    add_common_run_arguments(plan_parser)

    run_parser = subparsers.add_parser("run", help="Profile, analyze, and render report artifacts.")
    add_common_run_arguments(run_parser)
    run_parser.add_argument(
        "--require-approval",
        action="store_true",
        help="Prompt for approval after writing the analysis plan.",
    )
    return parser


def add_common_run_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("input_path", type=Path, help="Path to a CSV, XLSX, or XLS file.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("axiom_output"),
        help="Directory where run artifacts are written.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run id. Defaults to a timestamped id.",
    )
    parser.add_argument(
        "--title",
        default="Project Axiom Analysis",
        help="Report/deck title.",
    )


def main() -> None:
    args = build_parser().parse_args()
    from axiom.pipeline import create_plan, run_pipeline

    if args.command == "plan":
        result = create_plan(
            input_path=args.input_path,
            output_dir=args.output_dir,
            run_id=args.run_id,
            title=args.title,
        )
        print(f"Axiom plan ready: {result.run_dir / 'analysis_plan.json'}")
        for question in result.analysis_plan["recommended_questions"]:
            print(f"- {question}")
    elif args.command == "run":
        approved = True
        if args.require_approval:
            plan_result = create_plan(
                input_path=args.input_path,
                output_dir=args.output_dir,
                run_id=args.run_id,
                title=args.title,
            )
            print(f"Axiom plan ready: {plan_result.run_dir / 'analysis_plan.json'}")
            for question in plan_result.analysis_plan["recommended_questions"]:
                print(f"- {question}")
            answer = input("Approve this analysis plan and render outputs? [y/N]: ").strip().lower()
            approved = answer in {"y", "yes"}
            if not approved:
                print("Run stopped before analysis. Review the plan and rerun when ready.")
                return
            args.run_id = plan_result.run_dir.name

        result = run_pipeline(
            input_path=args.input_path,
            output_dir=args.output_dir,
            run_id=args.run_id,
            title=args.title,
            approved=approved,
        )
        print(f"Axiom run complete: {result.run_dir}")
        for name, path in result.artifacts.items():
            print(f"- {name}: {path}")
        if result.audit:
            print(f"Audit status: {result.audit['status']}")


if __name__ == "__main__":
    main()
