"""EN + CS copy for the Dashboard section."""

from __future__ import annotations


STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "nav_label": "Dashboard",
        "title": "Dashboard",
    },
    "cs": {
        "nav_label": "Dashboard",
        "title": "Dashboard",
    },
}


def s(lang: str) -> dict[str, str]:
    return STRINGS.get(lang) or STRINGS["en"]
