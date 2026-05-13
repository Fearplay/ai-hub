"""Modal dialog for the optional follow-up questions step (PySide6 port).

Cloned from :mod:`src.sections.ai_career.followup_dialog` so the
LinkedIn section stays isolated per the section contract.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.qt.dialog import BaseDialog
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    MutedLabel,
    SubtleLabel,
    custom_label,
    hbox,
    themed_text_edit,
    vbox,
)
from src.theme import Theme


class _QuestionRowState:
    def __init__(
        self,
        *,
        question: dict,
        other_label: str,
        other_hint: str,
        theme: Theme,
    ) -> None:
        self.question = question
        self.options: list[str] = list(question.get("options") or [])
        self.multi_select: bool = bool(question.get("multi_select"))
        self.allow_free_text: bool = bool(question.get("allow_free_text", True))
        self.theme = theme
        self.other_label = other_label
        self.other_hint = other_hint

        self.selected: set[int] = set()
        self.other_on: bool = False

        self.other_field = themed_text_edit(theme, placeholder=other_hint, min_height=60)
        self.other_field.setVisible(False)

        self.option_chips: list[ClickFrame] = []
        self.other_chip: Optional[ClickFrame] = None

    def _update_chip(self, chip: ClickFrame, label: str, *, active: bool) -> None:
        chip.setStyleSheet(_chip_qss(self.theme, active=active))
        layout = chip.layout()
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        layout.addWidget(custom_label(
            label,
            color="#FFFFFF" if active else self.theme.text,
            size=12,
            weight=QFont.Weight.DemiBold if active else QFont.Weight.Medium,
        ))

    def toggle_option(self, idx: int) -> None:
        if self.multi_select:
            if idx in self.selected:
                self.selected.discard(idx)
            else:
                self.selected.add(idx)
        else:
            self.selected = set() if idx in self.selected else {idx}
        for i, chip in enumerate(self.option_chips):
            self._update_chip(chip, self.options[i], active=i in self.selected)

    def toggle_other(self) -> None:
        self.other_on = not self.other_on
        self.other_field.setVisible(self.other_on)
        if self.other_chip is not None:
            self._update_chip(self.other_chip, self.other_label, active=self.other_on)

    def compose_answer(self) -> str:
        parts: list[str] = []
        for idx in sorted(self.selected):
            if 0 <= idx < len(self.options):
                parts.append(self.options[idx])
        if self.other_on:
            other_text = self.other_field.toPlainText().strip()
            if other_text:
                parts.append(other_text)
        return ", ".join(parts)


def _chip_qss(theme: Theme, *, active: bool) -> str:
    bg = theme.primary if active else theme.surface_2
    border = theme.primary if active else theme.border
    return f"""
        ClickFrame {{
            background-color: {bg};
            border: 1px solid {border};
            border-radius: 999px;
        }}
        ClickFrame:hover {{
            border: 1px solid {theme.primary};
        }}
    """


def _make_chip(theme: Theme, label: str, *, active: bool) -> ClickFrame:
    chip = ClickFrame()
    chip.setStyleSheet(_chip_qss(theme, active=active))
    layout = hbox(spacing=0, margins=(12, 7, 12, 7))
    chip.setLayout(layout)
    layout.addWidget(custom_label(
        label,
        color="#FFFFFF" if active else theme.text,
        size=12,
        weight=QFont.Weight.DemiBold if active else QFont.Weight.Medium,
    ))
    return chip


def open_followup_dialog(
    parent: Optional[QWidget],
    theme: Theme,
    *,
    title: str,
    intro: str,
    cancel_label: str,
    continue_label: str,
    answer_hint: str,
    skip_all_label: str,
    other_label: str,
    other_hint: str,
    questions: Sequence[dict],
    on_submit: Callable[[list[dict]], None],
    on_cancel: Callable[[], None],
) -> None:
    if not questions:
        on_submit([])
        return

    dialog = BaseDialog(parent=parent, theme=theme, title=title, width=680, height=620)
    states: list[_QuestionRowState] = []

    body_holder = QWidget()
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body_holder.setLayout(body_layout)
    body_layout.addWidget(MutedLabel(intro, theme=theme, size=12))
    body_layout.addSpacing(4)

    for q in questions:
        state = _QuestionRowState(question=q, other_label=other_label, other_hint=other_hint, theme=theme)
        states.append(state)

        card = QFrame()
        card.setObjectName("LinkedInFollowupQuestionCard")
        card.setStyleSheet(
            f"""
            QFrame#LinkedInFollowupQuestionCard {{
                background-color: {theme.surface};
                border: 1px solid {theme.border};
                border-radius: 12px;
            }}
            """
        )
        card_layout = vbox(spacing=8, margins=(14, 14, 14, 14))
        card.setLayout(card_layout)

        topic = (q.get("topic") or "—").strip()
        topic_holder = QFrame()
        topic_holder.setStyleSheet("background: transparent; border: none;")
        topic_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
        topic_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        topic_holder.setLayout(topic_layout)
        topic_chip = QFrame()
        topic_chip.setStyleSheet(
            f"background-color: {rgba(theme.primary, 0.14)}; border: none; border-radius: 8px;"
        )
        tc_layout = hbox(spacing=0, margins=(10, 4, 10, 4))
        topic_chip.setLayout(tc_layout)
        tc_layout.addWidget(custom_label(topic, color=theme.primary, size=11, weight=QFont.Weight.Bold))
        topic_layout.addWidget(topic_chip)
        card_layout.addWidget(topic_holder)

        card_layout.addWidget(BodyLabel(q.get("question") or "", theme=theme, size=13, weight=QFont.Weight.DemiBold))
        if q.get("rationale"):
            card_layout.addWidget(SubtleLabel(q["rationale"], theme=theme, size=11, italic=True))

        if state.options or state.allow_free_text:
            chips_holder = QFrame()
            chips_holder.setStyleSheet("background: transparent; border: none;")
            chips_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
            chips_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            chips_holder.setLayout(chips_layout)

            for idx, opt in enumerate(state.options):
                chip = _make_chip(theme, opt, active=False)
                state.option_chips.append(chip)
                chip.clicked.connect(lambda i=idx, st=state: st.toggle_option(i))
                chips_layout.addWidget(chip)

            if state.allow_free_text or not state.options:
                other_chip = _make_chip(theme, other_label, active=False)
                state.other_chip = other_chip
                other_chip.clicked.connect(lambda st=state: st.toggle_other())
                chips_layout.addWidget(other_chip)
                if not state.options:
                    state.toggle_other()
            chips_layout.addStretch(1)
            card_layout.addWidget(chips_holder)

        card_layout.addWidget(state.other_field)
        body_layout.addWidget(card)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.surface}; border: none; }}")
    scroll.setWidget(body_holder)
    scroll.setMinimumHeight(420)
    dialog.body_layout.addWidget(scroll)

    def _build_answers() -> list[dict]:
        out: list[dict] = []
        for st in states:
            out.append({
                "topic": st.question.get("topic") or "",
                "question": st.question.get("question") or "",
                "rationale": st.question.get("rationale") or "",
                "answer": st.compose_answer(),
            })
        return out

    def _on_skip() -> None:
        skipped: list[dict] = []
        for st in states:
            skipped.append({
                "topic": st.question.get("topic") or "",
                "question": st.question.get("question") or "",
                "rationale": st.question.get("rationale") or "",
                "answer": "",
            })
        dialog.accept()
        on_submit(skipped)

    def _on_cancel() -> None:
        dialog.reject()
        on_cancel()

    def _on_continue() -> None:
        answers = _build_answers()
        dialog.accept()
        on_submit(answers)

    skip_btn = QPushButton(skip_all_label)
    skip_btn.setStyleSheet(
        f"QPushButton {{ background: transparent; color: {theme.text_muted}; border: none; padding: 8px 10px; }}"
    )
    cancel_btn = QPushButton(cancel_label)
    cancel_btn.setStyleSheet(
        f"QPushButton {{ background: transparent; color: {theme.text}; border: none; padding: 8px 12px; }}"
    )
    continue_btn = QPushButton(continue_label)
    continue_btn.setStyleSheet(
        f"""
        QPushButton {{
            background-color: {theme.primary};
            color: #FFFFFF;
            border: none;
            border-radius: 8px;
            padding: 10px 18px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background-color: {theme.primary_hover}; }}
        """
    )

    dialog.add_action(skip_btn, on_click=_on_skip)
    dialog.add_action(cancel_btn, on_click=_on_cancel)
    dialog.add_action(continue_btn, on_click=_on_continue)
    dialog.exec()
