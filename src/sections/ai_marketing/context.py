"""AI Marketing - right-hand panel (Brief, Quick actions, Recent conversations)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QSizePolicy, QWidget

from src.components.context_panel import (
    context_panel_shell,
    history_column,
    quick_actions_column,
)
from src.components.section_card import section_card
from src.i18n import t
from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import BodyLabel, MutedLabel, hbox, vbox
from src.sections.ai_marketing.data import brief_fields, history, quick_actions
from src.sections.ai_marketing.strings import s
from src.theme import Theme


def _brief_field(theme: Theme, *, label: str, value: str, chip: bool = False) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    holder.setLayout(layout)

    layout.addWidget(MutedLabel(label, theme=theme, size=11))

    if chip:
        chip_holder = QFrame()
        chip_holder.setStyleSheet("background: transparent;")
        chip_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
        chip_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        chip_holder.setLayout(chip_layout)
        chip_widget = QFrame()
        chip_widget.setStyleSheet(
            f"background-color: {rgba(theme.primary, 0.18)}; border-radius: 12px;"
        )
        chip_widget.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        cw_layout = hbox(spacing=0, margins=(10, 4, 10, 4))
        chip_widget.setLayout(cw_layout)
        cw_layout.addWidget(BodyLabel(value, theme=theme, size=12))
        chip_layout.addWidget(chip_widget)
        layout.addWidget(chip_holder)
    else:
        layout.addWidget(BodyLabel(value, theme=theme, size=13))

    return holder


def _brief_content(theme: Theme, lang: str) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=12, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    for field in brief_fields(lang):
        layout.addWidget(
            _brief_field(
                theme,
                label=field["label"],
                value=field["value"],
                chip=field.get("chip", False),
            )
        )
    return holder


def build_context(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    return context_panel_shell(
        theme,
        section_card(theme, icon=Icons.DESCRIPTION_OUTLINED, title=txt["brief_title"], body=_brief_content(theme, lang)),
        section_card(theme, icon=Icons.BOLT_OUTLINED, title=t("quick_actions", lang),
                     body=quick_actions_column(theme, quick_actions(lang))),
        section_card(theme, icon=Icons.HISTORY, title=t("recent_conversations", lang),
                     body=history_column(theme, history(lang))),
    )
