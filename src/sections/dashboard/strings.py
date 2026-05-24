"""EN + CS copy for the Dashboard section."""

from __future__ import annotations


STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "nav_label": "Dashboard",
        "title": "Dashboard",
        "subtitle": "All your AI assistants in one place. Pick a module to get started.",
        "module_count_one": "AI module available",
        "module_count_other": "AI modules available",
        "modules_grid_title": "Your AI modules",
        "modules_grid_desc": "Click any card to jump straight into that assistant.",
        "open_btn": "Open",
        "empty_title": "No AI modules visible",
        "empty_desc": "Every section is hidden right now. Edit src/sections/<key>/section.py and flip hidden=False to bring one back.",
    },
    "cs": {
        "nav_label": "Dashboard",
        "title": "Dashboard",
        "subtitle": "Všichni tvoji AI asistenti na jednom místě. Vyber si modul a pojď na to.",
        "module_count_one": "AI modul k dispozici",
        "module_count_other": "AI modulů k dispozici",
        "modules_grid_title": "Tvoje AI moduly",
        "modules_grid_desc": "Klikni na kartu a přejdi rovnou do dané sekce.",
        "open_btn": "Otevřít",
        "empty_title": "Žádné AI moduly nejsou viditelné",
        "empty_desc": "Všechny sekce jsou teď schované. Otevři src/sections/<key>/section.py a nastav hidden=False, aby se některá vrátila zpět.",
    },
}


def s(lang: str) -> dict[str, str]:
    return STRINGS.get(lang) or STRINGS["en"]
