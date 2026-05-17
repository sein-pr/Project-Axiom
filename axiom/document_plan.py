from __future__ import annotations

from typing import Any

from axiom.branding import normalize_theme


REPORT_SECTION_TYPES = {
    "executive_summary",
    "kpi_summary",
    "chart_story",
    "data_model",
    "data_quality",
    "methodology",
    "self_healing",
}
SLIDE_TYPES = {
    "title",
    "executive_summary",
    "kpi",
    "chart",
    "data_model",
    "data_quality",
    "self_healing",
}


def deterministic_document_blueprint(
    title: str,
    manifesto: dict[str, Any],
    visualizations: list[dict[str, Any]],
) -> dict[str, Any]:
    sections = [
        {
            "type": "executive_summary",
            "title": "Executive Summary",
            "intent": "Summarize the most decision-ready insights.",
        }
    ]

    if manifesto.get("derived_measures"):
        sections.append(
            {
                "type": "kpi_summary",
                "title": "KPI Measures",
                "intent": "Explain inferred and created measures used in the analysis.",
            }
        )

    if visualizations:
        sections.append(
            {
                "type": "chart_story",
                "title": "Visual Analysis",
                "intent": "Walk through the recommended charts in a business sequence.",
                "chart_refs": list(range(min(len(visualizations), 5))),
            }
        )

    if manifesto.get("relationships"):
        sections.append(
            {
                "type": "data_model",
                "title": "Data Model",
                "intent": "Show how uploaded files relate to each other.",
            }
        )

    sections.extend(
        [
            {
                "type": "data_quality",
                "title": "Data Quality",
                "intent": "Highlight warnings, sampling, and chunk-processing context.",
            },
            {
                "type": "self_healing",
                "title": "Self-Healing Trace",
                "intent": "Document how the generated analyst code executed.",
            },
        ]
    )

    slides = [{"type": "title", "title": title}]
    slides.append({"type": "executive_summary", "title": "Executive Summary"})

    if manifesto.get("derived_measures"):
        slides.append({"type": "kpi", "title": "Inferred KPIs"})

    for index, visualization in enumerate(visualizations[:4]):
        slides.append(
            {
                "type": "chart",
                "title": visualization.get("title", f"Chart {index + 1}"),
                "chart_ref": index,
            }
        )

    if manifesto.get("relationships"):
        slides.append({"type": "data_model", "title": "Relationships"})

    slides.append({"type": "self_healing", "title": "Execution Trace"})

    return {
        "style": "executive_technical",
        "theme": normalize_theme(None),
        "report_sections": sections,
        "deck_slides": slides,
        "repair_notes": [],
    }


def normalize_document_blueprint(
    blueprint: dict[str, Any] | None,
    fallback: dict[str, Any],
    chart_count: int,
) -> dict[str, Any]:
    if not isinstance(blueprint, dict):
        repaired = dict(fallback)
        repaired["repair_notes"] = ["Missing or invalid blueprint; used deterministic fallback."]
        return repaired

    repair_notes: list[str] = []
    sections = []
    for section in blueprint.get("report_sections", []):
        if not isinstance(section, dict):
            repair_notes.append("Dropped non-object report section.")
            continue
        section_type = section.get("type")
        if section_type not in REPORT_SECTION_TYPES:
            repair_notes.append(f"Dropped unsupported report section type: {section_type}.")
            continue
        sections.append(_normalize_chart_refs(section, chart_count, one_based=_uses_one_based_refs(section.get("chart_refs", []), chart_count)))

    slides = []
    for slide in blueprint.get("deck_slides", []):
        if not isinstance(slide, dict):
            repair_notes.append("Dropped non-object slide.")
            continue
        slide_type = slide.get("type")
        if slide_type not in SLIDE_TYPES:
            repair_notes.append(f"Dropped unsupported slide type: {slide_type}.")
            continue
        slides.append(_normalize_chart_ref(slide, chart_count, one_based=_uses_one_based_refs([slide.get("chart_ref")], chart_count)))

    if not sections:
        repair_notes.append("No usable report sections; used fallback sections.")
        sections = fallback["report_sections"]
    if not slides:
        repair_notes.append("No usable deck slides; used fallback slides.")
        slides = fallback["deck_slides"]
    slides = _ensure_chart_story_slides(slides, fallback.get("deck_slides", []), chart_count, repair_notes)

    return {
        "style": str(blueprint.get("style", fallback.get("style", "executive_technical"))),
        "theme": normalize_theme(blueprint.get("theme", fallback.get("theme"))),
        "report_sections": sections[:8],
        "deck_slides": slides[:10],
        "repair_notes": repair_notes,
    }


def _normalize_chart_refs(section: dict[str, Any], chart_count: int, one_based: bool = False) -> dict[str, Any]:
    normalized = dict(section)
    refs = []
    for ref in section.get("chart_refs", []):
        normalized_ref = _normalize_ref(ref, chart_count, one_based=one_based)
        if normalized_ref is not None:
            refs.append(normalized_ref)
    normalized["chart_refs"] = refs
    normalized.setdefault("title", str(section.get("type", "Section")).replace("_", " ").title())
    return normalized


def _normalize_chart_ref(slide: dict[str, Any], chart_count: int, one_based: bool = False) -> dict[str, Any]:
    normalized = dict(slide)
    chart_ref = slide.get("chart_ref")
    normalized_ref = _normalize_ref(chart_ref, chart_count, one_based=one_based)
    if normalized_ref is None:
        normalized.pop("chart_ref", None)
    else:
        normalized["chart_ref"] = normalized_ref
    normalized.setdefault("title", str(slide.get("type", "Slide")).replace("_", " ").title())
    return normalized


def _ensure_chart_story_slides(
    slides: list[dict[str, Any]],
    fallback_slides: list[dict[str, Any]],
    chart_count: int,
    repair_notes: list[str],
) -> list[dict[str, Any]]:
    if chart_count == 0:
        return slides

    required_chart_slides = min(4, chart_count)
    existing_refs = {
        slide.get("chart_ref")
        for slide in slides
        if slide.get("type") == "chart" and isinstance(slide.get("chart_ref"), int)
    }
    current_chart_count = len(existing_refs)
    if current_chart_count >= min(2, required_chart_slides):
        return slides

    repaired = list(slides)
    for fallback_slide in fallback_slides:
        if current_chart_count >= required_chart_slides:
            break
        if fallback_slide.get("type") != "chart":
            continue
        chart_ref = fallback_slide.get("chart_ref")
        if not isinstance(chart_ref, int) or chart_ref in existing_refs or chart_ref >= chart_count:
            continue
        repaired.append(dict(fallback_slide))
        existing_refs.add(chart_ref)
        current_chart_count += 1

    if len(repaired) > len(slides):
        repair_notes.append("Added chart-story slides so the deck shows more of the recommended visual sequence.")
    return repaired


def _uses_one_based_refs(refs: list[Any], chart_count: int) -> bool:
    int_refs = [ref for ref in refs if isinstance(ref, int)]
    return bool(int_refs) and 0 not in int_refs and max(int_refs) <= chart_count


def _normalize_ref(ref: Any, chart_count: int, one_based: bool = False) -> int | None:
    if not isinstance(ref, int):
        return None
    candidate = ref - 1 if one_based else ref
    if 0 <= candidate < chart_count:
        return candidate
    return None
