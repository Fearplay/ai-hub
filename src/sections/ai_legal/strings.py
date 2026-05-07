"""EN + CS copy for the AI Legal section."""

from __future__ import annotations


STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "nav_label": "AI Legal assistant",
        "title": "AI Legal assistant",
    },
    "cs": {
        "nav_label": "AI Právní asistent",
        "title": "AI Právní asistent",
    },
}


def s(lang: str) -> dict[str, str]:
    return STRINGS.get(lang) or STRINGS["en"]
