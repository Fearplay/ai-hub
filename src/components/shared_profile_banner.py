"""Reusable "shared career profile" banner for section setup tabs.

AI Career / AI Job Search / AI LinkedIn each let the user upload a CV. Once
the user has built their shared profile in the **My Profile** section, those
sections show this banner so they can pull the same CV (+ LinkedIn / GitHub
/ notes) into the current form with one click instead of re-uploading. The
upload zones stay in place, so a per-run override is always possible.

The component is intentionally generic: it renders already-translated
strings and fires callbacks. The per-section ``shared_profile.py`` modules
own the data mapping (shared sources -> that section's in-memory state) and
the navigation, keeping section isolation intact.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QSizePolicy, QWidget

from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    FlowLayout,
    GhostButton,
    IconLabel,
    MutedLabel,
    PrimaryButton,
    hbox,
    vbox,
    wrap_label_slot,
)
from src.theme import Theme

MY_PROFILE_KEY = "my_profile"


def open_my_profile() -> None:
    """Navigate to the My Profile section (used as the banner edit action)."""
    from src.services import logger as logger_service

    try:
        from src.app import get_active_window
    except Exception as exc:
        logger_service.log_exception(
            "shared_profile_banner", "open_profile_import_failed", exc,
        )
        return
    window = get_active_window()
    if window is None:
        return
    try:
        window.set_section(MY_PROFILE_KEY)
    except Exception as exc:
        logger_service.log_exception(
            "shared_profile_banner", "open_profile_failed", exc,
        )


def shared_profile_banner(
    theme: Theme,
    *,
    title: str,
    summary: str,
    edit_label: str,
    on_edit: Callable[[], None],
    use_label: str = "",
    on_use: Optional[Callable[[], None]] = None,
    applied: bool = False,
) -> QFrame:
    """Render the shared-profile banner.

    ``applied`` flips the look from a call-to-action (accent border + a
    "use it here" button) to a confirmed state (check icon, no button).
    """
    accent = theme.primary
    card = QFrame()
    card.setObjectName("SharedProfileBanner")
    card.setStyleSheet(
        f"""
        QFrame#SharedProfileBanner {{
            background-color: {rgba(accent, 0.08)};
            border: 1px solid {rgba(accent, 0.28)};
            border-radius: 12px;
        }}
        """
    )
    # Vertical card: a [badge | text] row on top, then the action buttons
    # on their own wrapping row below. Previously the buttons sat in a
    # column to the *right* of an expanding text block, so in a narrow
    # column (e.g. AI LinkedIn's Builder with the context panel open) their
    # labels got clipped ("Pouzit zd...", "Upravit p..."). Giving them the
    # full card width - and letting them wrap via FlowLayout - keeps every
    # label fully readable at any window size.
    layout = vbox(spacing=10, margins=(14, 12, 14, 12))
    card.setLayout(layout)

    top_row = QFrame()
    top_row.setStyleSheet("background: transparent;")
    top_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    top_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    top_row.setLayout(top_layout)

    badge = QFrame()
    badge.setFixedSize(36, 36)
    badge.setStyleSheet(f"background-color: {rgba(accent, 0.16)}; border-radius: 9px;")
    bl = hbox(spacing=0, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setLayout(bl)
    bl.addWidget(
        IconLabel(
            Icons.CHECK_CIRCLE if applied else Icons.ID_CARD,
            color=accent,
            size=20,
        ),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )
    top_layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)

    text_holder = QFrame()
    text_holder.setStyleSheet("background: transparent;")
    text_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    tl = vbox(spacing=2, margins=(0, 0, 0, 0))
    text_holder.setLayout(tl)
    title_label = BodyLabel(title, theme=theme, size=13)
    title_label.setStyleSheet(f"color: {accent}; background: transparent; font-weight: 700;")
    wrap_label_slot(title_label)
    tl.addWidget(title_label)
    if summary:
        summary_label = MutedLabel(summary, theme=theme, size=11)
        wrap_label_slot(summary_label)
        tl.addWidget(summary_label)
    top_layout.addWidget(text_holder, 1)
    layout.addWidget(top_row)

    actions = QFrame()
    actions.setStyleSheet("background: transparent;")
    # ``setHeightForWidth`` lets the parent vbox grow the row to two lines
    # when FlowLayout wraps the second button on a very narrow column.
    actions_policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    actions_policy.setHeightForWidth(True)
    actions.setSizePolicy(actions_policy)
    actions_flow = FlowLayout(actions, margin=0, h_spacing=8, v_spacing=8)
    actions.setLayout(actions_flow)
    if not applied and use_label and on_use is not None:
        use_btn = PrimaryButton(use_label, theme=theme, icon=Icons.DOWNLOAD_OUTLINED)
        use_btn.clicked.connect(on_use)
        actions_flow.addWidget(use_btn)
    edit_btn = GhostButton(edit_label, theme=theme, icon=Icons.OPEN_IN_NEW)
    edit_btn.clicked.connect(on_edit)
    actions_flow.addWidget(edit_btn)
    layout.addWidget(actions)

    return card
