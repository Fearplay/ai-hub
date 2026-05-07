"""EN + CS copy for the AI Business section."""

from __future__ import annotations


STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "nav_label": "AI Business",
        "title": "AI Business",
    },
    "cs": {
        "nav_label": "AI Podnikání",
        "title": "AI Podnikání",
    },
}


def s(lang: str) -> dict[str, str]:
    return STRINGS.get(lang) or STRINGS["en"]
