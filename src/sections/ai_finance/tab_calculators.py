"""Calculators tab for AI Finance - pure Python, no AI calls.

Six side-by-side calculator cards:

* Compound interest
* Mortgage payment
* Loan affordability
* Retirement planner
* Savings goal (deposits to reach a target)
* Currency converter (uses :mod:`src.services.market_data` when the
  live market toggle is on; falls back to a friendly message otherwise)

Each calculator has its own ``QFrame`` and computes results on the GUI
thread - the math is fast enough that no worker is needed.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QScrollArea,
    QWidget,
)

from src.qt.icons import Icons
from src.qt.widgets import (
    BodyLabel,
    MutedLabel,
    PrimaryButton,
    SubtleLabel,
    TitleLabel,
    custom_label,
    hbox,
    vbox,
)
from src.services import logger as logger_service
from src.services import market_data, settings_store
from src.sections.ai_finance._widgets import (
    card_title,
    labelled_line_edit,
    section_card,
)
from src.sections.ai_finance.strings import s
from src.theme import Theme


def _parse_float(text: str, default: float = 0.0) -> float:
    try:
        return float((text or str(default)).replace(" ", "").replace(",", "."))
    except ValueError:
        return default


def _parse_int(text: str, default: int = 0) -> int:
    try:
        return int(round(float((text or str(default)).replace(",", "."))))
    except ValueError:
        return default


def _make_calculator(
    theme: Theme,
    *,
    title: str,
    subtitle: str,
    icon: str,
) -> tuple[QFrame, callable]:
    """Return ``(card, add_field)`` so each calc keeps its layout tight."""
    card, layout = section_card(theme)
    layout.addWidget(card_title(theme, title=title, subtitle=subtitle, icon=icon))

    def add(widget: QWidget) -> None:
        layout.addWidget(widget)

    return card, add


def _result_panel(theme: Theme) -> tuple[QFrame, Callable[[list[tuple[str, str]]], None]]:
    """A small result strip that can be refreshed with new label/value pairs."""
    panel = QFrame()
    panel.setStyleSheet(
        f"background-color: {theme.surface_2}; border-radius: 10px;"
    )
    layout = vbox(spacing=4, margins=(12, 10, 12, 10))
    panel.setLayout(layout)
    title = SubtleLabel("", theme=theme, size=11)
    layout.addWidget(title)
    title.setVisible(False)
    rows: list[tuple] = []

    def set_rows(items: list[tuple[str, str]]) -> None:
        while layout.count() > 1:
            item = layout.takeAt(1)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not items:
            panel.setVisible(False)
            return
        panel.setVisible(True)
        for label, value in items:
            row = QFrame()
            row.setStyleSheet("background: transparent;")
            r_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
            row.setLayout(r_layout)
            r_layout.addWidget(MutedLabel(label, theme=theme, size=12))
            r_layout.addStretch(1)
            val = custom_label(value, color=theme.text, size=14)
            val.setStyleSheet(
                f"color: {theme.text}; background: transparent; font-weight: 700;"
            )
            r_layout.addWidget(val)
            layout.addWidget(row)

    panel.setVisible(False)
    return panel, set_rows


def _compound_calculator(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    card, add = _make_calculator(
        theme,
        title=txt["calc_section_compound"],
        subtitle=txt["calc_compound_help"],
        icon=Icons.TIMELINE,
    )
    p_row, p_field = labelled_line_edit(theme, label=txt["calc_field_principal"], placeholder="10000", initial="10000")
    m_row, m_field = labelled_line_edit(theme, label=txt["calc_field_monthly_contribution"], placeholder="500", initial="500")
    r_row, r_field = labelled_line_edit(theme, label=txt["calc_field_rate"], placeholder="5", initial="5")
    y_row, y_field = labelled_line_edit(theme, label=txt["calc_field_years"], placeholder="10", initial="10")
    add(p_row)
    add(m_row)
    add(r_row)
    add(y_row)
    btn = PrimaryButton(txt["calc_run"], theme=theme, icon=Icons.PLAY_ARROW_ROUNDED)
    add(btn)
    result, set_rows = _result_panel(theme)
    add(result)

    def _calc() -> None:
        principal = _parse_float(p_field.text())
        monthly = _parse_float(m_field.text())
        rate = _parse_float(r_field.text()) / 100.0
        years = _parse_int(y_field.text(), 1)
        months = years * 12
        i = rate / 12.0 if rate else 0.0
        # Future value with regular contributions.
        if i:
            fv_principal = principal * (1 + i) ** months
            fv_contrib = monthly * (((1 + i) ** months - 1) / i)
        else:
            fv_principal = principal
            fv_contrib = monthly * months
        future_value = fv_principal + fv_contrib
        total_contrib = principal + monthly * months
        interest = future_value - total_contrib
        set_rows(
            [
                (txt["calc_result_future_value"], f"{future_value:,.0f}".replace(",", " ")),
                (txt["calc_result_total_contributions"], f"{total_contrib:,.0f}".replace(",", " ")),
                (txt["calc_result_total_interest"], f"{interest:,.0f}".replace(",", " ")),
            ]
        )

    btn.clicked.connect(_calc)
    return card


def _mortgage_calculator(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    card, add = _make_calculator(
        theme,
        title=txt["calc_section_mortgage"],
        subtitle=txt["calc_mortgage_help"],
        icon=Icons.HOME_OUTLINED,
    )
    price_row, price_field = labelled_line_edit(theme, label=txt["calc_field_price"], placeholder="4000000", initial="4000000")
    down_row, down_field = labelled_line_edit(theme, label=txt["calc_field_down_payment"], placeholder="800000", initial="800000")
    rate_row, rate_field = labelled_line_edit(theme, label=txt["calc_field_rate"], placeholder="5.5", initial="5.5")
    term_row, term_field = labelled_line_edit(theme, label=txt["calc_field_term_years"], placeholder="25", initial="25")
    add(price_row)
    add(down_row)
    add(rate_row)
    add(term_row)
    btn = PrimaryButton(txt["calc_run"], theme=theme, icon=Icons.PLAY_ARROW_ROUNDED)
    add(btn)
    result, set_rows = _result_panel(theme)
    add(result)

    def _calc() -> None:
        price = _parse_float(price_field.text())
        down = _parse_float(down_field.text())
        rate = _parse_float(rate_field.text()) / 100.0
        years = _parse_int(term_field.text(), 1)
        principal = max(0.0, price - down)
        months = years * 12
        i = rate / 12.0
        if i:
            payment = principal * i * (1 + i) ** months / ((1 + i) ** months - 1)
        else:
            payment = principal / months if months else 0.0
        total = payment * months
        set_rows(
            [
                (txt["calc_result_monthly_payment"], f"{payment:,.0f}".replace(",", " ")),
                (txt["calc_result_total_cost"], f"{total:,.0f}".replace(",", " ")),
            ]
        )

    btn.clicked.connect(_calc)
    return card


def _loan_calculator(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    card, add = _make_calculator(
        theme,
        title=txt["calc_section_loan"],
        subtitle=txt["calc_loan_help"],
        icon=Icons.PAYMENTS_OUTLINED,
    )
    income_row, income_field = labelled_line_edit(theme, label=txt["calc_field_income"], placeholder="50000", initial="50000")
    debt_row, debt_field = labelled_line_edit(theme, label=txt["calc_field_debt"], placeholder="0", initial="0")
    dti_row, dti_field = labelled_line_edit(theme, label=txt["calc_field_dti"], placeholder="35", initial="35")
    rate_row, rate_field = labelled_line_edit(theme, label=txt["calc_field_rate"], placeholder="6", initial="6")
    term_row, term_field = labelled_line_edit(theme, label=txt["calc_field_term_years"], placeholder="20", initial="20")
    add(income_row)
    add(debt_row)
    add(dti_row)
    add(rate_row)
    add(term_row)
    btn = PrimaryButton(txt["calc_run"], theme=theme, icon=Icons.PLAY_ARROW_ROUNDED)
    add(btn)
    result, set_rows = _result_panel(theme)
    add(result)

    def _calc() -> None:
        income = _parse_float(income_field.text())
        debt = _parse_float(debt_field.text())
        dti = _parse_float(dti_field.text()) / 100.0
        rate = _parse_float(rate_field.text()) / 100.0
        years = _parse_int(term_field.text(), 1)
        max_payment = max(0.0, income * dti - debt)
        months = years * 12
        i = rate / 12.0
        if i:
            max_loan = max_payment * ((1 + i) ** months - 1) / (i * (1 + i) ** months)
        else:
            max_loan = max_payment * months
        set_rows(
            [
                (txt["calc_result_max_payment"], f"{max_payment:,.0f}".replace(",", " ")),
                (txt["calc_result_max_loan"], f"{max_loan:,.0f}".replace(",", " ")),
            ]
        )

    btn.clicked.connect(_calc)
    return card


def _retirement_calculator(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    card, add = _make_calculator(
        theme,
        title=txt["calc_section_retirement"],
        subtitle=txt["calc_retirement_help"],
        icon=Icons.ELDERLY,
    )
    age_row, age_field = labelled_line_edit(theme, label=txt["calc_field_retirement_age"], placeholder="30", initial="30")
    target_age_row, target_age_field = labelled_line_edit(theme, label=txt["calc_field_retirement_target_age"], placeholder="65", initial="65")
    now_row, now_field = labelled_line_edit(theme, label=txt["calc_field_retirement_savings_now"], placeholder="50000", initial="50000")
    monthly_row, monthly_field = labelled_line_edit(theme, label=txt["calc_field_retirement_monthly"], placeholder="3000", initial="3000")
    rate_row, rate_field = labelled_line_edit(theme, label=txt["calc_field_retirement_rate"], placeholder="6", initial="6")
    add(age_row)
    add(target_age_row)
    add(now_row)
    add(monthly_row)
    add(rate_row)
    btn = PrimaryButton(txt["calc_run"], theme=theme, icon=Icons.PLAY_ARROW_ROUNDED)
    add(btn)
    result, set_rows = _result_panel(theme)
    add(result)

    def _calc() -> None:
        age = _parse_int(age_field.text(), 30)
        target = _parse_int(target_age_field.text(), 65)
        now = _parse_float(now_field.text())
        monthly = _parse_float(monthly_field.text())
        rate = _parse_float(rate_field.text()) / 100.0
        years = max(0, target - age)
        months = years * 12
        i = rate / 12.0
        if i:
            fv_principal = now * (1 + i) ** months
            fv_contrib = monthly * (((1 + i) ** months - 1) / i)
        else:
            fv_principal = now
            fv_contrib = monthly * months
        future_value = fv_principal + fv_contrib
        total_contrib = now + monthly * months
        set_rows(
            [
                (txt["calc_result_future_value"], f"{future_value:,.0f}".replace(",", " ")),
                (txt["calc_result_total_contributions"], f"{total_contrib:,.0f}".replace(",", " ")),
            ]
        )

    btn.clicked.connect(_calc)
    return card


def _savings_calculator(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    card, add = _make_calculator(
        theme,
        title=txt["calc_section_savings"],
        subtitle=txt["calc_savings_help"],
        icon=Icons.SAVINGS_OUTLINED,
    )
    current_row, current_field = labelled_line_edit(theme, label=txt["calc_field_current"], placeholder="0", initial="0")
    target_row, target_field = labelled_line_edit(theme, label=txt["calc_field_target"], placeholder="120000", initial="120000")
    months_row, months_field = labelled_line_edit(theme, label=txt["calc_field_target_months"], placeholder="12", initial="12")
    rate_row, rate_field = labelled_line_edit(theme, label=txt["calc_field_rate"], placeholder="3", initial="3")
    add(current_row)
    add(target_row)
    add(months_row)
    add(rate_row)
    btn = PrimaryButton(txt["calc_run"], theme=theme, icon=Icons.PLAY_ARROW_ROUNDED)
    add(btn)
    result, set_rows = _result_panel(theme)
    add(result)

    def _calc() -> None:
        current = _parse_float(current_field.text())
        target = _parse_float(target_field.text())
        months = max(1, _parse_int(months_field.text(), 12))
        rate = _parse_float(rate_field.text()) / 100.0
        gap = max(0.0, target - current * (1 + rate / 12.0) ** months)
        i = rate / 12.0
        if i:
            monthly = gap * i / ((1 + i) ** months - 1)
        else:
            monthly = gap / months
        set_rows(
            [
                (txt["calc_result_monthly_needed"], f"{monthly:,.0f}".replace(",", " ")),
                (
                    txt["calc_result_total_contributions"],
                    f"{(monthly * months + current):,.0f}".replace(",", " "),
                ),
            ]
        )

    btn.clicked.connect(_calc)
    return card


def _currency_calculator(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    card, add = _make_calculator(
        theme,
        title=txt["calc_section_currency"],
        subtitle=txt["calc_currency_help"],
        icon=Icons.CURRENCY_EXCHANGE,
    )
    amount_row, amount_field = labelled_line_edit(theme, label=txt["calc_field_fx_amount"], placeholder="100", initial="100")
    pair_row, pair_field = labelled_line_edit(
        theme,
        label=txt["calc_field_fx_pair"],
        hint=txt["calc_field_fx_pair_hint"],
        placeholder="USDCZK=X",
        initial="USDCZK=X",
    )
    add(amount_row)
    add(pair_row)
    btn = PrimaryButton(txt["calc_run"], theme=theme, icon=Icons.PLAY_ARROW_ROUNDED)
    add(btn)
    result, set_rows = _result_panel(theme)
    add(result)
    info = MutedLabel("", theme=theme, size=11)
    info.setVisible(False)
    add(info)

    def _calc() -> None:
        amount = _parse_float(amount_field.text())
        pair = pair_field.text().strip() or "USDCZK=X"
        if not settings_store.get_market_data_enabled():
            info.setText(txt["calc_market_disabled"])
            info.setVisible(True)
            set_rows([])
            return
        info.setVisible(False)
        btn.setEnabled(False)

        def _worker() -> None:
            try:
                fx = market_data.get_fx(pair)
            except Exception as exc:
                logger_service.log_exception(
                    "ai_finance.tab_calculators", "fx_failed", exc
                )
                fx = None

            def _apply() -> None:
                btn.setEnabled(True)
                if fx is None:
                    info.setText(txt["calc_market_unavailable"])
                    info.setVisible(True)
                    set_rows([])
                    return
                info.setVisible(False)
                converted = amount * fx
                set_rows(
                    [
                        (txt["calc_result_converted"], f"{converted:,.4f}".replace(",", " ")),
                        ("Rate", f"{fx:,.4f}".replace(",", " ")),
                    ]
                )

            from src.qt.runtime import dispatch as runtime_dispatch

            runtime_dispatch(_apply)

        threading.Thread(target=_worker, daemon=True).start()

    btn.clicked.connect(_calc)
    return card


def build_calculators_tab(theme: Theme, lang: str) -> QWidget:
    page = QWidget()
    page.setStyleSheet(f"background-color: {theme.bg};")
    outer = vbox(spacing=18, margins=(24, 20, 24, 24))
    page.setLayout(outer)

    grid_holder = QFrame()
    grid_holder.setStyleSheet("background: transparent;")
    grid = QGridLayout(grid_holder)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(18)
    grid.setVerticalSpacing(18)

    calculators = [
        _compound_calculator,
        _mortgage_calculator,
        _loan_calculator,
        _retirement_calculator,
        _savings_calculator,
        _currency_calculator,
    ]
    for index, builder in enumerate(calculators):
        try:
            widget = builder(theme, lang)
        except Exception as exc:
            logger_service.log_exception(
                "ai_finance.tab_calculators", f"calculator_{index}_failed", exc
            )
            continue
        grid.addWidget(widget, index // 2, index % 2)
    outer.addWidget(grid_holder)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(page)
    return scroll
