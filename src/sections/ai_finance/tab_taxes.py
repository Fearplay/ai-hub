"""Tax tab for AI Finance.

Form -> checklist + deadlines + documents-to-prep + tips. The pipeline
emits an explicit ``disclaimer`` field that we render as a pill on the
right so users do not forget this is not a substitute for a licensed
tax advisor.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QWidget,
)

from src.qt.icons import Icons
from src.qt.widgets import (
    BodyLabel,
    MutedLabel,
    PrimaryButton,
    hbox,
    vbox,
    wrap_label_slot,
)
from src.services import logger as logger_service
from src.sections.ai_finance import pipeline
from src.sections.ai_finance._charts import DeadlineTimeline
from src.sections.ai_finance._widgets import (
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


def _build_form(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    card, layout = section_card(theme)
    layout.addWidget(
        card_title(
            theme,
            title=txt["taxes_title"],
            subtitle=txt["taxes_desc"],
            icon=Icons.RECEIPT_LONG_OUTLINED,
        )
    )

    cached = STATE.last_tax_input
    country_row, country_field = labelled_line_edit(
        theme,
        label=txt["taxes_field_country"],
        hint=txt["taxes_field_country_hint"],
        initial=str(cached.get("country") or ""),
    )
    status_row, status_field = labelled_line_edit(
        theme,
        label=txt["taxes_field_status"],
        hint=txt["taxes_field_status_hint"],
        initial=str(cached.get("filing_status") or ""),
    )
    year_row, year_field = labelled_line_edit(
        theme,
        label=txt["taxes_field_year"],
        hint=txt["taxes_field_year_hint"],
        initial=str(cached.get("year") or ""),
    )
    notes_row, notes_field = labelled_text_edit(
        theme,
        label=txt["taxes_field_notes"],
        hint=txt["taxes_field_notes_hint"],
        placeholder=txt["taxes_field_notes_hint"],
        initial=str(cached.get("notes") or ""),
        min_height=90,
    )

    top_row = QFrame()
    top_row.setStyleSheet("background: transparent;")
    top_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    top_row.setLayout(top_layout)
    top_layout.addWidget(country_row, 2)
    top_layout.addWidget(status_row, 2)
    top_layout.addWidget(year_row, 1)
    layout.addWidget(top_row)
    layout.addWidget(notes_row)

    run_btn = PrimaryButton(txt["taxes_run_button"], theme=theme, icon=Icons.CHECKLIST)

    def _run() -> None:
        run_btn.setEnabled(False)
        country = country_field.text().strip()
        status = status_field.text().strip()
        year = year_field.text().strip()
        notes = notes_field.toPlainText().strip()

        def _worker() -> None:
            try:
                pipeline.generate_tax_checklist(
                    output_lang=lang,
                    country=country,
                    filing_status=status,
                    year=year,
                    notes=notes,
                )
            except Exception as exc:
                logger_service.log_exception(
                    "ai_finance.tab_taxes", "tax_worker_failed", exc
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


def _empty_result(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    card, layout = section_card(theme)
    layout.addWidget(card_title(theme, title=txt["taxes_title"], subtitle=txt["taxes_desc"], icon=Icons.RECEIPT_LONG_OUTLINED))
    layout.addWidget(MutedLabel(txt["taxes_desc"], theme=theme, size=12))
    return card


def _result_view(theme: Theme, lang: str, plan: dict) -> QWidget:
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=12, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    head = section_card(theme)[0]
    head_layout = head.layout()
    head_layout.addWidget(
        card_title(
            theme,
            title=txt["taxes_title"],
            subtitle=f"{plan.get('country', '')} - {plan.get('filing_status', '')} - {plan.get('year', '')}",
            icon=Icons.RECEIPT_LONG_OUTLINED,
        )
    )
    layout.addWidget(head)

    checklist = plan.get("checklist") or []
    if checklist:
        items = [f"**{item.get('title', '')}** - {item.get('detail', '')}" for item in checklist]
        layout.addWidget(
            list_card(
                theme,
                title=txt["taxes_checklist_title"],
                items=items,
                icon=Icons.CHECKLIST,
            )
        )

    deadlines = plan.get("deadlines") or []
    if deadlines:
        timeline_card, timeline_layout = section_card(theme)
        timeline_layout.addWidget(
            card_title(
                theme,
                title=txt["taxes_timeline_title"],
                icon=Icons.SCHEDULE,
            )
        )
        timeline_layout.addWidget(DeadlineTimeline(deadlines=deadlines, theme=theme))
        layout.addWidget(timeline_card)
        items = [f"**{d.get('label', '')}** - {d.get('date_or_window', '')}" for d in deadlines]
        layout.addWidget(
            list_card(
                theme,
                title=txt["taxes_deadlines_title"],
                items=items,
                icon=Icons.SCHEDULE,
            )
        )

    docs = plan.get("documents_needed") or []
    if docs:
        layout.addWidget(
            list_card(
                theme,
                title=txt["taxes_documents_title"],
                items=docs,
                icon=Icons.FOLDER_OPEN,
            )
        )

    tips = plan.get("tips") or []
    if tips:
        layout.addWidget(
            list_card(
                theme,
                title=txt["taxes_tips_title"],
                items=tips,
                icon=Icons.LIGHTBULB_OUTLINE,
            )
        )

    layout.addWidget(
        disclaimer_pill(theme, label=plan.get("disclaimer") or txt["disclaimer_long"])
    )
    return holder


def build_taxes_tab(theme: Theme, lang: str) -> QWidget:
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
    if STATE.tax_checklist is None:
        result_layout.addWidget(_empty_result(theme, lang))
    else:
        result_layout.addWidget(_result_view(theme, lang, STATE.tax_checklist))
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
