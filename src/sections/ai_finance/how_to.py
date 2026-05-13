"""How-to dialog for the AI Finance section.

Wired through :func:`src.components.how_to_dialog.open_how_to` from the
header's ``?`` button. Keep the copy short - the dialog is the user's
30-second orientation, not a manual.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget

from src.components.how_to_dialog import HowToSection, open_how_to
from src.qt.icons import Icons
from src.sections.ai_finance.strings import s
from src.theme import Theme


def _sections(lang: str) -> list[HowToSection]:
    if lang == "cs":
        return [
            HowToSection(
                icon=Icons.QUESTION_ANSWER_OUTLINED,
                title="Chat s finančním pomocníkem",
                body=(
                    "V záložce Chat napiš dotaz vlastními slovy. AI Finance ti "
                    "doporučí přepnout do strukturované záložky (Rozpočet, "
                    "Investice...), kdykoliv je tvoje otázka vhodnější pro "
                    "ucelený výstup s grafem nebo tabulkou."
                ),
            ),
            HowToSection(
                icon=Icons.PIE_CHART_OUTLINE,
                title="Rozpočet a spoření",
                body=(
                    "V záložce Rozpočet vyber metodu (50/30/20, 60/20/20...) "
                    "a vyplň příjem, esenciální výdaje a cíle. Dostaneš "
                    "rozpis kategorií + návrh úspor a investic."
                ),
            ),
            HowToSection(
                icon=Icons.TRENDING_UP,
                title="Investiční scénáře",
                body=(
                    "Záložka Investice vrátí tři vzdělávací scénáře "
                    "(konzervativní, vyvážený, růstový) - nikdy nedoporučujeme "
                    "konkrétní akcii ani fond, jen třídy aktiv."
                ),
            ),
            HowToSection(
                icon=Icons.QUERY_STATS,
                title="Analýza výdajů",
                body=(
                    "Přetáhni výpis z banky (CSV/PDF). Parsování probíhá lokálně "
                    "u tebe v PC - AI uvidí jen extrahovaný text, žádné citlivé "
                    "metadata."
                ),
            ),
            HowToSection(
                icon=Icons.SHIELD_OUTLINED,
                title="Daně a pojištění",
                body=(
                    "Tyto dvě záložky generují checklist + upozornění. Nejde "
                    "o licencované poradenství - důležité kroky si ověř u "
                    "kvalifikovaného poradce."
                ),
            ),
            HowToSection(
                icon=Icons.CALCULATE_OUTLINED,
                title="Kalkulačky a tržní data",
                body=(
                    "Kalkulačky jsou ryze klientské (žádné AI volání). Pravý "
                    "panel ukazuje živé tickery přes yfinance - v Nastavení "
                    "můžeš live data vypnout."
                ),
            ),
            HowToSection(
                icon=Icons.PUBLIC,
                title="Web search v chatu",
                body=(
                    "V Nastavení můžeš zapnout 'Web search v chatu'. Model "
                    "pak dohledá aktuální data (kurzy, zprávy). Posíláme "
                    "pouze tvůj dotaz, nikoli údaje o tobě."
                ),
            ),
        ]
    return [
        HowToSection(
            icon=Icons.QUESTION_ANSWER_OUTLINED,
            title="Chat with the assistant",
            body=(
                "Type any question in the Chat tab. The assistant will nudge "
                "you to a structured tab (Budget, Investments...) whenever a "
                "chart / table answer is sharper than free-form prose."
            ),
        ),
        HowToSection(
            icon=Icons.PIE_CHART_OUTLINE,
            title="Budgets + savings",
            body=(
                "Pick a method (50/30/20, 60/20/20...) and fill in income, "
                "essentials, and goals. The assistant produces a category "
                "breakdown plus saving / investing suggestions."
            ),
        ),
        HowToSection(
            icon=Icons.TRENDING_UP,
            title="Investment scenarios",
            body=(
                "The Investments tab returns three educational scenarios "
                "(Conservative / Moderate / Growth). We never recommend a "
                "specific stock or fund - only asset classes."
            ),
        ),
        HowToSection(
            icon=Icons.QUERY_STATS,
            title="Expense analysis",
            body=(
                "Drop a bank statement (CSV / PDF). Parsing happens locally "
                "on your machine - the AI only sees the extracted text, "
                "never the raw file."
            ),
        ),
        HowToSection(
            icon=Icons.SHIELD_OUTLINED,
            title="Taxes + insurance",
            body=(
                "These tabs build a checklist and flag watch-outs. They are "
                "not a substitute for a licensed tax or insurance advisor - "
                "verify anything important professionally."
            ),
        ),
        HowToSection(
            icon=Icons.CALCULATE_OUTLINED,
            title="Calculators + live markets",
            body=(
                "Calculators run client-side (no AI call). The right panel "
                "shows live tickers via yfinance - disable in Settings to "
                "keep the section fully offline."
            ),
        ),
        HowToSection(
            icon=Icons.PUBLIC,
            title="Web search in chat",
            body=(
                "Settings has a 'Web search in chat' toggle. When on, the "
                "model can look up live data (prices, news). Only your "
                "prompt is sent - no personal data, no device info."
            ),
        ),
    ]


def open_finance_how_to(parent: Optional[QWidget], theme: Theme, lang: str) -> None:
    txt = s(lang)
    open_how_to(
        parent,
        theme,
        title=txt["menu_how_to"],
        sections=_sections(lang),
        close_label=txt["how_to_close"] if "how_to_close" in txt else ("Close" if lang == "en" else "Zavřít"),
    )
