"""EN + CS copy for the AI Documents section."""

from __future__ import annotations


STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "nav_label": "AI Documents",
        "title": "AI Documents",
    },
    "cs": {
        "nav_label": "AI Dokumenty",
        "title": "AI Dokumenty",
    },
}


def s(lang: str) -> dict[str, str]:
    return STRINGS.get(lang) or STRINGS["en"]
