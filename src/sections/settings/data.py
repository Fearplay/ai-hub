"""Static metadata for the Settings UI (key rows, model dropdowns)."""

from __future__ import annotations

from src.qt.icons import Icons

from src.services import secrets


SECTION_ICON = Icons.SETTINGS_OUTLINED


def key_rows(txt: dict) -> list[dict]:
    """Definition of the API key rows shown in the Keys card."""
    return [
        {
            "name": secrets.OPENAI_API_KEY,
            "icon": Icons.AUTO_AWESOME,
            "label_key": "key_openai_label",
            "hint_key": "key_openai_hint",
            "label": txt["key_openai_label"],
            "hint": txt["key_openai_hint"],
            "color": "#10A37F",
        },
        {
            "name": secrets.ANTHROPIC_API_KEY,
            "icon": Icons.PSYCHOLOGY_OUTLINED,
            "label_key": "key_anthropic_label",
            "hint_key": "key_anthropic_hint",
            "label": txt["key_anthropic_label"],
            "hint": txt["key_anthropic_hint"],
            "color": "#D97706",
        },
        {
            "name": secrets.GITHUB_TOKEN,
            "icon": Icons.CODE,
            "label_key": "key_github_label",
            "hint_key": "key_github_hint",
            "label": txt["key_github_label"],
            "hint": txt["key_github_hint"],
            "color": "#3B82F6",
        },
    ]
