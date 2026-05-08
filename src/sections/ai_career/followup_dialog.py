"""Modal dialog for the optional follow-up questions step.

When the user opts into "Ask clarifying questions before each run" in
Settings, the pipeline pauses after candidate / job-spec extraction and
asks the LLM for any unclear items it spotted (Python experience, team
lead history, ...). Each question carries:

* a short ``topic`` chip,
* the ``question`` text and a ``rationale`` line,
* a list of pre-canned ``options`` (chips the user toggles),
* a ``multi_select`` flag (radio vs. checkbox behaviour),
* an ``allow_free_text`` flag that reveals an "Other" text field.

The user picks zero or more options, optionally types an Other answer, or
just leaves the row blank to skip. The dialog is opened via
``open_followup_dialog`` and triggers ``on_submit`` with a list of
``{topic, question, rationale, answer}`` dicts (the dialog flattens
multiple selections + Other text into a single human-readable answer
string), or ``on_cancel`` when the user bails out.
"""

from __future__ import annotations

from typing import Callable, Sequence

import flet as ft

from src.sections.ai_career._dialog import close_dialog as _close_dialog
from src.sections.ai_career._dialog import open_dialog as _open_dialog
from src.theme import Theme


class _QuestionRowState:
    """Tracks the user's interaction state for one question row.

    ``selected`` indexes track which options are currently picked. For
    single-select questions only one index sticks at a time; for multi-
    select the set grows / shrinks as the user toggles chips. ``other_on``
    + ``other_field`` carry the free-text answer. ``compose_answer`` joins
    everything into a single human-readable string when the dialog
    submits.
    """

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

        self.selected: set[int] = set()
        self.other_on: bool = False

        self.other_field = ft.TextField(
            hint_text=other_hint,
            multiline=True,
            min_lines=1,
            max_lines=4,
            text_style=ft.TextStyle(color=theme.text, size=13),
            hint_style=ft.TextStyle(color=theme.text_subtle, size=12),
            bgcolor=theme.surface_2,
            border=ft.InputBorder.NONE,
            filled=True,
            cursor_color=theme.primary,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border_radius=10,
            visible=False,
        )

        # Filled in by build_row(); we keep references so toggle handlers
        # can repaint just the chip controls in place.
        self.option_holders: list[ft.Container] = []
        self.other_holder: ft.Container | None = None

    # --- toggle handlers ----------------------------------------------------

    def _refresh_chip(self, idx: int) -> None:
        if 0 <= idx < len(self.option_holders):
            self.option_holders[idx].content = self._chip_view(idx)
            try:
                self.option_holders[idx].update()
            except Exception:
                pass

    def _refresh_other_chip(self) -> None:
        if self.other_holder is not None:
            self.other_holder.content = self._other_chip_view()
            try:
                self.other_holder.update()
            except Exception:
                pass

    def _toggle_option(self, idx: int) -> None:
        if self.multi_select:
            if idx in self.selected:
                self.selected.discard(idx)
            else:
                self.selected.add(idx)
            self._refresh_chip(idx)
        else:
            previously = list(self.selected)
            if idx in self.selected:
                self.selected.discard(idx)
            else:
                self.selected = {idx}
            for prev in previously:
                if prev != idx:
                    self._refresh_chip(prev)
            self._refresh_chip(idx)

    def _toggle_other(self) -> None:
        self.other_on = not self.other_on
        self.other_field.visible = self.other_on
        try:
            self.other_field.update()
        except Exception:
            pass
        self._refresh_other_chip()

    # --- chip rendering -----------------------------------------------------

    def _chip_view(self, idx: int) -> ft.Control:
        active = idx in self.selected
        return _chip(self.theme, self.options[idx], active=active)

    def _other_chip_view(self) -> ft.Control:
        return _chip(self.theme, self.other_label, active=self.other_on)

    # --- compose final answer ----------------------------------------------

    def compose_answer(self) -> str:
        parts: list[str] = []
        for idx in sorted(self.selected):
            if 0 <= idx < len(self.options):
                parts.append(self.options[idx])
        if self.other_on:
            other_text = (self.other_field.value or "").strip()
            if other_text:
                parts.append(other_text)
        return ", ".join(parts)


def _chip(theme: Theme, label: str, *, active: bool) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            label,
            color=ft.Colors.WHITE if active else theme.text,
            size=12,
            weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_500,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=7),
        bgcolor=theme.primary if active else theme.surface_2,
        border_radius=999,
        border=ft.border.all(
            1,
            theme.primary if active else theme.border,
        ),
    )


def open_followup_dialog(
    page: ft.Page,
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

    states: list[_QuestionRowState] = []

    def _question_row(q: dict) -> ft.Container:
        topic = q.get("topic") or "—"
        question_text = q.get("question") or ""
        rationale = q.get("rationale") or ""

        state = _QuestionRowState(
            question=q,
            other_label=other_label,
            other_hint=other_hint,
            theme=theme,
        )
        states.append(state)

        topic_chip = ft.Container(
            content=ft.Text(
                topic,
                color=theme.primary,
                size=11,
                weight=ft.FontWeight.W_700,
                style=ft.TextStyle(letter_spacing=0.6),
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            bgcolor=ft.Colors.with_opacity(0.14, theme.primary),
            border_radius=8,
        )

        question_block: list[ft.Control] = [
            ft.Row(controls=[topic_chip], spacing=0, tight=True),
            ft.Text(question_text, color=theme.text, size=13, weight=ft.FontWeight.W_600),
        ]
        if rationale:
            question_block.append(
                ft.Text(rationale, color=theme.text_muted, size=11, italic=True)
            )

        # Build the chip row (option chips + optional Other chip).
        chip_controls: list[ft.Control] = []
        for idx, _opt in enumerate(state.options):
            holder = ft.Container(
                content=state._chip_view(idx),
                ink=True,
                on_click=lambda _e, i=idx, st=state: st._toggle_option(i),
                border_radius=999,
            )
            state.option_holders.append(holder)
            chip_controls.append(holder)

        if state.allow_free_text or not state.options:
            other_holder = ft.Container(
                content=state._other_chip_view(),
                ink=True,
                on_click=lambda _e, st=state: st._toggle_other(),
                border_radius=999,
            )
            state.other_holder = other_holder
            chip_controls.append(other_holder)
            # When there are no options, default to having the Other field
            # already open - otherwise the user has nothing to interact with
            # except the chip.
            if not state.options:
                state.other_on = True
                state.other_field.visible = True

        if chip_controls:
            question_block.append(
                ft.Row(
                    controls=chip_controls,
                    spacing=8,
                    run_spacing=8,
                    wrap=True,
                )
            )

        question_block.append(state.other_field)

        return ft.Container(
            content=ft.Column(controls=question_block, spacing=8, tight=True),
            padding=14,
            bgcolor=theme.surface,
            border=ft.border.all(1, theme.border),
            border_radius=12,
        )

    rows = [_question_row(q) for q in questions]

    body = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(intro, color=theme.text_muted, size=12),
                ft.Container(height=4),
                *rows,
            ],
            spacing=10,
            tight=True,
            scroll=ft.ScrollMode.ADAPTIVE,
        ),
        width=620,
        height=520,
    )

    def _close() -> None:
        _close_dialog(page)

    def _build_answers() -> list[dict]:
        out: list[dict] = []
        for st in states:
            out.append(
                {
                    "topic": st.question.get("topic") or "",
                    "question": st.question.get("question") or "",
                    "rationale": st.question.get("rationale") or "",
                    "answer": st.compose_answer(),
                }
            )
        return out

    def _on_continue(_e: ft.ControlEvent) -> None:
        answered = _build_answers()
        _close()
        on_submit(answered)

    def _on_skip_all(_e: ft.ControlEvent) -> None:
        skipped: list[dict] = []
        for st in states:
            skipped.append(
                {
                    "topic": st.question.get("topic") or "",
                    "question": st.question.get("question") or "",
                    "rationale": st.question.get("rationale") or "",
                    "answer": "",
                }
            )
        _close()
        on_submit(skipped)

    def _on_cancel(_e: ft.ControlEvent) -> None:
        _close()
        on_cancel()

    skip_button = ft.TextButton(
        content=ft.Text(
            skip_all_label, color=theme.text_muted, size=12, weight=ft.FontWeight.W_500
        ),
        style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=10, vertical=8)),
        on_click=_on_skip_all,
    )
    cancel_button = ft.TextButton(
        content=ft.Text(
            cancel_label, color=theme.text, size=12, weight=ft.FontWeight.W_500
        ),
        style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=12, vertical=8)),
        on_click=_on_cancel,
    )
    continue_button = ft.TextButton(
        content=ft.Text(
            continue_label,
            color=ft.Colors.WHITE,
            size=13,
            weight=ft.FontWeight.W_600,
        ),
        style=ft.ButtonStyle(
            bgcolor=theme.primary,
            padding=ft.padding.symmetric(horizontal=18, vertical=10),
        ),
        on_click=_on_continue,
    )

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=theme.surface,
        title=ft.Text(title, color=theme.text, size=18, weight=ft.FontWeight.W_700),
        content=body,
        actions=[skip_button, cancel_button, continue_button],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    _open_dialog(page, dialog)
