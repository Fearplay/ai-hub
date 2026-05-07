"""EN + CS copy for the AI Study section."""

from __future__ import annotations


STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "nav_label": "AI Study",
        "title": "AI Study",
    },
    "cs": {
        "nav_label": "AI Studium",
        "title": "AI Studium",
    },
}


def s(lang: str) -> dict[str, str]:
    return STRINGS.get(lang) or STRINGS["en"]
