from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from fpdf import FPDF
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

from axiom.branding import BRAND, hex_to_rgb


def render_artifacts(
    frame: pd.DataFrame,
    manifesto: dict[str, Any],
    analysis: dict[str, Any],
    run_dir: Path,
    title: str,
    logo_path: Path | None = None,
    brand_guideline: str = "",
) -> dict[str, Path]:
    assets_dir = run_dir / "assets"
    logs_dir = run_dir / "sandbox_logs"
    assets_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    manifesto_path = run_dir / "data_manifesto.json"
    summary_path = run_dir / "summary_stats.json"
    manifesto_path.write_text(json.dumps(manifesto, indent=2, default=str), encoding="utf-8")
    summary_path.write_text(json.dumps(analysis, indent=2, default=str), encoding="utf-8")

    chart_paths = _create_charts(frame, analysis, assets_dir)
    report_path = _render_pdf(title, manifesto, analysis, chart_paths, run_dir / "report.pdf", logo_path)
    deck_path = _render_pptx(title, analysis, chart_paths, run_dir / "slide_deck.pptx", logo_path)
    workbook_path = _render_xlsx(frame, analysis, run_dir / "raw_data_dashboard.xlsx")
    trace_path = _write_trace(logs_dir / "analysis_trace.py")

    return {
        "manifesto": manifesto_path,
        "summary": summary_path,
        "pdf": report_path,
        "pptx": deck_path,
        "xlsx": workbook_path,
        "analysis_trace": trace_path,
    }


def _create_charts(frame: pd.DataFrame, analysis: dict[str, Any], assets_dir: Path) -> list[Path]:
    sns.set_theme(
        style="darkgrid",
        rc={
            "axes.facecolor": BRAND["graphite"],
            "figure.facecolor": BRAND["dark_navy"],
            "axes.edgecolor": BRAND["border_gray"],
            "axes.labelcolor": BRAND["silver_white"],
            "text.color": BRAND["silver_white"],
            "xtick.color": BRAND["soft_gray"],
            "ytick.color": BRAND["soft_gray"],
        },
    )
    chart_paths: list[Path] = []

    numeric_columns = analysis["numeric_columns"]
    categorical_columns = analysis["categorical_columns"]

    if numeric_columns:
        column = numeric_columns[0]
        path = assets_dir / f"{column}_distribution.png"
        plt.figure(figsize=(8, 4.5))
        sns.histplot(frame[column].dropna(), kde=True, color=BRAND["electric_blue"])
        plt.title(f"{column} distribution")
        plt.tight_layout()
        plt.savefig(path, dpi=180)
        plt.close()
        chart_paths.append(path)

    if categorical_columns:
        column = categorical_columns[0]
        values = frame[column].dropna().astype(str).value_counts().head(10)
        if not values.empty:
            path = assets_dir / f"{column}_top_categories.png"
            plt.figure(figsize=(8, 4.5))
            sns.barplot(x=values.values, y=values.index, orient="h", color=BRAND["primary_blue"])
            plt.title(f"Top {column} categories")
            plt.xlabel("Count")
            plt.ylabel(column)
            plt.tight_layout()
            plt.savefig(path, dpi=180)
            plt.close()
            chart_paths.append(path)

    if len(numeric_columns) >= 2:
        path = assets_dir / "correlation_heatmap.png"
        plt.figure(figsize=(7, 5.5))
        sns.heatmap(frame[numeric_columns].corr(numeric_only=True), annot=True, cmap="coolwarm", center=0)
        plt.title("Numeric correlation heatmap")
        plt.tight_layout()
        plt.savefig(path, dpi=180)
        plt.close()
        chart_paths.append(path)

    return chart_paths


def _render_pdf(
    title: str,
    manifesto: dict[str, Any],
    analysis: dict[str, Any],
    chart_paths: list[Path],
    output_path: Path,
    logo_path: Path | None,
) -> Path:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _pdf_background(pdf)
    _pdf_logo(pdf, logo_path)
    pdf.set_text_color(*hex_to_rgb(BRAND["silver_white"]))
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "AXIOM", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*hex_to_rgb(BRAND["soft_gray"]))
    pdf.cell(0, 6, BRAND["tagline"], new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*hex_to_rgb(BRAND["silver_white"]))
    pdf.multi_cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*hex_to_rgb(BRAND["soft_gray"]))
    pdf.multi_cell(
        0,
        7,
        f"Rows: {manifesto['row_count']} | Columns: {manifesto['column_count']}",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*hex_to_rgb(BRAND["electric_blue"]))
    pdf.cell(0, 9, "Executive Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*hex_to_rgb(BRAND["silver_white"]))
    for insight in analysis["insight_candidates"] or ["No insight candidates generated."]:
        pdf.multi_cell(0, 6, f"- {insight}", new_x="LMARGIN", new_y="NEXT")

    if manifesto["anomaly_warnings"]:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*hex_to_rgb(BRAND["electric_blue"]))
        pdf.cell(0, 9, "Data Quality Warnings", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*hex_to_rgb(BRAND["silver_white"]))
        for warning in manifesto["anomaly_warnings"]:
            pdf.multi_cell(0, 6, f"- {warning}", new_x="LMARGIN", new_y="NEXT")

    for chart_path in chart_paths:
        pdf.add_page()
        _pdf_background(pdf)
        _pdf_logo(pdf, logo_path)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*hex_to_rgb(BRAND["electric_blue"]))
        pdf.cell(0, 8, chart_path.stem.replace("_", " ").title(), new_x="LMARGIN", new_y="NEXT")
        pdf.image(str(chart_path), x=15, y=30, w=180)

    pdf.output(output_path)
    return output_path


def _render_pptx(
    title: str,
    analysis: dict[str, Any],
    chart_paths: list[Path],
    output_path: Path,
    logo_path: Path | None,
) -> Path:
    presentation = Presentation()
    title_slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    _style_slide_background(title_slide)
    _ppt_logo(title_slide, logo_path)
    title_box = title_slide.shapes.add_textbox(Inches(0.75), Inches(2.15), Inches(8.7), Inches(0.8))
    title_frame = title_box.text_frame
    title_frame.text = title
    title_frame.paragraphs[0].font.size = Pt(34)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = _ppt_color(BRAND["silver_white"])
    tagline_box = title_slide.shapes.add_textbox(Inches(0.78), Inches(3.05), Inches(6.6), Inches(0.4))
    tagline_frame = tagline_box.text_frame
    tagline_frame.text = BRAND["tagline"]
    tagline_frame.paragraphs[0].font.size = Pt(16)
    tagline_frame.paragraphs[0].font.color.rgb = _ppt_color(BRAND["soft_cyan"])

    for insight in analysis["insight_candidates"][:6]:
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        _style_slide_background(slide)
        _ppt_logo(slide, logo_path)
        heading = slide.shapes.add_textbox(Inches(0.75), Inches(0.45), Inches(8.0), Inches(0.5))
        heading.text_frame.text = "Insight"
        heading.text_frame.paragraphs[0].font.bold = True
        heading.text_frame.paragraphs[0].font.size = Pt(20)
        heading.text_frame.paragraphs[0].font.color.rgb = _ppt_color(BRAND["electric_blue"])
        text_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(8.4), Inches(1.3))
        text_frame = text_box.text_frame
        text_frame.text = insight
        text_frame.paragraphs[0].font.size = Pt(24)
        text_frame.paragraphs[0].font.color.rgb = _ppt_color(BRAND["silver_white"])

    for chart_path in chart_paths[:3]:
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        _style_slide_background(slide)
        _ppt_logo(slide, logo_path)
        heading = slide.shapes.add_textbox(Inches(0.75), Inches(0.45), Inches(8.0), Inches(0.5))
        heading.text_frame.text = chart_path.stem.replace("_", " ").title()
        heading.text_frame.paragraphs[0].font.bold = True
        heading.text_frame.paragraphs[0].font.size = Pt(20)
        heading.text_frame.paragraphs[0].font.color.rgb = _ppt_color(BRAND["electric_blue"])
        slide.shapes.add_picture(str(chart_path), Inches(0.8), Inches(1.25), width=Inches(8.4))

    presentation.save(output_path)
    return output_path


def _render_xlsx(frame: pd.DataFrame, analysis: dict[str, Any], output_path: Path) -> Path:
    with pd.ExcelWriter(output_path, engine="xlsxwriter", datetime_format="yyyy-mm-dd") as writer:
        frame.to_excel(writer, sheet_name="Clean Data", index=False)
        pd.DataFrame(analysis["numeric_summary"]).T.to_excel(writer, sheet_name="Numeric Summary")

        workbook = writer.book
        data_sheet = writer.sheets["Clean Data"]
        header_format = workbook.add_format(
            {
                "bold": True,
                "font_color": BRAND["silver_white"],
                "bg_color": BRAND["primary_blue"],
                "border": 1,
                "border_color": BRAND["border_gray"],
            }
        )
        for column_index, column in enumerate(frame.columns):
            data_sheet.write(0, column_index, column, header_format)
            data_sheet.set_column(column_index, column_index, min(max(len(column) + 2, 12), 28))

        if analysis["numeric_columns"]:
            first_numeric = analysis["numeric_columns"][0]
            column_index = frame.columns.get_loc(first_numeric)
            data_sheet.conditional_format(
                1,
                column_index,
                len(frame),
                column_index,
                {
                    "type": "3_color_scale",
                    "min_color": BRAND["deep_blue"],
                    "mid_color": BRAND["electric_blue"],
                    "max_color": BRAND["ai_purple"],
                },
            )

    return output_path


def _pdf_background(pdf: FPDF) -> None:
    pdf.set_fill_color(*hex_to_rgb(BRAND["dark_navy"]))
    pdf.rect(0, 0, 210, 297, style="F")
    pdf.set_draw_color(*hex_to_rgb(BRAND["primary_blue"]))
    pdf.set_line_width(0.8)
    pdf.line(15, 24, 195, 24)


def _pdf_logo(pdf: FPDF, logo_path: Path | None) -> None:
    if logo_path and logo_path.exists():
        pdf.image(str(logo_path), x=165, y=8, w=28)


def _style_slide_background(slide) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = _ppt_color(BRAND["dark_navy"])


def _ppt_logo(slide, logo_path: Path | None) -> None:
    if logo_path and logo_path.exists():
        slide.shapes.add_picture(str(logo_path), Inches(8.25), Inches(0.25), width=Inches(1.25))


def _ppt_color(hex_color: str) -> RGBColor:
    return RGBColor(*hex_to_rgb(hex_color))


def _write_trace(output_path: Path) -> Path:
    output_path.write_text(
        "\n".join(
            [
                "# Project Axiom MVP analysis trace",
                "# Future versions will store every sandbox command and observation here.",
                "profile_dataset(frame, source_name)",
                "analyze_dataset(cleaned_frame)",
                "render_artifacts(cleaned_frame, manifesto, analysis, run_dir, title)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return output_path
