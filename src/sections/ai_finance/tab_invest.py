"""Investments tab for AI Finance.

Form on the left, three risk-tier scenario cards on the right. We
never name a single stock or fund - only asset classes - per the
no-stock-picking policy in ``prompts.FINANCE_EXPERT_RULES``.
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

from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    MutedLabel,
    PrimaryButton,
    SubtleLabel,
    TitleLabel,
    custom_label,
    hbox,
    vbox,
    wrap_label_slot,
)
from src.services import logger as logger_service
from src.sections.ai_finance import pipeline
from src.sections.ai_finance._charts import (
    AllocationStackedBar,
    ProjectionSparkline,
    allocation_legend,
)
from src.sections.ai_finance._widgets import (
    amount_bar,
    card_title,
    disclaimer_pill,
    labelled_combo,
    labelled_line_edit,
    labelled_text_edit,
    list_card,
    responsive_two_columns,
    section_card,
)
from src.sections.ai_finance.state import STATE
from src.sections.ai_finance.strings import s
from src.theme import Theme


_ASSET_COLORS = ("#3B82F6", "#22C55E", "#F59E0B", "#A78BFA", "#EF4444", "#0EA5E9")


def _parse_float(text: str) -> float:
    try:
        return float((text or "0").replace(" ", "").replace(",", "."))
    except ValueError:
        return 0.0


def _parse_int(text: str, default: int = 0) -> int:
    try:
        return int(float((text or str(default)).replace(",", ".")))
    except ValueError:
        return default


def _build_form(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    card, layout = section_card(theme)
    layout.addWidget(
        card_title(
            theme,
            title=txt["invest_title"],
            subtitle=txt["invest_desc"],
            icon=Icons.TRENDING_UP,
        )
    )

    cached = STATE.last_invest_input
    currency_row, currency_field = labelled_line_edit(
        theme,
        label=txt["form_currency"],
        hint=txt["currency_code"],
        initial=str(cached.get("currency") or txt["currency_code"]),
    )
    amount_row, amount_field = labelled_line_edit(
        theme,
        label=txt["invest_field_amount"],
        hint=txt["invest_field_amount_hint"],
        placeholder=txt["invest_field_amount_hint"],
        initial=str(cached.get("amount") or ""),
    )
    horizon_row, horizon_field = labelled_line_edit(
        theme,
        label=txt["invest_field_horizon"],
        hint=txt["invest_field_horizon_hint"],
        placeholder=txt["invest_field_horizon_hint"],
        initial=str(cached.get("horizon_years") or "10"),
    )

    risk_options = [
        ("conservative", txt["invest_risk_label_conservative"]),
        ("moderate", txt["invest_risk_label_moderate"]),
        ("growth", txt["invest_risk_label_growth"]),
    ]
    risk_row, risk_combo = labelled_combo(
        theme,
        label=txt["invest_field_risk"],
        options=risk_options,
        initial_value=str(cached.get("risk") or "moderate"),
    )

    focus_row, focus_field = labelled_line_edit(
        theme,
        label=txt["invest_field_focus"],
        hint=txt["invest_field_focus_hint"],
        placeholder=txt["invest_field_focus_hint"],
        initial=str(cached.get("focus") or ""),
    )
    notes_row, notes_field = labelled_text_edit(
        theme,
        label=txt["taxes_field_notes"],
        hint=txt["taxes_field_notes_hint"],
        placeholder=txt["taxes_field_notes_hint"],
        initial=str(cached.get("notes") or ""),
        min_height=70,
    )

    top_row = QFrame()
    top_row.setStyleSheet("background: transparent;")
    top_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    top_row.setLayout(top_layout)
    top_layout.addWidget(currency_row, 1)
    top_layout.addWidget(amount_row, 2)
    layout.addWidget(top_row)

    layout.addWidget(horizon_row)
    layout.addWidget(risk_row)
    layout.addWidget(focus_row)
    layout.addWidget(notes_row)

    run_btn = PrimaryButton(txt["invest_run_button"], theme=theme, icon=Icons.AUTO_AWESOME)

    def _run() -> None:
        run_btn.setEnabled(False)
        currency = currency_field.text().strip() or txt["currency_code"]
        amount = _parse_float(amount_field.text())
        horizon = _parse_int(horizon_field.text(), default=10)
        risk = risk_combo.currentData() or "moderate"
        focus = focus_field.text().strip()
        notes = notes_field.toPlainText().strip()

        def _worker() -> None:
            try:
                pipeline.generate_investment_scenarios(
                    output_lang=lang,
                    currency=currency,
                    amount=amount,
                    horizon_years=horizon,
                    risk=risk,
                    focus=focus,
                    notes=notes,
                )
            except Exception as exc:
                logger_service.log_exception(
                    "ai_finance.tab_invest", "invest_worker_failed", exc
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


def _scenario_card(
    theme: Theme,
    lang: str,
    scenario: dict,
    currency: str,
    *,
    amount: float = 0.0,
    horizon_years: float = 5.0,
) -> QFrame:
    txt = s(lang)
    risk_level = scenario.get("risk_level", "moderate")
    risk_color = {
        "conservative": "#22C55E",
        "moderate": "#3B82F6",
        "growth": "#F59E0B",
    }.get(risk_level, theme.primary)

    card = QFrame()
    card.setObjectName("FinanceScenarioCard")
    card.setStyleSheet(
        f"""
        QFrame#FinanceScenarioCard {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-left: 4px solid {risk_color};
            border-radius: 12px;
        }}
        """
    )
    layout = vbox(spacing=10, margins=(18, 16, 18, 16))
    card.setLayout(layout)

    head = QFrame()
    head.setStyleSheet("background: transparent;")
    head_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    head.setLayout(head_layout)
    head_layout.addWidget(TitleLabel(scenario.get("name", ""), theme=theme, size=15))
    pill = QFrame()
    pill.setStyleSheet(
        f"background-color: {rgba(risk_color, 0.16)}; border-radius: 999px;"
    )
    pill_layout = hbox(spacing=4, margins=(8, 2, 10, 2))
    pill.setLayout(pill_layout)
    pill_layout.addWidget(custom_label(risk_level.title(), color=risk_color, size=10))
    head_layout.addWidget(pill)
    head_layout.addStretch(1)
    layout.addWidget(head)

    if scenario.get("description"):
        layout.addWidget(MutedLabel(scenario["description"], theme=theme, size=12))

    stats = QFrame()
    stats.setStyleSheet("background: transparent;")
    stats_layout = hbox(spacing=24, margins=(0, 0, 0, 0))
    stats.setLayout(stats_layout)

    def _stat(label: str, value: str) -> QFrame:
        col = QFrame()
        col.setStyleSheet("background: transparent;")
        col_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
        col.setLayout(col_layout)
        col_layout.addWidget(SubtleLabel(label, theme=theme, size=11))
        col_layout.addWidget(BodyLabel(value, theme=theme, size=15))
        return col

    expected = scenario.get("expected_annual_return_pct", 0)
    projected = scenario.get("projected_value", 0)
    stats_layout.addWidget(_stat(txt["invest_scenario_return"], f"{expected:.1f}%"))
    stats_layout.addWidget(
        _stat(
            txt["invest_scenario_projected"],
            f"{float(projected):,.0f} {currency}".replace(",", " "),
        )
    )
    stats_layout.addStretch(1)
    layout.addWidget(stats)

    # -- Stacked allocation bar + legend ----
    allocations = scenario.get("allocation") or []
    if allocations:
        segments: list[tuple[str, float, str]] = []
        for i, alloc in enumerate(allocations):
            color = _ASSET_COLORS[i % len(_ASSET_COLORS)]
            segments.append(
                (
                    str(alloc.get("asset_class", "")),
                    float(alloc.get("percent", 0) or 0.0),
                    color,
                )
            )
        layout.addWidget(SubtleLabel(txt["invest_scenario_allocation"], theme=theme, size=11))
        layout.addWidget(AllocationStackedBar(segments=segments, theme=theme))
        layout.addWidget(allocation_legend(theme, segments))

    # -- Projection sparkline (synthesised compounding curve) ----
    if amount > 0 and horizon_years > 0:
        layout.addWidget(SubtleLabel(txt["invest_projection_label"], theme=theme, size=11))
        layout.addWidget(
            ProjectionSparkline(
                amount=amount,
                annual_return_pct=float(expected or 0.0),
                horizon_years=horizon_years,
                color=risk_color,
                theme=theme,
            )
        )
    return card


def _result_view(theme: Theme, lang: str, plan: dict) -> QWidget:
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=14, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    currency = plan.get("currency") or txt["currency_code"]
    amount = float(plan.get("amount") or 0.0)
    horizon_years = float(plan.get("horizon_years") or 0.0)
    for scenario in plan.get("scenarios") or []:
        layout.addWidget(
            _scenario_card(
                theme,
                lang,
                scenario,
                currency,
                amount=amount,
                horizon_years=horizon_years,
            )
        )

    notes_card, notes_layout = section_card(theme)
    notes_layout.addWidget(
        card_title(theme, title=txt["invest_diversification_title"], icon=Icons.HUB_OUTLINED)
    )
    notes_layout.addWidget(
        BodyLabel(
            plan.get("diversification_note", "") or "-", theme=theme, size=12
        )
    )
    notes_layout.addWidget(
        card_title(theme, title=txt["invest_risk_title"], icon=Icons.WARNING_AMBER_ROUNDED)
    )
    notes_layout.addWidget(
        BodyLabel(plan.get("risk_note", "") or "-", theme=theme, size=12)
    )
    layout.addWidget(notes_card)
    layout.addWidget(disclaimer_pill(theme, label=plan.get("disclaimer") or txt["disclaimer_long"]))
    return holder


def _empty_result(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)
    card, layout = section_card(theme)
    layout.addWidget(card_title(theme, title=txt["invest_title"], subtitle=txt["invest_desc"], icon=Icons.TRENDING_UP))
    layout.addWidget(MutedLabel(txt["invest_desc"], theme=theme, size=12))
    return card


def build_invest_tab(theme: Theme, lang: str) -> QWidget:
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
    if STATE.investment_scenario is None:
        result_layout.addWidget(_empty_result(theme, lang))
    else:
        result_layout.addWidget(_result_view(theme, lang, STATE.investment_scenario))
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
