"""Chat-mode body for the AI Career section (Version B).

The Chat tab is the conversational counterpart to the structured Form
mode. The user types in a free-form prompt, optionally attaches a CV or
job posting, and the HR-expert assistant replies inline. Every turn is
appended to :data:`STATE.chat_messages`; attachments parse to plain
text and live in :data:`STATE.chat_attachments` so subsequent prompts
can reference the same documents without re-reading the disk.

Demo mode short-circuits the network call via
:func:`src.sections.ai_career.pipeline.send_chat_message`, so the chat
flow can be exercised without an API key.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from typing import Callable, Optional

import flet as ft

from src.services.file_parser import ParsedFile, parse_file
from src.sections.ai_career import pipeline
from src.sections.ai_career.refs import REFS, safe
from src.sections.ai_career.state import (
    MODE_FORM,
    STATE,
    TAB_SETUP,
)
from src.sections.ai_career.strings import s
from src.theme import Theme


def _request_full_refresh() -> None:
    """Trigger a full section rebuild from anywhere in this module."""
    try:
        from src.app import request_section_refresh
    except Exception:
        return
    request_section_refresh()


_RESUME_EXTENSIONS = ("pdf", "docx", "txt", "md", "html", "htm")


def _user_bubble(theme: Theme, *, text: str, time_label: str, attachment_name: str = "") -> ft.Row:
    body_children: list[ft.Control] = []
    if text:
        body_children.append(
            ft.Text(text, color=theme.user_bubble_text, size=14, selectable=True)
        )
    if attachment_name:
        body_children.append(
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ATTACH_FILE, color=theme.user_bubble_text, size=14),
                    ft.Text(
                        attachment_name,
                        color=theme.user_bubble_text,
                        size=12,
                        weight=ft.FontWeight.W_500,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
                spacing=6,
                tight=True,
            )
        )

    bubble = ft.Container(
        content=ft.Column(controls=body_children, spacing=6, tight=True),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        bgcolor=theme.user_bubble,
        border_radius=14,
    )
    avatar = ft.Container(
        content=ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE, size=16),
        width=28,
        height=28,
        bgcolor=theme.primary_soft,
        border_radius=14,
        alignment=ft.Alignment.CENTER,
    )
    return ft.Row(
        controls=[
            ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Text(time_label, color=theme.text_muted, size=11),
                        padding=ft.padding.only(right=4),
                        alignment=ft.Alignment.CENTER_RIGHT,
                    ),
                    ft.Row(
                        controls=[bubble, avatar],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                        tight=True,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.END,
                spacing=4,
                tight=True,
            ),
        ],
        alignment=ft.MainAxisAlignment.END,
    )


def _assistant_bubble(theme: Theme, *, text: str, time_label: str) -> ft.Row:
    body = ft.Container(
        content=ft.Markdown(
            text or "",
            extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
            selectable=True,
        ),
        padding=14,
        bgcolor=theme.assistant_bubble,
        border_radius=14,
    )
    avatar = ft.Container(
        content=ft.Icon(ft.Icons.WORK_OUTLINE, color=ft.Colors.WHITE, size=18),
        width=36,
        height=36,
        bgcolor=theme.primary,
        border_radius=10,
        alignment=ft.Alignment.CENTER,
    )
    return ft.Row(
        controls=[
            avatar,
            ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Text(time_label, color=theme.text_muted, size=11),
                        padding=ft.padding.only(left=4),
                    ),
                    body,
                ],
                spacing=4,
                expand=True,
                tight=True,
            ),
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def _intro_bubble(theme: Theme, txt: dict) -> ft.Row:
    return _assistant_bubble(
        theme,
        text=txt["chat_mode_greeting"],
        time_label=datetime.now().strftime("%H:%M"),
    )


def _quick_action_chip(
    theme: Theme,
    label: str,
    icon: str,
    on_click: Callable[[ft.ControlEvent], None],
) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=theme.primary, size=14),
                ft.Text(label, color=theme.text, size=12, weight=ft.FontWeight.W_500),
            ],
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        bgcolor=theme.surface,
        border_radius=8,
        border=ft.border.all(1, theme.border),
        ink=True,
        on_click=on_click,
    )


def _message_list(theme: Theme, txt: dict, list_ref: ft.Ref[ft.ListView]) -> ft.ListView:
    bubbles: list[ft.Control] = []
    if not STATE.chat_messages:
        bubbles.append(_intro_bubble(theme, txt))
    else:
        for msg in STATE.chat_messages:
            if msg.role == "user":
                bubbles.append(
                    _user_bubble(
                        theme,
                        text=msg.text,
                        time_label=msg.time,
                        attachment_name=msg.attachment_name,
                    )
                )
            else:
                bubbles.append(
                    _assistant_bubble(
                        theme,
                        text=msg.text,
                        time_label=msg.time,
                    )
                )

    return ft.ListView(
        ref=list_ref,
        controls=bubbles,
        spacing=18,
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        expand=True,
        auto_scroll=True,
    )


def _input_bar(
    theme: Theme,
    lang: str,
    txt: dict,
    *,
    on_after_send: Callable[[], None],
) -> ft.Container:
    text_field = ft.TextField(
        hint_text=txt["chat_mode_send_hint"],
        hint_style=ft.TextStyle(color=theme.text_subtle, size=13),
        text_style=ft.TextStyle(color=theme.text, size=14),
        border=ft.InputBorder.NONE,
        filled=False,
        bgcolor="transparent",
        cursor_color=theme.primary,
        content_padding=ft.padding.symmetric(horizontal=4, vertical=12),
        expand=True,
        multiline=True,
        min_lines=1,
        max_lines=4,
    )

    file_picker = ft.FilePicker()
    picker_registered: dict[str, bool] = {"done": False}
    pending_attachment: dict[str, Optional[ParsedFile]] = {"file": None}

    status_text = ft.Text("", color=theme.text_muted, size=11)
    # Holders we re-render whenever the staged attachment changes so the
    # chip + drop-target affordance stay in sync with reality.
    attachment_chip_holder = ft.Container(visible=False)
    drop_hint_holder = ft.Container(visible=True)
    input_row_holder = ft.Container()

    def _set_status(message: str, *, error: bool = False) -> None:
        status_text.value = message
        status_text.color = "#EF4444" if error else theme.text_muted
        try:
            status_text.update()
        except Exception:
            pass

    def _build_attachment_chip(attachment: ParsedFile) -> ft.Control:
        """Removable pill above the input row showing the staged file."""
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, color=theme.primary, size=14),
                    ft.Text(
                        attachment.name,
                        color=theme.text,
                        size=12,
                        weight=ft.FontWeight.W_500,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=14,
                        icon_color=theme.text_muted,
                        tooltip=txt["chat_mode_attachment_remove"],
                        on_click=_remove_attachment,
                        padding=0,
                    ),
                ],
                spacing=4,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.only(left=10, right=2, top=2, bottom=2),
            bgcolor=theme.assistant_bubble,
            border_radius=999,
            border=ft.border.all(1, theme.border),
        )

    def _refresh_attachment_visuals() -> None:
        attachment = pending_attachment["file"]
        # NOTE on real OS-level file drop:
        # Flet 0.84 does not surface OS drag-and-drop events on the
        # ``flet pack`` runtime we ship through ``build_exe.bat`` (the
        # only renderer that supports it - flet-dropzone - requires
        # ``flet build`` + Flutter SDK + Visual Studio C++ workload,
        # which violates the "no prerequisites" promise from
        # ``build-exe.mdc``). The dashed border + hint label below are a
        # *visual* affordance: clicking anywhere in the input row opens
        # the file picker, which is functionally equivalent to dropping
        # a file. Revisit if/when we move off ``flet pack``.
        if attachment is None:
            attachment_chip_holder.content = None
            attachment_chip_holder.visible = False
            drop_hint_holder.visible = True
            input_row_holder.border = ft.border.all(
                1.5, ft.Colors.with_opacity(0.55, theme.border)
            )
            _set_status("")
        else:
            attachment_chip_holder.content = _build_attachment_chip(attachment)
            attachment_chip_holder.visible = True
            drop_hint_holder.visible = False
            input_row_holder.border = ft.border.all(1, theme.primary)
            _set_status(txt["chat_mode_attached_template"].format(name=attachment.name))
        for c in (attachment_chip_holder, drop_hint_holder, input_row_holder):
            try:
                c.update()
            except Exception:
                pass

    def _remove_attachment(_e: ft.ControlEvent) -> None:
        pending_attachment["file"] = None
        _refresh_attachment_visuals()

    def _stage_file_from_path(path: str) -> None:
        if not path:
            return
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext not in _RESUME_EXTENSIONS:
            _set_status(txt["resume_unsupported"], error=True)
            return
        parsed = parse_file(path)
        if not parsed.ok:
            _set_status(parsed.error or txt["resume_unsupported"], error=True)
            return
        pending_attachment["file"] = parsed
        _refresh_attachment_visuals()

    async def _open_picker(_e: ft.ControlEvent) -> None:
        page = _e.page
        if page is None:
            return
        if not picker_registered["done"]:
            registry = getattr(page, "_services", None)
            if registry is not None:
                try:
                    registry.register_service(file_picker)
                except Exception:
                    pass
            picker_registered["done"] = True
        try:
            files = await file_picker.pick_files(
                dialog_title=txt["chat_mode_input_attach"],
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=list(_RESUME_EXTENSIONS),
            )
        except Exception:
            files = []
        if not files:
            return
        first = files[0]
        path = getattr(first, "path", "") or ""
        _stage_file_from_path(path)

    def _send(_e: Optional[ft.ControlEvent] = None) -> None:
        if STATE.chat_running:
            return
        text_value = (text_field.value or "").strip()
        attachment = pending_attachment["file"]
        if not text_value and attachment is None:
            return

        if attachment is not None:
            STATE.chat_attachments[attachment.name] = attachment.text
            attachment_label = attachment.name
        else:
            attachment_label = ""

        pipeline.append_chat_message(
            "user",
            text_value,
            attachment_name=attachment_label,
        )
        text_field.value = ""
        pending_attachment["file"] = None
        _refresh_attachment_visuals()
        try:
            text_field.update()
        except Exception:
            pass
        STATE.chat_running = True
        STATE.chat_last_error = ""
        on_after_send()

        def _worker() -> None:
            assistant_text, error = pipeline.send_chat_message(
                output_lang=lang,
                user_text=text_value or f"(Attached {attachment_label})",
            )
            STATE.chat_running = False
            if error:
                STATE.chat_last_error = error
                pipeline.append_chat_message(
                    "assistant",
                    txt["chat_mode_error_template"].format(error=error),
                )
            else:
                pipeline.append_chat_message("assistant", assistant_text)
            safe(REFS.rerender_context)
            REFS.dispatch(_request_full_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    attach_btn = ft.IconButton(
        icon=ft.Icons.ATTACH_FILE,
        icon_color=theme.text_muted,
        icon_size=20,
        tooltip=txt["chat_mode_input_attach"],
        on_click=_open_picker,
    )
    send_btn = ft.IconButton(
        icon=ft.Icons.SEND,
        icon_color=ft.Colors.WHITE,
        icon_size=18,
        bgcolor=theme.primary,
        on_click=_send,
        tooltip=txt["footer_run_btn"],
    )

    text_field.on_submit = lambda e: _send(e)

    input_row_holder.content = ft.Row(
        controls=[attach_btn, text_field, send_btn],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    input_row_holder.padding = ft.padding.symmetric(horizontal=10, vertical=4)
    input_row_holder.bgcolor = theme.surface
    input_row_holder.border_radius = 14
    # Subtle accent border so the input visually invites a file drop.
    # See the long comment in ``_refresh_attachment_visuals`` for why
    # real OS drop is not wired.
    input_row_holder.border = ft.border.all(
        1.5, ft.Colors.with_opacity(0.55, theme.border)
    )

    drop_hint_holder.content = ft.Row(
        controls=[
            ft.Icon(ft.Icons.UPLOAD_FILE_OUTLINED, color=theme.text_muted, size=12),
            ft.Text(
                txt["chat_mode_drop_hint"],
                color=theme.text_muted,
                size=11,
                italic=True,
            ),
        ],
        spacing=6,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    drop_hint_holder.padding = ft.padding.only(left=4, top=2, bottom=2)

    running_text = ft.Text(
        txt["chat_mode_running"] if STATE.chat_running else "",
        color=theme.text_muted,
        size=11,
        italic=True,
    )

    footer_row = ft.Row(
        controls=[
            running_text,
            ft.Container(expand=True),
            status_text,
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                attachment_chip_holder,
                drop_hint_holder,
                input_row_holder,
                footer_row,
            ],
            spacing=6,
            tight=True,
        ),
        padding=ft.padding.only(left=24, right=24, top=10, bottom=14),
    )


def _quick_actions(theme: Theme, lang: str, txt: dict, on_after_send: Callable[[], None]) -> ft.Row:
    def _send_canned(prompt_text: str) -> None:
        if STATE.chat_running:
            return
        pipeline.append_chat_message("user", prompt_text)
        STATE.chat_running = True
        on_after_send()

        def _worker() -> None:
            assistant_text, error = pipeline.send_chat_message(
                output_lang=lang,
                user_text=prompt_text,
            )
            STATE.chat_running = False
            if error:
                STATE.chat_last_error = error
                pipeline.append_chat_message(
                    "assistant",
                    txt["chat_mode_error_template"].format(error=error),
                )
            else:
                pipeline.append_chat_message("assistant", assistant_text)
            safe(REFS.rerender_context)
            REFS.dispatch(_request_full_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    return ft.Row(
        controls=[
            _quick_action_chip(
                theme,
                txt["chat_mode_quick_action_cv"],
                ft.Icons.DESCRIPTION_OUTLINED,
                lambda e: _send_canned(txt["chat_mode_quick_action_cv"]),
            ),
            _quick_action_chip(
                theme,
                txt["chat_mode_quick_action_letter"],
                ft.Icons.MAIL_OUTLINE,
                lambda e: _send_canned(txt["chat_mode_quick_action_letter"]),
            ),
            _quick_action_chip(
                theme,
                txt["chat_mode_quick_action_interview"],
                ft.Icons.QUESTION_ANSWER_OUTLINED,
                lambda e: _send_canned(txt["chat_mode_quick_action_interview"]),
            ),
            _quick_action_chip(
                theme,
                txt["chat_mode_quick_action_gaps"],
                ft.Icons.QUERY_STATS,
                lambda e: _send_canned(txt["chat_mode_quick_action_gaps"]),
            ),
        ],
        spacing=8,
        wrap=True,
        run_spacing=8,
    )


def build_chat_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
    on_switch_to_form: Callable[[], None],
) -> ft.Control:
    txt = s(lang)

    # Keep a Ref so we can ``scroll_to`` after the section rebuild lands
    # in the page tree. ``auto_scroll=True`` only kicks in when controls
    # are appended after mount; on a full rebuild every bubble is
    # already in ``controls`` so the freshly-built ListView sits at
    # offset 0 - which is what was sliding the conversation back to the
    # start every time the AI replied.
    list_ref: ft.Ref[ft.ListView] = ft.Ref[ft.ListView]()
    list_holder = ft.Container(content=_message_list(theme, txt, list_ref), expand=True)
    quick_actions_holder = ft.Container(
        content=_quick_actions(theme, lang, txt, on_request_rerender),
    )
    input_holder = ft.Container(
        content=_input_bar(theme, lang, txt, on_after_send=on_request_rerender),
    )

    def _scroll_to_bottom_when_ready() -> None:
        lv = list_ref.current
        if lv is None:
            return
        try:
            lv.scroll_to(offset=-1, duration=0)
        except Exception:
            pass

    # Schedule the scroll once the rebuild is on-screen. ``REFS.dispatch``
    # routes the call through the page's asyncio loop so the ListView
    # has been mounted by the time we ask it to scroll.
    REFS.dispatch(_scroll_to_bottom_when_ready)

    def _open_form_mode(_e: ft.ControlEvent) -> None:
        STATE.mode = MODE_FORM
        STATE.active_tab = TAB_SETUP
        on_switch_to_form()

    def _clear_chat(_e: ft.ControlEvent) -> None:
        STATE.reset_chat()
        on_request_rerender()

    header_row = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.RESTART_ALT, color=theme.text_muted, size=14),
                            ft.Text(
                                txt["chat_mode_clear_btn"],
                                color=theme.text,
                                size=12,
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                        spacing=6,
                        tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    bgcolor=theme.surface,
                    border_radius=8,
                    border=ft.border.all(1, theme.border),
                    ink=True,
                    on_click=_clear_chat,
                ),
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.GRID_VIEW_OUTLINED, color=theme.primary, size=14),
                            ft.Text(
                                txt["chat_mode_open_form_btn"],
                                color=theme.text,
                                size=12,
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                        spacing=6,
                        tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    bgcolor=theme.surface,
                    border_radius=8,
                    border=ft.border.all(1, theme.border),
                    ink=True,
                    on_click=_open_form_mode,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(left=24, right=24, top=12, bottom=4),
    )

    return ft.Column(
        controls=[
            header_row,
            ft.Container(content=list_holder, expand=True),
            ft.Container(
                content=quick_actions_holder,
                padding=ft.padding.only(left=24, right=24, top=4, bottom=4),
            ),
            input_holder,
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
