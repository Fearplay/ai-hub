"""Expense Analysis tab for AI Finance.

Form on the left with an optional file drop zone (CSV / PDF / TXT
local-only parse via :mod:`src.services.file_parser`). Right side shows
the categorised spend, top outflows and recurring payments once a run
finishes.
"""

from __future__ import annotations

import threading
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.components.file_drop_zone import file_drop_zone
from src.qt.icons import Icons
from src.qt.widgets import (
    BodyLabel,
    MutedLabel,
    PrimaryButton,
    TitleLabel,
    custom_label,
    hbox,
    vbox,
    wrap_label_slot,
)
from src.services import logger as logger_service
from src.services.file_parser import ParsedFile
from src.sections.ai_finance import pipeline
from src.sections.ai_finance._widgets import (
    amount_bar,
    card_title,
    disclaimer_pill,
    labelled_line_edit,
    labelled_text_edit,
    list_card,
    responsive_two_columns,
    section_card,
)
from src.sections.ai_finance.state import STATE
from src.sections.ai_finance.strings import s
from src.theme import Theme


_CATEGORY_COLORS = (
    "#3B82F6",
    "#22C55E",
    "#F59E0B",
    "#A78BFA",
    "#EF4444",
    "#0EA5E9",
    "#14B8A6",
    "#F472B6",
)


def _build_form(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    card, layout = section_card(theme)
    layout.addWidget(
        card_title(
            theme,
            title=txt["analysis_title"],
            subtitle=txt["analysis_desc"],
            icon=Icons.QUERY_STATS,
        )
    )

    cached = STATE.last_analysis_input

    currency_row, currency_field = labelled_line_edit(
        theme,
        label=txt["form_currency"],
        hint=txt["currency_code"],
        initial=str(cached.get("currency") or txt["currency_code"]),
    )
    period_row, period_field = labelled_line_edit(
        theme,
        label=txt["analysis_field_period"],
        hint=txt["analysis_field_period_hint"],
        initial=str(cached.get("period") or ""),
    )
    focus_row, focus_field = labelled_line_edit(
        theme,
        label=txt["analysis_field_focus"],
        hint=txt["analysis_field_focus_hint"],
        initial=str(cached.get("focus") or ""),
    )
    goal_row, goal_field = labelled_text_edit(
        theme,
        label=txt["analysis_field_goal"],
        hint=txt["analysis_field_goal_hint"],
        placeholder=txt["analysis_field_goal_hint"],
        initial=str(cached.get("goal") or ""),
        min_height=70,
    )

    top_row = QFrame()
    top_row.setStyleSheet("background: transparent;")
    top_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    top_row.setLayout(top_layout)
    top_layout.addWidget(currency_row, 1)
    top_layout.addWidget(period_row, 2)
    layout.addWidget(top_row)
    layout.addWidget(focus_row)
    layout.addWidget(goal_row)

    upload_state: dict[str, Optional[ParsedFile]] = {"file": None}

    def _on_file(parsed: ParsedFile) -> None:
        upload_state["file"] = parsed
        attach_label.setText(f"{txt['drop_zone_attached']} {parsed.name}")
        attach_label.setVisible(True)

    drop = file_drop_zone(
        theme,
        log_area="ai_finance.analysis",
        title=txt["analysis_upload_title"],
        hint=txt["analysis_upload_hint"],
        extensions=("csv", "pdf", "txt", "md", "html", "htm"),
        unsupported_message=txt["error_no_input"],
        on_file_resolved=_on_file,
        height=160,
    )
    layout.addWidget(drop)

    attach_label = custom_label("", color=theme.text_muted, size=11)
    attach_label.setVisible(False)
    layout.addWidget(attach_label)

    run_btn = PrimaryButton(txt["analysis_run_button"], theme=theme, icon=Icons.QUERY_STATS)

    def _run() -> None:
        run_btn.setEnabled(False)
        currency = currency_field.text().strip() or txt["currency_code"]
        period = period_field.text().strip()
        focus = focus_field.text().strip()
        goal = goal_field.toPlainText().strip()
        statement_text = ""
        upload = upload_state["file"]
        if upload is not None:
            statement_text = upload.text or ""

        def _worker() -> None:
            try:
                pipeline.analyze_expenses(
                    output_lang=lang,
                    currency=currency,
                    period=period,
                    focus=focus,
                    goal=goal,
                    statement_text=statement_text,
                )
            except Exception as exc:
                logger_service.log_exception(
                    "ai_finance.tab_analysis", "analysis_worker_failed", exc
                )

        threading.Thread(target=_worker, daemon=True).start()

    run_btn.clicked.connect(_run)
    row = QFrame()
    row.setStyleSheet("background: transparent;")
    row_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    row.setLayout(row_layout)
    row_layout.addWidget(run_btn)
    row_layout.addStretch(1)
    layout.addWidget(row)
    layout.addWidget(disclaimer_pill(theme, label=txt["disclaimer_short"]))
    return card


def _stat_pill(theme: Theme, label: str, value: str, *, color: str) -> QFrame:
    pill = QFrame()
    pill.setStyleSheet(
        f"background-color: {theme.surface_2}; border-radius: 10px;"
    )
    pl = vbox(spacing=2, margins=(14, 10, 14, 10))
    pill.setLayout(pl)
    label_widget = MutedLabel(label, theme=theme, size=11)
    pl.addWidget(label_widget)
    val_label = custom_label(value, color=color, size=16)
    val_label.setStyleSheet(f"color: {color}; background: transparent; font-weight: 700;")
    pl.addWidget(val_label)
    return pill


def _result_view(theme: Theme, lang: str, plan: dict) -> QWidget:
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=12, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    currency = plan.get("currency") or txt["currency_code"]

    totals_card, totals_layout = section_card(theme)
    totals_layout.addWidget(
        card_title(
            theme,
            title=txt["analysis_title"],
            subtitle=plan.get("summary") or plan.get("period") or "",
            icon=Icons.QUERY_STATS,
        )
    )
    pills_row = QFrame()
    pills_row.setStyleSheet("background: transparent;")
    pills_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    pills_row.setLayout(pills_layout)
    pills_layout.addWidget(
        _stat_pill(
            theme,
            txt["analysis_totals_income"],
            f"{plan.get('total_income', 0):,.0f} {currency}".replace(",", " "),
            color="#22C55E",
        )
    )
    pills_layout.addWidget(
        _stat_pill(
            theme,
            txt["analysis_totals_expenses"],
            f"{plan.get('total_expenses', 0):,.0f} {currency}".replace(",", " "),
            color="#EF4444",
        )
    )
    net = plan.get("net_cash_flow", 0)
    pills_layout.addWidget(
        _stat_pill(
            theme,
            txt["analysis_totals_net"],
            f"{net:,.0f} {currency}".replace(",", " "),
            color="#3B82F6" if net >= 0 else "#EF4444",
        )
    )
    pills_layout.addStretch(1)
    totals_layout.addWidget(pills_row)
    layout.addWidget(totals_card)

    cats = plan.get("categories") or []
    if cats:
        cat_card, cat_layout = section_card(theme)
        cat_layout.addWidget(card_title(theme, title=txt["analysis_categories_title"], icon=Icons.PIE_CHART_OUTLINE))
        for i, cat in enumerate(cats):
            cat_layout.addWidget(
                amount_bar(
                    theme,
                    label=str(cat.get("name", "")),
                    value=f"{cat.get('amount', 0):,.0f} {currency}".replace(",", " "),
                    percent=float(cat.get("percent_of_expenses", 0)),
                    color=_CATEGORY_COLORS[i % len(_CATEGORY_COLORS)],
                )
            )
        layout.addWidget(cat_card)

    top = plan.get("top_outflows") or []
    if top:
        items = [
            f"**{entry.get('label', '')}** - {entry.get('amount', 0):,.0f} {currency} - {entry.get('note', '')}".replace(
                ",", " "
            )
            for entry in top
        ]
        layout.addWidget(
            list_card(
                theme,
                title=txt["analysis_top_outflows_title"],
                items=items,
                icon=Icons.TRENDING_UP,
            )
        )

    recurring = plan.get("recurring") or []
    if recurring:
        items = [
            f"**{entry.get('label', '')}** - {entry.get('monthly_amount', 0):,.0f} {currency} ({entry.get('category', '')})".replace(
                ",", " "
            )
            for entry in recurring
        ]
        layout.addWidget(
            list_card(
                theme,
                title=txt["analysis_recurring_title"],
                items=items,
                icon=Icons.RESTART_ALT,
            )
        )

    suggestions = plan.get("suggestions") or []
    if suggestions:
        layout.addWidget(
            list_card(
                theme,
                title=txt["analysis_suggestions_title"],
                items=suggestions,
                icon=Icons.LIGHTBULB_OUTLINE,
            )
        )
    layout.addWidget(disclaimer_pill(theme, label=txt["disclaimer_long"]))
    return holder


def _empty_result(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    card, layout = section_card(theme)
    layout.addWidget(card_title(theme, title=txt["analysis_title"], subtitle=txt["analysis_desc"], icon=Icons.QUERY_STATS))
    layout.addWidget(MutedLabel(txt["analysis_upload_hint"], theme=theme, size=12))
    return card


def build_analysis_tab(theme: Theme, lang: str) -> QWidget:
    page = QWidget()
    page.setStyleSheet(f"background-color: {theme.bg};")
    outer = vbox(spacing=18, margins=(24, 20, 24, 24))
    page.setLayout(outer)

    form_col = QFrame()
    form_col.setStyleSheet("background: transparent;")
    form_layout = vbox(spacing=12, margins=(0, 0, 0, 0))
    form_col.setLayout(form_layout)
    form_layout.addWidget(_build_form(theme, lang))
    form_layout.addStretch(1)

    result_col = QFrame()
    result_col.setStyleSheet("background: transparent;")
    wrap_label_slot(result_col)
    result_layout = vbox(spacing=12, margins=(0, 0, 0, 0))
    result_col.setLayout(result_layout)
    if STATE.expense_analysis is None:
        result_layout.addWidget(_empty_result(theme, lang))
    else:
        result_layout.addWidget(_result_view(theme, lang, STATE.expense_analysis))
    result_layout.addStretch(1)

    columns = responsive_two_columns(form_col, result_col)
    outer.addWidget(columns)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(page)
    return scroll
