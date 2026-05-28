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
        # Side panel - activity / recent runs
        "activity_title": "Activity",
        "activity_subtitle": "Your most recent runs",
        "activity_empty": "No saved runs yet. Run any module to see it here.",
        # Side panel - session cost
        "cost_title": "Session cost",
        "cost_calls": "API calls",
        "cost_tokens_in": "Input tokens",
        "cost_tokens_out": "Output tokens",
        "cost_total": "Total cost",
        # Side panel - quick actions
        "quick_actions_title": "Quick actions",
        "qa_last_run": "Continue last run",
        "qa_outputs": "Open outputs folder",
        "qa_settings": "Settings",
        # Relative time
        "time_just_now": "just now",
        "time_min_ago": "{n} min ago",
        "time_hours_ago": "{n} h ago",
        "time_days_ago": "{n} d ago",
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
        # Side panel - activity / recent runs
        "activity_title": "Aktivita",
        "activity_subtitle": "Tvoje poslední běhy",
        "activity_empty": "Zatím žádné uložené běhy. Spusť libovolný modul a uvidíš ho tady.",
        # Side panel - session cost
        "cost_title": "Náklady relace",
        "cost_calls": "API volání",
        "cost_tokens_in": "Vstupní tokeny",
        "cost_tokens_out": "Výstupní tokeny",
        "cost_total": "Celková cena",
        # Side panel - quick actions
        "quick_actions_title": "Rychlé akce",
        "qa_last_run": "Pokračovat v posledním běhu",
        "qa_outputs": "Otevřít složku výstupů",
        "qa_settings": "Nastavení",
        # Relative time
        "time_just_now": "právě teď",
        "time_min_ago": "před {n} min",
        "time_hours_ago": "před {n} h",
        "time_days_ago": "před {n} dny",
    },
}


def s(lang: str) -> dict[str, str]:
    return STRINGS.get(lang) or STRINGS["en"]
