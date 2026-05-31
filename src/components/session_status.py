"""Left-sidebar session status block: session cost + Activity.

This replaces the per-section right context panel. Session cost is read
from the global :data:`src.services.cost_tracker.COST`; Activity is read
from the global :data:`src.services.activity_tracker.ACTIVITY`. Both are
live: the block subscribes to each tracker and patches its labels in
place (on the GUI thread via :func:`src.qt.runtime.dispatch`) so it
updates while a pipeline runs without rebuilding the sidebar.

Layout mirrors the compact "image 10" look the user asked for: an
uppercase subtle "SESSION COST" header, a calls/tokens line, the dollar
amount, then an "ACTIVITY" header with a coloured status dot + label.

Colours are accent-independent on purpose. The dot uses traffic-light
semantics (green ready / amber working / red error) and the text uses
neutral tokens, so the per-section accent restyle (``update_theme`` in
``sidebar.py``, which runs without a rebuild on section switch) never
has to touch this block - only a light/dark toggle rebuilds it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame

from src.i18n import t
from src.qt.lifecycle import is_widget_alive, on_destroyed
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.widgets import (
    MutedLabel,
    SubtleLabel,
    custom_label,
    hbox,
    vbox,
)
from src.services.activity_tracker import (
    ACTIVITY,
    CATEGORY_BUSY,
    CATEGORY_ERROR,
    CATEGORY_READY,
)
from src.services.cost_tracker import COST
from src.theme import Theme


_DOT_COLORS = {
    CATEGORY_READY: "#22C55E",
    CATEGORY_BUSY: "#F59E0B",
    CATEGORY_ERROR: "#EF4444",
}

_ACTIVITY_LABEL_KEYS = {
    CATEGORY_READY: "status_activity_ready",
    CATEGORY_BUSY: "status_activity_busy",
    CATEGORY_ERROR: "status_activity_error",
}


def session_status_block(theme: Theme, lang: str) -> QFrame:
    """Build the cost + Activity status block for the sidebar footer.

    Subscribes to ``COST`` and ``ACTIVITY`` and updates in place; the
    subscriptions are torn down automatically when the block's C++ side
    is destroyed (sidebar rebuild on a theme/language toggle).
    """
    frame = QFrame()
    frame.setObjectName("SidebarStatus")
    frame.setStyleSheet("QFrame#SidebarStatus { background: transparent; }")
    layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    frame.setLayout(layout)

    # --- session cost ------------------------------------------------------
    cost_holder = QFrame()
    cost_holder.setStyleSheet("background: transparent;")
    cost_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    cost_holder.setLayout(cost_layout)
    cost_layout.addWidget(
        SubtleLabel(
            t("status_cost_title", lang).upper(),
            theme=theme,
            size=10,
            weight=QFont.Weight.Bold,
        )
    )
    calls_label = MutedLabel("", theme=theme, size=12)
    cost_layout.addWidget(calls_label)
    amount_label = custom_label(
        "", color=theme.text, size=13, weight=QFont.Weight.Bold
    )
    cost_layout.addWidget(amount_label)
    layout.addWidget(cost_holder)

    # --- activity ----------------------------------------------------------
    act_holder = QFrame()
    act_holder.setStyleSheet("background: transparent;")
    act_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    act_holder.setLayout(act_layout)
    act_layout.addWidget(
        SubtleLabel(
            t("status_activity_title", lang).upper(),
            theme=theme,
            size=10,
            weight=QFont.Weight.Bold,
        )
    )
    dot_row = QFrame()
    dot_row.setStyleSheet("background: transparent;")
    dot_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    dot_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    dot_row.setLayout(dot_layout)
    dot = QFrame()
    dot.setFixedSize(9, 9)
    dot.setStyleSheet(
        f"background-color: {_DOT_COLORS[CATEGORY_READY]}; border-radius: 4px;"
    )
    dot_layout.addWidget(dot)
    activity_label = custom_label(
        "", color=theme.text, size=12, weight=QFont.Weight.DemiBold
    )
    dot_layout.addWidget(activity_label, 1)
    act_layout.addWidget(dot_row)
    layout.addWidget(act_holder)

    def _refresh_cost() -> None:
        if not is_widget_alive(frame):
            return
        calls_label.setText(
            t("status_cost_calls", lang).format(
                calls=COST.calls, tokens=COST.tokens_total
            )
        )
        amount_label.setText(
            t("status_cost_session", lang).format(cost=f"{COST.cost_usd:.2f}")
        )

    def _refresh_activity() -> None:
        if not is_widget_alive(frame):
            return
        category = ACTIVITY.category
        color = _DOT_COLORS.get(category, _DOT_COLORS[CATEGORY_BUSY])
        dot.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
        label = ACTIVITY.label or t(_ACTIVITY_LABEL_KEYS.get(category, "status_activity_ready"), lang)
        activity_label.setText(label)

    # Trackers fire from worker threads; hop to the GUI thread before
    # touching widgets (see qt/runtime + qt/lifecycle).
    unsub_cost = COST.subscribe(lambda: runtime_dispatch(_refresh_cost))
    unsub_activity = ACTIVITY.subscribe(lambda: runtime_dispatch(_refresh_activity))
    on_destroyed(frame, unsub_cost)
    on_destroyed(frame, unsub_activity)

    _refresh_cost()
    _refresh_activity()
    return frame
