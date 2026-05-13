"""Bottom message input - text field + action chips."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QSizePolicy

from src.i18n import t
from src.qt.icons import Icons
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    IconLabel,
    IconOnlyButton,
    SubtleLabel,
    hbox,
    themed_line_edit,
    vbox,
)
from src.theme import Theme


def _input_action_chip(theme: Theme, icon: str, label: str) -> ClickFrame:
    chip = ClickFrame()
    chip.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 8px;
        }}
        ClickFrame:hover {{
            background-color: {theme.surface_2};
        }}
        """
    )
    layout = hbox(spacing=6, margins=(10, 6, 10, 6))
    chip.setLayout(layout)
    layout.addWidget(IconLabel(icon, color=theme.text_muted, size=14))
    layout.addWidget(BodyLabel(label, theme=theme, size=11))
    return chip


def _send_button(theme: Theme) -> IconOnlyButton:
    btn = IconOnlyButton(
        Icons.SEND,
        color="#FFFFFF",
        size=18,
        bg=theme.primary,
        bg_hover=theme.primary_hover,
        radius=10,
    )
    btn.setFixedSize(40, 40)
    return btn


def chat_input(theme: Theme, lang: str) -> QFrame:
    container = QFrame()
    container.setStyleSheet("background: transparent;")
    container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

    outer = vbox(spacing=12, margins=(24, 12, 24, 20))
    container.setLayout(outer)

    input_row = QFrame()
    input_row.setObjectName("MockChatInputRow")
    input_row.setStyleSheet(
        f"""
        QFrame#MockChatInputRow {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 12px;
        }}
        """
    )
    row_layout = hbox(spacing=8, margins=(8, 4, 8, 4))
    input_row.setLayout(row_layout)

    attach_btn = IconOnlyButton(
        Icons.ATTACH_FILE,
        color=theme.text_muted,
        size=18,
        bg="transparent",
        bg_hover=theme.surface_2,
        tooltip=t("attach_file", lang),
    )
    row_layout.addWidget(attach_btn)

    text_field = themed_line_edit(theme, placeholder=t("type_message", lang))
    text_field.setStyleSheet(
        f"""
        QLineEdit {{
            background-color: transparent;
            border: none;
            color: {theme.text};
            padding: 12px 4px;
        }}
        """
    )
    row_layout.addWidget(text_field, 1)

    row_layout.addWidget(_send_button(theme))
    outer.addWidget(input_row)

    actions = QFrame()
    actions.setStyleSheet("background: transparent;")
    actions_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    actions.setLayout(actions_layout)
    actions_layout.addWidget(_input_action_chip(theme, Icons.ATTACH_FILE, t("attach_file", lang)))
    actions_layout.addWidget(_input_action_chip(theme, Icons.MIC_NONE_OUTLINED, t("voice_input", lang)))
    actions_layout.addWidget(_input_action_chip(theme, Icons.AUTO_FIX_HIGH, t("improve_prompt", lang)))
    actions_layout.addStretch(1)
    actions_layout.addWidget(SubtleLabel(t("ai_disclaimer", lang), theme=theme, size=11, italic=True))
    outer.addWidget(actions)

    return container
