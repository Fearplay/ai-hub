"""AI Finance - right-hand context panel.

Four cards stacked vertically:

1. Activity + cost - the dot indicator and a per-session cost line.
2. Quick actions - "Create budget", "Analyse expenses", etc. wired
   directly to ``STATE.active_tab`` so the centre column repaints.
3. Markets - live tickers via :mod:`src.services.market_data`. The
   user picks which symbols to track via the in-card ``Upravit``
   editor; the list lives in ``settings.json`` (read/written through
   :func:`src.services.settings_store.get_finance_tickers` and
   :func:`set_finance_tickers`). Empty list / disabled toggle / fetch
   error each render their own empty-state copy - no mock data.
4. Recent analyses + tip card. Both render empty-state hints when the
   user has not finished an analysis yet.

The panel is rerendered on demand through :func:`REFS.request_context_refresh`.
Workers in :mod:`src.sections.ai_finance.pipeline` set state then
trigger the refresh - they never touch widgets directly.
"""

from __future__ import annotations

import threading
import time
from typing import Optional, Sequence

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.components.context_panel import (
    context_panel_shell,
    history_row,
    quick_action_row,
)
from src.components.section_card import section_card
from src.qt.icons import Icons
from src.qt.lifecycle import is_widget_alive, on_destroyed
from src.qt.runtime import get_main_window
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    GhostButton,
    IconLabel,
    IconOnlyButton,
    MutedLabel,
    PrimaryButton,
    SubtleLabel,
    TitleLabel,
    custom_label,
    hbox,
    vbox,
)
from src.services import logger as logger_service
from src.services import settings_store
from src.services.cost_tracker import COST
from src.sections.ai_finance import pipeline
from src.sections.ai_finance.data import (
    TREND_DOWN,
    TREND_UP,
    market_meta_for,
    quick_actions,
)
from src.sections.ai_finance.refs import REFS
from src.sections.ai_finance.state import (
    STATE,
    TAB_ANALYSIS,
    TAB_BUDGET,
    TAB_CALCULATORS,
    TAB_INVEST,
    TAB_TAXES,
)
from src.sections.ai_finance.strings import s
from src.theme import Theme


SPARK_WIDTH = 64
SPARK_HEIGHT = 26
MARKETS_REFRESH_SECONDS = 60.0


_ACTIVITY_KEYS = {
    "ready": "activity_ready",
    "thinking": "activity_thinking",
    "analyzing": "activity_analyzing",
    "generating": "activity_generating",
    "exporting": "activity_exporting",
    "error": "activity_error",
}


_QUICK_ACTION_TARGETS = {
    "quick_create_budget": TAB_BUDGET,
    "quick_analyze_expenses": TAB_ANALYSIS,
    "quick_invest_advice": TAB_INVEST,
    "quick_tax_guide": TAB_TAXES,
    "quick_calculators": TAB_CALCULATORS,
}


_ICON_OVERRIDES = {
    "^GSPC": Icons.PUBLIC,
    "^IXIC": Icons.MEMORY,
    "^DJI": Icons.ACCOUNT_BALANCE_OUTLINED,
    "BTC-USD": Icons.CURRENCY_BITCOIN,
    "EURCZK=X": Icons.EURO,
}


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_finance.context", "request_full_refresh_import", exc
        )
        return
    request_section_refresh()


class _Sparkline(QWidget):
    """Tiny line chart painted via ``QPainter`` - same widget as before."""

    def __init__(self, values: Sequence[float], *, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._values = list(values) or [0.0, 0.0]
        self._color = QColor(color)
        self.setFixedSize(SPARK_WIDTH, SPARK_HEIGHT)

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._values:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        lo = min(self._values)
        hi = max(self._values)
        span = (hi - lo) or 1.0

        margin_y = 3
        plot_h = SPARK_HEIGHT - 2 * margin_y
        step_x = SPARK_WIDTH / max(1, len(self._values) - 1)

        points = QPolygonF()
        for i, v in enumerate(self._values):
            x = i * step_x
            y = margin_y + (1 - (v - lo) / span) * plot_h
            points.append(QPointF(x, y))

        pen = QPen(self._color, 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPolyline(points)


def _format_value(value: float) -> str:
    if value == 0.0:
        return "-"
    if abs(value) >= 1000:
        return f"{value:,.2f}".replace(",", " ")
    return f"{value:,.4f}".replace(",", " ")


def _format_change(pct: float) -> str:
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.2f}%"


def _ticker_row(theme: Theme, ticker: dict) -> ClickFrame:
    trend = ticker.get("trend") or ("up" if (ticker.get("change_pct") or 0) >= 0 else "down")
    trend_color = (
        TREND_UP if trend == "up"
        else TREND_DOWN if trend == "down"
        else theme.text_muted
    )

    row = ClickFrame()
    row.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: transparent;
            border-radius: 8px;
        }}
        ClickFrame:hover {{
            background-color: {theme.surface_2};
        }}
        """
    )
    layout = hbox(spacing=10, margins=(4, 6, 4, 6))
    row.setLayout(layout)

    icon_color = ticker.get("icon_color") or "#94A3B8"
    icon = ticker.get("icon") or _ICON_OVERRIDES.get(ticker.get("symbol", ""), Icons.PUBLIC)
    icon_box = QFrame()
    icon_box.setFixedSize(28, 28)
    icon_box.setStyleSheet(
        f"background-color: {icon_color}; border-radius: 8px;"
    )
    ib = hbox(spacing=0, margins=(0, 0, 0, 0))
    ib.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setLayout(ib)
    ib.addWidget(IconLabel(icon, color="#FFFFFF", size=14),
                 alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(icon_box)

    name_value = QFrame()
    name_value.setStyleSheet("background: transparent;")
    name_value.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    nv_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    name_value.setLayout(nv_layout)
    symbol = ticker.get("symbol_label") or ticker.get("symbol") or ""
    nv_layout.addWidget(BodyLabel(symbol, theme=theme, size=12))
    value_label = ticker.get("value") or _format_value(ticker.get("last", 0.0))
    nv_layout.addWidget(MutedLabel(value_label, theme=theme, size=11))
    layout.addWidget(name_value, 1)

    layout.addWidget(_Sparkline(ticker.get("spark") or [], color=trend_color))

    change_text = ticker.get("change") or _format_change(ticker.get("change_pct", 0.0))
    change_label = QLabel(change_text)
    change_font = QFont()
    change_font.setPixelSize(11)
    change_font.setWeight(QFont.Weight.Bold)
    change_label.setFont(change_font)
    change_label.setStyleSheet(f"color: {trend_color}; background: transparent;")
    layout.addWidget(change_label)
    return row


def _ticker_label(txt: dict, symbol: str, fallback: str) -> str:
    """Return a localised ticker label when we have one."""
    if symbol == "^GSPC":
        return txt["ticker_sp500"]
    if symbol == "^IXIC":
        return txt["ticker_nasdaq"]
    if symbol == "^DJI":
        return txt["ticker_dow"]
    if symbol == "BTC-USD":
        return txt["ticker_btc"]
    if symbol == "EURCZK=X":
        return txt["ticker_eur"]
    return fallback or symbol


def _live_tickers(lang: str) -> list[dict]:
    """Map ``STATE.markets`` (LiveQuote payload) onto the panel format."""
    txt = s(lang)
    if not STATE.markets:
        return []
    rows: list[dict] = []
    for q in STATE.markets:
        symbol = q.get("symbol", "")
        friendly, color = market_meta_for(symbol)
        friendly = _ticker_label(txt, symbol, friendly)
        rows.append({
            "symbol": symbol,
            "symbol_label": friendly,
            "icon": _ICON_OVERRIDES.get(symbol, Icons.SHOW_CHART),
            "icon_color": color,
            "last": q.get("last", 0.0),
            "change_pct": q.get("change_pct", 0.0),
            "trend": q.get("trend") or ("up" if (q.get("change_pct") or 0) >= 0 else "down"),
            "spark": q.get("spark") or [],
        })
    return rows


def _markets_body(theme: Theme, lang: str) -> QFrame:
    """Live-only Markets body. Empty-state copy when nothing is live.

    The Markets card never falls back to mock tickers - if the toggle
    is off, no symbols are configured, the fetch is in flight, or the
    fetch failed, the user sees an explicit hint instead of fake data
    (see :func:`_open_tickers_dialog` for the editor entry point).
    """
    txt = s(lang)
    rows_holder = QFrame()
    rows_holder.setStyleSheet("background: transparent;")
    rows_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    rows_holder.setLayout(rows_layout)

    live_rows = _live_tickers(lang)
    enabled = settings_store.get_market_data_enabled()
    configured = settings_store.get_finance_tickers()

    if not enabled:
        rows_layout.addWidget(
            SubtleLabel(txt["calc_market_disabled"], theme=theme, size=11, italic=True)
        )
        return rows_holder
    if not configured:
        rows_layout.addWidget(
            SubtleLabel(txt["markets_empty_no_tickers"], theme=theme, size=11, italic=True)
        )
        return rows_holder
    if STATE.markets_error and not live_rows:
        # ``markets_error`` holds either a localisation key (e.g. set
        # by ``refresh_markets`` on a zero-quote response) or a raw
        # exception string. Try the localised version first so the user
        # always sees translated copy when we have it.
        error_msg = txt.get(STATE.markets_error)
        if not error_msg:
            error_msg = txt["markets_error_generic"].format(
                error=STATE.markets_error
            )
        rows_layout.addWidget(custom_label(
            error_msg, color="#EF4444", size=11, italic=True,
        ))
        return rows_holder
    if not live_rows:
        if STATE.markets_loading:
            # Show the user's saved watchlist immediately while live data
            # is still in flight so the card does not look empty.
            for symbol in configured[:5]:
                fallback_name, color = market_meta_for(symbol)
                rows_layout.addWidget(_ticker_row(theme, {
                    "symbol": symbol,
                    "symbol_label": _ticker_label(txt, symbol, fallback_name),
                    "icon": _ICON_OVERRIDES.get(symbol, Icons.SHOW_CHART),
                    "icon_color": color,
                    "value": "...",
                    "change": "...",
                    "trend": "flat",
                    "spark": [],
                }))
            rows_layout.addWidget(
                SubtleLabel(txt["markets_loading"], theme=theme, size=11, italic=True)
            )
        else:
            rows_layout.addWidget(
                SubtleLabel(txt["markets_empty_no_data"], theme=theme, size=11, italic=True)
            )
        return rows_holder

    for ticker in live_rows:
        rows_layout.addWidget(_ticker_row(theme, ticker))
    return rows_holder


def _activity_body(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    activity_key = _ACTIVITY_KEYS.get(STATE.activity, "activity_ready")
    label = txt.get(activity_key) or txt["activity_ready"]
    color = "#22C55E" if STATE.activity == "ready" else (
        "#EF4444" if STATE.activity == "error" else theme.primary
    )

    row = QFrame()
    row.setStyleSheet("background: transparent;")
    rl = hbox(spacing=8, margins=(0, 0, 0, 0))
    rl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    row.setLayout(rl)
    dot = QFrame()
    dot.setFixedSize(10, 10)
    dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
    rl.addWidget(dot)
    rl.addWidget(BodyLabel(label, theme=theme, size=13, weight=QFont.Weight.DemiBold), 1)
    layout.addWidget(row)

    if STATE.last_error and STATE.activity == "error":
        layout.addWidget(custom_label(STATE.last_error, color="#EF4444", size=11))

    provider = settings_store.get_provider()
    model_label = settings_store.get_model()
    layout.addWidget(BodyLabel(
        f"{COST.calls} / {COST.tokens_total} tok",
        theme=theme, size=12,
    ))
    layout.addWidget(SubtleLabel(
        f"${COST.cost_usd:.4f} - {provider.title()} - {model_label}",
        theme=theme, size=11, italic=True,
    ))
    return holder


def _quick_actions_card(theme: Theme, lang: str) -> QFrame:
    rows = QFrame()
    rows.setStyleSheet("background: transparent;")
    rows_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    rows.setLayout(rows_layout)

    raw_actions = quick_actions(lang)
    for action in raw_actions:
        label = action["label"]
        icon = action["icon"]
        # match label back to a tab via the string key in `quick_actions`
        target_tab = None
        txt = s(lang)
        for key, tab in _QUICK_ACTION_TARGETS.items():
            if txt.get(key) == label:
                target_tab = tab
                break
        row = quick_action_row(theme, icon, label)

        def _handler(t=target_tab) -> None:
            if t is None:
                return
            if t == STATE.active_tab:
                return
            STATE.active_tab = t
            logger_service.log_event(
                "INFO", "ai_finance.context", "quick_action_navigate",
                new_tab=t,
            )
            _request_full_refresh()

        if target_tab is not None and hasattr(row, "clicked"):
            row.clicked.connect(_handler)
        rows_layout.addWidget(row)
    return rows


def _analyses_card(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    rows = QFrame()
    rows.setStyleSheet("background: transparent;")
    rows_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    rows.setLayout(rows_layout)
    if STATE.runs_history:
        for run in STATE.runs_history[:5]:
            title = run.get("title") or "AI Finance"
            timestamp = run.get("timestamp") or ""
            short = timestamp.split("T")[1][:5] if "T" in timestamp else timestamp
            rows_layout.addWidget(history_row(theme, title, short or "-"))
    else:
        rows_layout.addWidget(
            SubtleLabel(txt["analyses_empty"], theme=theme, size=11, italic=True)
        )
    return rows


def _tip_body(theme: Theme, lang: str) -> QWidget:
    """Render the AI-generated tip card body.

    Three states:

    * ``STATE.tip_running`` -> shimmer label.
    * ``STATE.tip`` populated -> title + body + next-step pill +
      "Generate new tip" button.
    * Empty -> static empty-state copy plus a button to kick off a
      generation if at least one analysis already exists.
    """
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    if STATE.tip_running:
        layout.addWidget(SubtleLabel(txt["tip_thinking"], theme=theme, size=12, italic=True))
        return holder

    tip = STATE.tip
    if isinstance(tip, dict) and (tip.get("title") or tip.get("body")):
        title = tip.get("title") or ""
        body = tip.get("body") or ""
        next_step = tip.get("next_step") or ""
        if title:
            layout.addWidget(BodyLabel(title, theme=theme, size=13, weight=QFont.Weight.DemiBold))
        if body:
            layout.addWidget(BodyLabel(body, theme=theme, size=12, selectable=True))
        if next_step:
            step_holder = QFrame()
            step_holder.setStyleSheet(
                f"background-color: {theme.surface_2}; border-radius: 8px;"
            )
            step_layout = vbox(spacing=2, margins=(10, 8, 10, 8))
            step_holder.setLayout(step_layout)
            step_layout.addWidget(SubtleLabel(txt["tip_next_step_label"], theme=theme, size=10, italic=True))
            step_layout.addWidget(BodyLabel(next_step, theme=theme, size=12, selectable=True))
            layout.addWidget(step_holder)
    else:
        layout.addWidget(BodyLabel(txt["tip_empty"], theme=theme, size=12, selectable=True))

    # "Generate new tip" button - only enabled if at least one analysis
    # is cached on STATE; otherwise the tip generator returns early
    # anyway and the user just gets the empty state again.
    if STATE.has_any_analysis():
        btn = GhostButton(txt["tip_regenerate_btn"], theme=theme, icon=Icons.AUTO_AWESOME)
        btn.setMinimumHeight(28)
        btn.setStyleSheet(
            btn.styleSheet() + "QPushButton { padding: 4px 12px; font-size: 11px; }"
        )
        btn.setToolTip(txt["tip_regenerate_tooltip"])
        btn.clicked.connect(lambda: _on_regenerate_tip(lang))
        layout.addWidget(btn)
    return holder


def _on_regenerate_tip(lang: str) -> None:
    """Spawn a daemon thread that regenerates the AI tip from STATE."""

    def _worker() -> None:
        try:
            pipeline.generate_tip(output_lang=lang)
        except Exception as exc:
            logger_service.log_exception(
                "ai_finance.context", "regenerate_tip_failed", exc,
            )

    threading.Thread(target=_worker, daemon=True).start()


def _open_tickers_dialog(theme: Theme, lang: str) -> None:
    """Modal editor for the live Markets ticker list.

    The list is persisted via :func:`settings_store.set_finance_tickers`
    and the panel + the next live fetch are rerendered immediately on
    save so the user sees the result without leaving the section.
    """
    txt = s(lang)
    parent = get_main_window()

    dialog = QDialog(parent)
    dialog.setWindowTitle(txt["markets_edit_title"])
    dialog.setModal(True)
    dialog.setStyleSheet(f"QDialog {{ background-color: {theme.bg}; }}")
    dialog.setMinimumWidth(420)
    dialog.setMaximumWidth(560)

    outer = vbox(spacing=14, margins=(20, 20, 20, 20))
    dialog.setLayout(outer)

    outer.addWidget(TitleLabel(txt["markets_edit_title"], theme=theme, size=16))
    outer.addWidget(MutedLabel(txt["markets_edit_hint"], theme=theme, size=12))

    rows_holder = QFrame()
    rows_holder.setStyleSheet("background: transparent;")
    rows_layout = vbox(spacing=8, margins=(0, 0, 0, 0))
    rows_holder.setLayout(rows_layout)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setStyleSheet("QScrollArea { background: transparent; }")
    scroll.setMinimumHeight(200)
    scroll.setMaximumHeight(320)
    scroll.setWidget(rows_holder)
    outer.addWidget(scroll, 1)

    state: dict[str, list[str]] = {
        "symbols": list(settings_store.get_finance_tickers())
    }

    def _refresh_rows() -> None:
        while rows_layout.count():
            item = rows_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
        if not state["symbols"]:
            rows_layout.addWidget(
                MutedLabel(txt["markets_edit_empty"], theme=theme, size=12)
            )
        for idx, symbol in enumerate(state["symbols"]):
            row = QFrame()
            row.setStyleSheet(
                f"background-color: {theme.surface}; border-radius: 8px;"
            )
            row.setMaximumWidth(520)
            rl = hbox(spacing=10, margins=(10, 8, 10, 8))
            rl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            row.setLayout(rl)
            friendly, color = market_meta_for(symbol)
            badge = QFrame()
            badge.setFixedSize(8, 8)
            badge.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
            rl.addWidget(badge)
            label_holder = QFrame()
            label_holder.setStyleSheet("background: transparent;")
            label_holder.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            ll = vbox(spacing=2, margins=(0, 0, 0, 0))
            label_holder.setLayout(ll)
            ll.addWidget(BodyLabel(symbol, theme=theme, size=12))
            ll.addWidget(MutedLabel(friendly, theme=theme, size=11))
            rl.addWidget(label_holder, 1)

            remove_btn = QPushButton("X")
            remove_btn.setFixedSize(28, 28)
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: transparent;
                    color: {theme.text_muted};
                    border: 1px solid {theme.border};
                    border-radius: 6px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {theme.surface_2};
                    color: #EF4444;
                }}
                """
            )

            def _make_remove(target_idx: int):
                def _remove() -> None:
                    if 0 <= target_idx < len(state["symbols"]):
                        del state["symbols"][target_idx]
                        _refresh_rows()
                return _remove

            remove_btn.clicked.connect(_make_remove(idx))
            rl.addWidget(remove_btn)
            rows_layout.addWidget(row)
        rows_layout.addStretch(1)

    _refresh_rows()

    add_row = QFrame()
    add_row.setStyleSheet("background: transparent;")
    add_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    add_row.setLayout(add_layout)
    add_input = QLineEdit()
    add_input.setPlaceholderText(txt["markets_edit_add_hint"])
    add_input.setStyleSheet(
        f"""
        QLineEdit {{
            background-color: {theme.surface};
            color: {theme.text};
            border: 1px solid {theme.border};
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 12px;
        }}
        QLineEdit:focus {{ border: 1px solid {theme.primary}; }}
        """
    )
    add_layout.addWidget(add_input, 1)
    add_btn = PrimaryButton(txt["markets_edit_add"], theme=theme, icon=Icons.ADD)

    def _on_add() -> None:
        raw = (add_input.text() or "").strip().upper()
        if not raw:
            return
        if raw in state["symbols"]:
            add_input.clear()
            return
        state["symbols"].append(raw)
        add_input.clear()
        _refresh_rows()

    add_btn.clicked.connect(_on_add)
    add_input.returnPressed.connect(_on_add)
    add_layout.addWidget(add_btn)
    outer.addWidget(add_row)

    actions_row = QFrame()
    actions_row.setStyleSheet("background: transparent;")
    actions_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    actions_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
    actions_row.setLayout(actions_layout)
    cancel_btn = GhostButton(txt["markets_edit_cancel"], theme=theme)
    cancel_btn.clicked.connect(dialog.reject)
    actions_layout.addWidget(cancel_btn)
    save_btn = PrimaryButton(txt["markets_edit_save"], theme=theme, icon=Icons.SAVE_OUTLINED)

    def _on_save() -> None:
        try:
            settings_store.set_finance_tickers(list(state["symbols"]))
            logger_service.log_event(
                "INFO", "ai_finance.context", "tickers_saved",
                count=len(state["symbols"]),
            )
        except Exception as exc:
            logger_service.log_exception(
                "ai_finance.context", "tickers_save_failed", exc,
            )
            return
        dialog.accept()
        STATE.markets = []
        STATE.markets_fetched_at = 0.0
        STATE.markets_error = ""
        REFS.request_context_refresh()
        _maybe_refresh_markets()

    save_btn.clicked.connect(_on_save)
    actions_layout.addWidget(save_btn)
    outer.addWidget(actions_row)

    dialog.exec()


# Throttle for the daemon thread that refreshes live tickers. We only
# spawn one fetch even if `build_context` is called repeatedly during a
# single language toggle.
_MARKETS_THREAD_LOCK = threading.Lock()
_MARKETS_LAST_FETCH: dict[str, float] = {"at": 0.0}


def _maybe_refresh_markets() -> None:
    if not settings_store.get_market_data_enabled():
        return
    now = time.time()
    last_at = max(STATE.markets_fetched_at, _MARKETS_LAST_FETCH["at"])
    if now - last_at < MARKETS_REFRESH_SECONDS and STATE.markets:
        return
    if STATE.markets_loading:
        return
    if not _MARKETS_THREAD_LOCK.acquire(blocking=False):
        return
    _MARKETS_LAST_FETCH["at"] = now

    def _worker() -> None:
        try:
            pipeline.refresh_markets()
        except Exception as exc:
            logger_service.log_exception(
                "ai_finance.context", "refresh_markets_worker_failed", exc
            )
        finally:
            try:
                _MARKETS_THREAD_LOCK.release()
            except Exception:
                pass

    threading.Thread(target=_worker, daemon=True).start()


def _force_refresh_markets() -> None:
    """Bypass the 60-second throttle and refetch live quotes now.

    Wired to the icon-only refresh button next to the Edit button. We
    clear ``markets_fetched_at`` AND the in-process ``_MARKETS_LAST_FETCH``
    cache so :func:`_maybe_refresh_markets` actually spawns a worker
    even if the previous fetch finished a few seconds ago. The card
    rerenders immediately so the loading state is visible while the
    daemon thread is in flight.
    """
    if not settings_store.get_market_data_enabled():
        return
    STATE.markets_fetched_at = 0.0
    STATE.markets_error = ""
    _MARKETS_LAST_FETCH["at"] = 0.0
    STATE.markets_loading = True
    REFS.request_context_refresh()
    logger_service.log_event(
        "INFO", "ai_finance.context", "markets_refresh_clicked"
    )
    _maybe_refresh_markets()


def _markets_card(theme: Theme, lang: str) -> QWidget:
    """Markets card with refresh + Edit buttons in the header.

    The refresh button skips the 60-second throttle so the user can
    actively pull new quotes; the Edit button opens the ticker editor.
    Both live in a tiny ``QFrame`` because :func:`section_card`'s
    ``trailing`` slot only accepts a single widget.
    """
    txt = s(lang)
    actions_holder = QFrame()
    actions_holder.setStyleSheet("background: transparent;")
    actions_layout = hbox(spacing=6, margins=(0, 0, 0, 0))
    actions_holder.setLayout(actions_layout)

    refresh_btn = IconOnlyButton(
        Icons.REFRESH,
        color=theme.text_muted,
        size=16,
        bg_hover=theme.surface_2,
        tooltip=txt["markets_refresh_tooltip"],
    )
    refresh_btn.clicked.connect(_force_refresh_markets)
    actions_layout.addWidget(refresh_btn)

    edit_btn = GhostButton(
        txt["markets_edit"], theme=theme, icon=Icons.EDIT_OUTLINED
    )
    edit_btn.setMinimumHeight(28)
    edit_btn.setStyleSheet(edit_btn.styleSheet() + "QPushButton { padding: 4px 10px; font-size: 11px; }")
    edit_btn.clicked.connect(lambda: _open_tickers_dialog(theme, lang))
    actions_layout.addWidget(edit_btn)

    return section_card(
        theme,
        icon=Icons.SHOW_CHART,
        title=txt["markets_title"],
        body=_markets_body(theme, lang),
        trailing=actions_holder,
    )


def build_context(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    panel_holder = QFrame()
    panel_holder.setStyleSheet("background: transparent;")
    panel_layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    panel_holder.setLayout(panel_layout)

    def _clear() -> None:
        if not is_widget_alive(panel_holder):
            return
        while panel_layout.count():
            item = panel_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _render() -> None:
        if not is_widget_alive(panel_holder):
            return
        _clear()
        cards: list[QWidget] = [
            section_card(
                theme,
                icon=Icons.INSIGHTS_OUTLINED,
                title=txt["activity_ready"] if STATE.activity == "ready" else txt["activity_thinking"].rstrip("."),
                body=_activity_body(theme, lang),
            ),
            section_card(
                theme,
                icon=Icons.BOLT_OUTLINED,
                title=txt["quick_title"],
                body=_quick_actions_card(theme, lang),
            ),
            _markets_card(theme, lang),
            section_card(
                theme,
                icon=Icons.HISTORY,
                title=txt["analyses_title"],
                body=_analyses_card(theme, lang),
            ),
            section_card(
                theme,
                icon=Icons.LIGHTBULB_OUTLINE,
                title=txt["tip_title"],
                body=_tip_body(theme, lang),
            ),
        ]
        shell = context_panel_shell(theme, *cards)
        panel_layout.addWidget(shell)

    REFS.rerender_context = _render

    def _on_panel_destroyed() -> None:
        if REFS.rerender_context is _render:
            REFS.rerender_context = None

    on_destroyed(panel_holder, _on_panel_destroyed)

    _render()

    QTimer.singleShot(50, _maybe_refresh_markets)

    return panel_holder
