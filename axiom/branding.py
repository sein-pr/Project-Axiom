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
    "presentation_background": "#F4F7FB",
    "presentation_surface": "#FFFFFF",
    "presentation_text": "#111827",
}

BRAND_COLORS = {value.upper() for value in BRAND.values() if isinstance(value, str) and value.startswith("#")}


def read_brand_guideline(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    cleaned = hex_color.lstrip("#")
    return tuple(int(cleaned[index : index + 2], 16) for index in (0, 2, 4))


def normalize_theme(theme: dict | None) -> dict:
    theme = theme or {}
    default = {
        "name": "light_executive",
        "background": BRAND["presentation_background"],
        "surface": BRAND["presentation_surface"],
        "text": BRAND["presentation_text"],
        "muted_text": BRAND["border_gray"],
        "accent": BRAND["primary_blue"],
        "secondary_accent": BRAND["ai_purple"],
        "chart_palette": [
            BRAND["primary_blue"],
            BRAND["electric_blue"],
            BRAND["ai_purple"],
            BRAND["soft_cyan"],
            BRAND["deep_blue"],
        ],
    }

    normalized = dict(default)
    if isinstance(theme, dict):
        normalized["name"] = str(theme.get("name", default["name"]))
        for key in ("background", "surface", "text", "muted_text", "accent", "secondary_accent"):
            value = str(theme.get(key, default[key])).upper()
            if _is_hex_color(value):
                normalized[key] = value

        palette = theme.get("chart_palette")
        if isinstance(palette, list):
            clean_palette = [str(color).upper() for color in palette if _is_hex_color(str(color))]
            if clean_palette:
                normalized["chart_palette"] = clean_palette[:8]

    return normalized


def _is_hex_color(value: str) -> bool:
    value = value.strip()
    if len(value) != 7 or not value.startswith("#"):
        return False
    return all(character in "0123456789ABCDEFabcdef" for character in value[1:])
