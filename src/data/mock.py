"""Mock data využívaná v UI mockupu (žádné LLM, žádný backend)."""

from __future__ import annotations

import flet as ft


NAV_ITEMS = [
    {"key": "dashboard", "icon": ft.Icons.DASHBOARD_OUTLINED, "label": "Dashboard"},
    {"key": "ai_career", "icon": ft.Icons.WORK_OUTLINE, "label": "AI Životopis / Kariéra"},
    {"key": "ai_legal", "icon": ft.Icons.GAVEL_OUTLINED, "label": "AI Právní asistent"},
    {"key": "ai_business", "icon": ft.Icons.BUSINESS_CENTER_OUTLINED, "label": "AI Podnikání"},
    {"key": "ai_marketing", "icon": ft.Icons.CAMPAIGN_OUTLINED, "label": "AI Marketing"},
    {"key": "ai_finance", "icon": ft.Icons.SAVINGS_OUTLINED, "label": "AI Finance"},
    {"key": "ai_study", "icon": ft.Icons.SCHOOL_OUTLINED, "label": "AI Studium"},
    {"key": "ai_documents", "icon": ft.Icons.DESCRIPTION_OUTLINED, "label": "AI Dokumenty"},
]

SECONDARY_NAV = [
    {"key": "history", "icon": ft.Icons.HISTORY, "label": "Historie"},
    {"key": "favorites", "icon": ft.Icons.STAR_OUTLINE, "label": "Oblíbené", "badge": "3"},
    {"key": "settings", "icon": ft.Icons.SETTINGS_OUTLINED, "label": "Nastavení"},
]

USER = {
    "name": "Jan Novák",
    "email": "jan.novak@email.com",
}

CHAT_TITLE = "AI Životopis / Kariéra"
CHAT_SUBTITLE = "Vytvářejte profesionální životopisy, motivační dopisy a připravte se na pohovor."
CHAT_ICON = ft.Icons.WORK_OUTLINE

MESSAGES = [
    {
        "role": "user",
        "time": "10:24",
        "text": "Vytvoř mi profesionální životopis na pozici Frontend Developer.",
    },
    {
        "role": "assistant",
        "time": "10:24",
        "text": (
            "Jasně, rád ti pomohu vytvořit profesionální životopis na pozici "
            "Frontend Developer.\nNejprve potřebuji pár informací:"
        ),
        "bullets": [
            "Tvé jméno a kontaktní údaje",
            "Pracovní zkušenosti",
            "Vzdělání",
            "Dovednosti (technologie, nástroje)",
            "Jazykové znalosti",
            "Projekty (pokud máš)",
        ],
        "footer": "Můžeš mi také poslat svůj současný životopis, pokud chceš, abych ho upravil.",
        "actions": [
            {"icon": ft.Icons.AUTO_AWESOME, "label": "Vygenerovat šablonu"},
            {"icon": ft.Icons.VISIBILITY_OUTLINED, "label": "Ukázka životopisu"},
            {"icon": ft.Icons.ARTICLE_OUTLINED, "label": "Formulářový režim"},
        ],
    },
    {
        "role": "user",
        "time": "10:25",
        "text": "Jmenuji se Jan Novák, mám 3 roky praxe...",
    },
    {
        "role": "assistant",
        "time": "10:25",
        "text": "Děkuji za informace! Připravuji tvůj životopis...",
        "attachment": {
            "name": "Jan_Novak_Zivotopis.docx",
            "type": "DOCX",
            "size": "24 kB",
        },
    },
]

CONTEXT_DOCS = [
    {"name": "Muj_zivotopis_2024.pdf", "type": "PDF", "size": "142 kB"},
    {"name": "Motivacni_dopis_vzor.docx", "type": "DOCX", "size": "32 kB"},
]

QUICK_ACTIONS = [
    {"icon": ft.Icons.MAIL_OUTLINE, "label": "Vytvořit motivační dopis"},
    {"icon": ft.Icons.HELP_OUTLINE, "label": "Připravit se na pohovor"},
    {"icon": ft.Icons.DESCRIPTION_OUTLINED, "label": "Analyzovat pracovní nabídku"},
    {"icon": ft.Icons.PERSON_OUTLINE, "label": "Vylepšit LinkedIn profil"},
]

CONVO_HISTORY = [
    {"title": "Životopis - Frontend Developer", "time": "Před 2 hodinami"},
    {"title": "Motivační dopis - Marketing", "time": "Včera"},
    {"title": "Příprava na pohovor", "time": "Včera"},
    {"title": "Analýza pracovní nabídky", "time": "3 dny zpět"},
]

INPUT_ACTIONS = [
    {"icon": ft.Icons.ATTACH_FILE, "label": "Připojit dokument"},
    {"icon": ft.Icons.MIC_NONE_OUTLINED, "label": "Hlasový vstup"},
    {"icon": ft.Icons.AUTO_FIX_HIGH, "label": "Vylepšit prompt"},
]

INPUT_HINT = "AI může dělat chyby. Ověřujte důležité informace."
