"""Insurance review tab for AI Finance.

Form + optional policy upload -> structured review with gaps,
duplicates, watch-outs and suggestions.
"""

from __future__ import annotations

import threading
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QWidget,
)

from src.components.file_drop_zone import file_drop_zone
from src.qt.icons import Icons
from src.qt.theme import rgba
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
from src.sections.ai_finance._charts import severity_heatmap
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


_SEVERITY_COLORS = {
    "high": "#EF4444",
    "medium": "#F59E0B",
    "low": "#3B82F6",
}


def _build_form(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    card, layout = section_card(theme)
    layout.addWidget(
        card_title(
            theme,
            title=txt["insurance_title"],
            subtitle=txt["insurance_desc"],
            icon=Icons.SHIELD_OUTLINED,
        )
    )

    cached = STATE.last_insurance_input
    household_row, household_field = labelled_line_edit(
        theme,
        label=txt["insurance_field_household"],
        hint=txt["insurance_field_household_hint"],
        initial=str(cached.get("household") or ""),
    )
    assets_row, assets_field = labelled_line_edit(
        theme,
        label=txt["insurance_field_assets"],
        hint=txt["insurance_field_assets_hint"],
        initial=str(cached.get("assets") or ""),
    )
    existing_row, existing_field = labelled_text_edit(
        theme,
        label=txt["insurance_field_existing"],
        hint=txt["insurance_field_existing_hint"],
        placeholder=txt["insurance_field_existing_hint"],
        initial=str(cached.get("existing") or ""),
        min_height=80,
    )
    concerns_row, concerns_field = labelled_text_edit(
        theme,
        label=txt["insurance_field_concerns"],
        hint=txt["insurance_field_concerns_hint"],
        placeholder=txt["insurance_field_concerns_hint"],
        initial=str(cached.get("concerns") or ""),
        min_height=70,
    )

    top_row = QFrame()
    top_row.setStyleSheet("background: transparent;")
    top_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    top_row.setLayout(top_layout)
    top_layout.addWidget(household_row, 1)
    top_layout.addWidget(assets_row, 2)
    layout.addWidget(top_row)
    layout.addWidget(existing_row)
    layout.addWidget(concerns_row)

    upload_state: dict[str, Optional[ParsedFile]] = {"file": None}
    attach_label = custom_label("", color=theme.text_muted, size=11)
    attach_label.setVisible(False)

    def _on_file(parsed: ParsedFile) -> None:
        upload_state["file"] = parsed
        attach_label.setText(f"{txt['drop_zone_attached']} {parsed.name}")
        attach_label.setVisible(True)

    drop = file_drop_zone(
        theme,
        log_area="ai_finance.insurance",
        title=txt["insurance_upload_title"],
        hint=txt["insurance_upload_hint"],
        extensions=("pdf", "docx", "txt", "md", "html", "htm"),
        unsupported_message=txt["error_no_input"],
        on_file_resolved=_on_file,
        height=160,
    )
    layout.addWidget(drop)
    layout.addWidget(attach_label)

    run_btn = PrimaryButton(txt["insurance_run_button"], theme=theme, icon=Icons.SHIELD_OUTLINED)

    def _run() -> None:
        run_btn.setEnabled(False)
        household = household_field.text().strip()
        assets = assets_field.text().strip()
        existing = existing_field.toPlainText().strip()
        concerns = concerns_field.toPlainText().strip()
        document_text = ""
        upload = upload_state["file"]
        if upload is not None:
            document_text = upload.text or ""

        def _worker() -> None:
            try:
                pipeline.review_insurance(
                    output_lang=lang,
                    household=household,
                    assets=assets,
                    existing=existing,
                    concerns=concerns,
                    document_text=document_text,
                )
            except Exception as exc:
                logger_service.log_exception(
                    "ai_finance.tab_insurance", "insurance_worker_failed", exc
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
    layout.addWidget(card_title(theme, title=txt["insurance_title"], subtitle=txt["insurance_desc"], icon=Icons.SHIELD_OUTLINED))
    layout.addWidget(MutedLabel(txt["insurance_desc"], theme=theme, size=12))
    return card


def _result_view(theme: Theme, lang: str, plan: dict) -> QWidget:
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=12, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    summary_card, summary_layout = section_card(theme)
    summary_layout.addWidget(
        card_title(
            theme,
            title=txt["insurance_title"],
            subtitle=plan.get("household") or "",
            icon=Icons.SHIELD_OUTLINED,
        )
    )
    if plan.get("summary"):
        summary_layout.addWidget(BodyLabel(plan["summary"], theme=theme, size=12, selectable=True))
    layout.addWidget(summary_card)

    policies = plan.get("policies") or []
    if policies:
        items = [
            f"**{p.get('name', '')}** ({p.get('kind', '')}) - {p.get('limit_note', '')} - {p.get('premium_note', '')}"
            for p in policies
        ]
        layout.addWidget(
            list_card(
                theme,
                title=txt["insurance_policies_title"],
                items=items,
                icon=Icons.SHIELD_OUTLINED,
            )
        )

    gaps = plan.get("coverage_gaps") or []
    if gaps:
        heatmap_card, heatmap_layout = section_card(theme)
        heatmap_layout.addWidget(
            card_title(
                theme,
                title=txt["insurance_heatmap_title"],
                icon=Icons.WARNING_AMBER_ROUNDED,
            )
        )
        heatmap_layout.addWidget(
            severity_heatmap(
                theme,
                gaps,
                high_label=txt["insurance_severity_high"],
                medium_label=txt["insurance_severity_medium"],
                low_label=txt["insurance_severity_low"],
            )
        )
        layout.addWidget(heatmap_card)

    duplicates = plan.get("duplicates") or []
    if duplicates:
        layout.addWidget(
            list_card(
                theme,
                title=txt["insurance_duplicates_title"],
                items=duplicates,
                icon=Icons.COMPARE_ARROWS,
            )
        )

    watch_outs = plan.get("watch_outs") or []
    if watch_outs:
        layout.addWidget(
            list_card(
                theme,
                title=txt["insurance_watch_outs_title"],
                items=watch_outs,
                icon=Icons.VISIBILITY_OUTLINED,
            )
        )

    suggestions = plan.get("suggestions") or []
    if suggestions:
        layout.addWidget(
            list_card(
                theme,
                title=txt["insurance_suggestions_title"],
                items=suggestions,
                icon=Icons.LIGHTBULB_OUTLINE,
            )
        )

    layout.addWidget(
        disclaimer_pill(theme, label=plan.get("disclaimer") or txt["disclaimer_long"])
    )
    return holder


def build_insurance_tab(theme: Theme, lang: str) -> QWidget:
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
    if STATE.insurance_review is None:
        result_layout.addWidget(_empty_result(theme, lang))
    else:
        result_layout.addWidget(_result_view(theme, lang, STATE.insurance_review))
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
