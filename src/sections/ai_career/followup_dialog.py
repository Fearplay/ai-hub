"""Modal dialog for the optional follow-up questions step.

When the user opts into "Ask clarifying questions before each run" in
Settings, the pipeline pauses after candidate / job-spec extraction and
asks the LLM for any unclear items it spotted (Python experience, team
lead history, …). Each question is rendered as a row with topic, question
text, rationale, and an answer field. The user may answer or skip each
question individually.

The dialog is opened via ``open_followup_dialog`` and triggers ``on_submit``
with a list of ``{topic, question, rationale, answer}`` dicts when the
user clicks Continue, or ``on_cancel`` when they bail out.
"""

from __future__ import annotations

from typing import Callable, Sequence

import flet as ft

from src.theme import Theme


def _open_dialog(page: ft.Page, dialog: ft.AlertDialog) -> None:
    """Flet 0.84 uses page.show_dialog(dlg); older releases used page.open(dlg)."""
    try:
        page.show_dialog(dialog)
        return
    except AttributeError:
        pass
    try:
        page.open(dialog)  # type: ignore[attr-defined]
    except Exception:
        page.dialog = dialog  # type: ignore[attr-defined]
        try:
            page.update()
        except Exception:
            pass


def _close_dialog(page: ft.Page) -> None:
    """Flet 0.84 uses page.pop_dialog(); older releases used page.close(dlg)."""
    try:
        page.pop_dialog()
        return
    except AttributeError:
        pass
    try:
        page.close(None)  # type: ignore[attr-defined]
    except Exception:
        pass


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
    questions: Sequence[dict],
    on_submit: Callable[[list[dict]], None],
    on_cancel: Callable[[], None],
) -> None:
    if not questions:
        # No questions - nothing to ask, treat as immediate submit.
        on_submit([])
        return

    field_refs: list[tuple[dict, ft.TextField]] = []

    def _question_row(q: dict) -> ft.Container:
        topic = q.get("topic") or "—"
        question_text = q.get("question") or ""
        rationale = q.get("rationale") or ""

        answer_field = ft.TextField(
            hint_text=answer_hint,
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
        )
        field_refs.append((q, answer_field))

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
        question_block.append(answer_field)

        return ft.Container(
            content=ft.Column(controls=question_block, spacing=6, tight=True),
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

    def _on_continue(_e: ft.ControlEvent) -> None:
        answered: list[dict] = []
        for q, field in field_refs:
            answer = (field.value or "").strip()
            answered.append(
                {
                    "topic": q.get("topic") or "",
                    "question": q.get("question") or "",
                    "rationale": q.get("rationale") or "",
                    "answer": answer,
                }
            )
        _close()
        on_submit(answered)

    def _on_skip_all(_e: ft.ControlEvent) -> None:
        skipped: list[dict] = []
        for q, _field in field_refs:
            skipped.append(
                {
                    "topic": q.get("topic") or "",
                    "question": q.get("question") or "",
                    "rationale": q.get("rationale") or "",
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
