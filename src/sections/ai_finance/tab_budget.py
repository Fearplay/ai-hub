"""Budget tab for AI Finance.

Two-column layout: left is the form (income, method, savings goal,
essentials, lifestyle, notes), right is the rendered :data:`STATE.budget`
once a run completes. While there is no budget yet we render a hint
card on the right asking the user to build one.
"""

from __future__ import annotations

import threading
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.qt.icons import Icons
from src.qt.widgets import (
    BodyLabel,
    GhostButton,
    MutedLabel,
    PrimaryButton,
    SubtleLabel,
    TitleLabel,
    hbox,
    vbox,
    wrap_label_slot,
)
from src.services import logger as logger_service
from src.sections.ai_finance import pipeline
from src.sections.ai_finance._widgets import (
    breakdown_table,
    budget_slices_from_plan,
    card_title,
    disclaimer_pill,
    donut_with_caption,
    labelled_combo,
    labelled_line_edit,
    labelled_text_edit,
    legend_for_splits,
    list_card,
    responsive_two_columns,
    section_card,
)
from src.sections.ai_finance.refs import REFS
from src.sections.ai_finance.state import (
    BUDGET_METHOD_50_30_20,
    STATE,
)
from src.sections.ai_finance.strings import s
from src.theme import Theme


def _parse_float(text: str) -> float:
    try:
        return float((text or "0").replace(" ", "").replace(",", "."))
    except ValueError:
        return 0.0


def _build_form(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    card, layout = section_card(theme)
    layout.addWidget(
        card_title(
            theme,
            title=txt["budget_mock_title"],
            subtitle=txt["budget_mock_desc"],
            icon=Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
        )
    )

    cached = STATE.last_budget_input
    currency_initial = str(cached.get("currency") or txt["currency_code"])
    income_initial = str(cached.get("income") or "")
    method_initial = str(cached.get("method") or BUDGET_METHOD_50_30_20)
    savings_initial = str(cached.get("savings_goal") or "")
    essentials_initial = str(cached.get("essentials") or "")
    lifestyle_initial = str(cached.get("lifestyle") or "")
    notes_initial = str(cached.get("notes") or "")

    currency_row, currency_field = labelled_line_edit(
        theme,
        label=txt["form_currency"],
        hint=txt["currency_code"],
        placeholder=txt["currency_code"],
        initial=currency_initial,
    )
    income_row, income_field = labelled_line_edit(
        theme,
        label=txt["budget_field_income"],
        hint=txt["budget_field_income_hint"],
        placeholder=txt["budget_field_income_hint"],
        initial=income_initial,
    )

    method_options = [
        (BUDGET_METHOD_50_30_20, txt["budget_method_50_30_20"]),
        ("60_20_20", txt["budget_method_60_20_20"]),
        ("70_20_10", txt["budget_method_70_20_10"]),
        ("zero_based", txt["budget_method_zero_based"]),
        ("custom", txt["budget_method_custom"]),
    ]
    method_row, method_combo = labelled_combo(
        theme,
        label=txt["budget_method_label"],
        options=method_options,
        initial_value=method_initial,
    )

    savings_row, savings_field = labelled_line_edit(
        theme,
        label=txt["budget_field_savings"],
        hint=txt["budget_field_savings_hint"],
        placeholder=txt["budget_field_savings_hint"],
        initial=savings_initial,
    )
    essentials_row, essentials_field = labelled_text_edit(
        theme,
        label=txt["budget_field_essentials"],
        hint=txt["budget_field_essentials_hint"],
        placeholder=txt["budget_field_essentials_hint"],
        initial=essentials_initial,
        min_height=90,
    )
    lifestyle_row, lifestyle_field = labelled_text_edit(
        theme,
        label=txt["budget_field_lifestyle"],
        hint=txt["budget_field_lifestyle_hint"],
        placeholder=txt["budget_field_lifestyle_hint"],
        initial=lifestyle_initial,
        min_height=70,
    )
    notes_row, notes_field = labelled_text_edit(
        theme,
        label=txt["taxes_field_notes"],
        hint=txt["taxes_field_notes_hint"],
        placeholder=txt["taxes_field_notes_hint"],
        initial=notes_initial,
        min_height=60,
    )

    top_row = QFrame()
    top_row.setStyleSheet("background: transparent;")
    top_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    top_row.setLayout(top_layout)
    top_layout.addWidget(currency_row, 1)
    top_layout.addWidget(income_row, 2)
    layout.addWidget(top_row)

    layout.addWidget(method_row)
    layout.addWidget(savings_row)
    layout.addWidget(essentials_row)
    layout.addWidget(lifestyle_row)
    layout.addWidget(notes_row)

    run_btn = PrimaryButton(txt["budget_run_button"], theme=theme, icon=Icons.AUTO_AWESOME)

    def _run() -> None:
        currency = currency_field.text().strip() or txt["currency_code"]
        income = _parse_float(income_field.text())
        method = method_combo.currentData() or BUDGET_METHOD_50_30_20
        savings = savings_field.text().strip()
        essentials = essentials_field.toPlainText().strip()
        lifestyle = lifestyle_field.toPlainText().strip()
        notes = notes_field.toPlainText().strip()

        run_btn.setEnabled(False)

        def _worker() -> None:
            try:
                pipeline.create_budget(
                    output_lang=lang,
                    currency=currency,
                    income=income,
                    method=method,
                    savings_goal=savings,
                    essentials=essentials,
                    lifestyle=lifestyle,
                    notes=notes,
                )
            except Exception as exc:
                logger_service.log_exception(
                    "ai_finance.tab_budget", "create_budget_worker_failed", exc
                )

        threading.Thread(target=_worker, daemon=True).start()

    run_btn.clicked.connect(_run)

    button_row = QFrame()
    button_row.setStyleSheet("background: transparent;")
    button_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    button_row.setLayout(button_layout)
    button_layout.addWidget(run_btn)
    button_layout.addStretch(1)
    layout.addWidget(button_row)
    layout.addWidget(disclaimer_pill(theme, label=txt["disclaimer_short"]))
    return card


def _empty_result(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    card, layout = section_card(theme)
    layout.addWidget(
        card_title(
            theme,
            title=txt["budget_title"],
            subtitle=txt["budget_subtitle"],
            icon=Icons.PIE_CHART_OUTLINE,
        )
    )
    layout.addWidget(MutedLabel(txt["budget_mock_desc"], theme=theme, size=12))
    return card


def _result_view(theme: Theme, lang: str, budget: dict) -> QWidget:
    txt = s(lang)
    holder = QWidget()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=14, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    main_card, main_layout = section_card(theme)
    main_layout.addWidget(
        card_title(
            theme,
            title=txt["budget_title"],
            subtitle=budget.get("summary") or txt["budget_subtitle"],
            icon=Icons.PIE_CHART_OUTLINE,
        )
    )
    slices = budget_slices_from_plan(budget)
    currency = budget.get("currency") or txt["currency_code"]
    income = budget.get("income") or 0

    body = QFrame()
    body.setStyleSheet("background: transparent;")
    body_layout = hbox(spacing=18, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)
    body_layout.addWidget(
        donut_with_caption(
            theme,
            slices=slices,
            caption_top=f"{income:,.0f} {currency}".replace(",", " "),
            caption_bottom=txt["donut_caption_bottom"],
        )
    )
    body_layout.addWidget(legend_for_splits(theme, slices, currency=currency), 1)
    main_layout.addWidget(body)

    breakdown = budget.get("breakdown") or []
    if breakdown:
        main_layout.addWidget(
            breakdown_table(
                theme,
                rows=breakdown,
                currency=currency,
                headers=[
                    txt["col_category"],
                    txt["col_recommended"],
                    txt["col_amount"],
                    txt["col_note"],
                ],
            )
        )
    layout.addWidget(main_card)

    warnings = budget.get("warnings") or []
    if warnings:
        layout.addWidget(
            list_card(
                theme,
                title=txt["budget_warnings_title"],
                items=warnings,
                icon=Icons.WARNING_AMBER_ROUNDED,
            )
        )
    suggestions = budget.get("suggestions") or []
    if suggestions:
        layout.addWidget(
            list_card(
                theme,
                title=txt["budget_suggestions_title"],
                items=suggestions,
                icon=Icons.LIGHTBULB_OUTLINE,
            )
        )
    layout.addWidget(disclaimer_pill(theme, label=txt["disclaimer_long"]))
    return holder


def build_budget_tab(theme: Theme, lang: str) -> QWidget:
    page = QWidget()
    page.setStyleSheet(f"background-color: {theme.bg};")
    outer = vbox(spacing=18, margins=(24, 20, 24, 24))
    page.setLayout(outer)

    form_holder = QFrame()
    form_holder.setStyleSheet("background: transparent;")
    form_holder.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    form_layout = vbox(spacing=12, margins=(0, 0, 0, 0))
    form_holder.setLayout(form_layout)
    form_layout.addWidget(_build_form(theme, lang))
    form_layout.addStretch(1)

    result_holder = QFrame()
    result_holder.setStyleSheet("background: transparent;")
    wrap_label_slot(result_holder)
    result_layout = vbox(spacing=12, margins=(0, 0, 0, 0))
    result_holder.setLayout(result_layout)
    if STATE.budget is None:
        result_layout.addWidget(_empty_result(theme, lang))
    else:
        result_layout.addWidget(_result_view(theme, lang, STATE.budget))
    result_layout.addStretch(1)

    columns = responsive_two_columns(form_holder, result_holder)
    outer.addWidget(columns)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(page)
    return scroll
