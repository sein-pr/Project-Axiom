from __future__ import annotations

from pathlib import Path


BRAND = {
    "name": "AXIOM",
    "product_name": "AXIOM Autonomous BI Engine",
    "tagline": "Insight. Automated. Intelligent.",
    "primary_blue": "#005BFF",
    "electric_blue": "#00A8FF",
    "ai_purple": "#6A3DFF",
    "soft_cyan": "#5EDCFF",
    "dark_navy": "#0B1020",
    "deep_blue": "#132B4F",
    "graphite": "#111827",
    "silver_white": "#F4F7FB",
    "soft_gray": "#C7D2E0",
    "border_gray": "#2D3748",
}


def read_brand_guideline(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    cleaned = hex_color.lstrip("#")
    return tuple(int(cleaned[index : index + 2], 16) for index in (0, 2, 4))

