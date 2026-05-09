"""Chat-mode body for the AI LinkedIn section.

The user types a free-form prompt, optionally attaches a CV / LinkedIn
export, and the LinkedIn voice expert replies inline. Every turn is
appended to :data:`STATE.chat_messages`; attachments parse to plain text
into :data:`STATE.chat_attachments` so subsequent prompts can reference
the same documents without re-reading the disk.

Demo mode short-circuits the network call via
:func:`src.sections.ai_linkedin.pipeline.send_chat_message`, so the chat
flow can be exercised without an API key.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from typing import Callable, Optional

import flet as ft

from src.services import logger as logger_service
from src.services.file_parser import ParsedFile, parse_file
from src.sections.ai_linkedin import pipeline
from src.sections.ai_linkedin.refs import REFS, safe
from src.sections.ai_linkedin.state import (
    MODE_BUILDER,
    STATE,
    TAB_SETUP,
)
from src.sections.ai_linkedin.strings import s
from src.theme import Theme


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.tab_chat", "request_full_refresh_import", exc,
        )
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
        content=ft.Icon(ft.Icons.HUB_OUTLINED, color=ft.Colors.WHITE, size=18),
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
        text=(
            "Hi! I'm your LinkedIn voice expert. Ask me to improve your headline,"
            " critique your About, draft a learning-update post or write a"
            " recruiter outreach DM. Switch to **Builder** mode whenever you"
            " want me to run a full profile pass."
        ),
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
        hint_text=txt["chat_placeholder"],
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

    pending_attachment: dict[str, Optional[ParsedFile]] = {"file": None}

    file_picker = ft.FilePicker()
    picker_registered: dict[str, bool] = {"done": False}

    status_text = ft.Text("", color=theme.text_muted, size=11)
    attachment_chip_holder = ft.Container(visible=False)
    drop_hint_holder = ft.Container(visible=True)
    input_row_holder = ft.Container()

    def _set_status(message: str, *, error: bool = False) -> None:
        status_text.value = message
        status_text.color = "#EF4444" if error else theme.text_muted
        logger_service.try_update(status_text)

    def _build_attachment_chip(attachment: ParsedFile) -> ft.Control:
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
        if attachment is None:
            attachment_chip_holder.content = None
            attachment_chip_holder.visible = False
            drop_hint_holder.visible = True
            input_row_holder.border = ft.border.all(
                1.5, ft.Colors.with_opacity(0.55, theme.border),
            )
            _set_status("")
        else:
            attachment_chip_holder.content = _build_attachment_chip(attachment)
            attachment_chip_holder.visible = True
            drop_hint_holder.visible = False
            input_row_holder.border = ft.border.all(1, theme.primary)
            _set_status(attachment.name)
        for c in (attachment_chip_holder, drop_hint_holder, input_row_holder):
            logger_service.try_update(c)

    def _remove_attachment(_e: ft.ControlEvent) -> None:
        pending_attachment["file"] = None
        _refresh_attachment_visuals()

    def _stage_file_from_path(path: str) -> None:
        if not path:
            return
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext not in _RESUME_EXTENSIONS:
            logger_service.log_event(
                "WARNING", "ai_linkedin.tab_chat",
                "stage_file_unsupported", ext=ext, path=path,
            )
            _set_status(f"Unsupported file: .{ext}", error=True)
            return
        parsed = parse_file(path)
        if not parsed.ok:
            logger_service.log_event(
                "WARNING", "ai_linkedin.tab_chat",
                "stage_file_parse_failed", path=path, error=parsed.error,
            )
            _set_status(parsed.error or "Could not parse file", error=True)
            return
        logger_service.log_event(
            "INFO", "ai_linkedin.tab_chat",
            "stage_file_ok", name=parsed.name, ext=ext, chars=len(parsed.text or ""),
        )
        pending_attachment["file"] = parsed
        _refresh_attachment_visuals()

    def _ensure_picker_registered(page: ft.Page) -> None:
        if picker_registered["done"]:
            return
        registry = getattr(page, "_services", None)
        if registry is not None:
            try:
                registry.register_service(file_picker)
            except Exception as exc:
                logger_service.log_exception(
                    "ai_linkedin.tab_chat", "register_picker_failed", exc,
                )
        picker_registered["done"] = True
        _try_wire_os_drop(page)

    def _try_wire_os_drop(page: ft.Page) -> None:
        if getattr(page, "_aihub_linkedin_chat_drop_wired", False):
            return
        for attr in ("on_drop", "on_file_drop", "on_files_drop"):
            handler = getattr(page, attr, "missing")
            if handler == "missing":
                continue
            try:
                def _on_drop(evt: ft.ControlEvent, _attr: str = attr) -> None:
                    raw = getattr(evt, "files", None) or getattr(evt, "paths", None) or []
                    for item in raw:
                        path = getattr(item, "path", "") or (item if isinstance(item, str) else "")
                        if path:
                            _stage_file_from_path(path)
                            break
                setattr(page, attr, _on_drop)
                logger_service.log_event(
                    "INFO", "ai_linkedin.tab_chat", "os_drop_wired", attr=attr,
                )
                break
            except Exception as exc:
                logger_service.log_exception(
                    "ai_linkedin.tab_chat", "os_drop_wire_failed", exc, attr=attr,
                )
        try:
            setattr(page, "_aihub_linkedin_chat_drop_wired", True)
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.tab_chat", "os_drop_marker_failed", exc,
            )

    async def _open_picker(e: ft.ControlEvent) -> None:
        page = e.page
        if page is None:
            return
        _ensure_picker_registered(page)
        try:
            files = await file_picker.pick_files(
                dialog_title=txt["chat_attachments_label"],
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=list(_RESUME_EXTENSIONS),
            )
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.tab_chat", "open_picker_failed", exc,
            )
            _set_status(str(exc), error=True)
            return
        if not files:
            return
        first = files[0]
        path = getattr(first, "path", "") or ""
        if path:
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

        logger_service.log_event(
            "INFO", "ai_linkedin.tab_chat",
            "send_start", chars=len(text_value), attachment=attachment_label,
            demo_mode=STATE.demo_mode,
        )

        pipeline.append_chat_message(
            "user", text_value, attachment_name=attachment_label,
        )
        text_field.value = ""
        pending_attachment["file"] = None
        _refresh_attachment_visuals()
        logger_service.try_update(text_field)
        STATE.chat_running = True
        STATE.chat_last_error = ""
        on_after_send()

        def _worker() -> None:
            try:
                assistant_text, error = pipeline.send_chat_message(
                    output_lang=lang,
                    user_text=text_value or f"(Attached {attachment_label})",
                )
            except Exception as exc:
                logger_service.log_exception(
                    "ai_linkedin.tab_chat", "send_worker_failed", exc,
                )
                assistant_text = ""
                error = str(exc) or "unexpected error"
            STATE.chat_running = False
            if error:
                STATE.chat_last_error = error
                logger_service.log_event(
                    "ERROR", "ai_linkedin.tab_chat",
                    "send_done_error", error=error,
                )
                pipeline.append_chat_message(
                    "assistant", f"_Error_: {error}",
                )
            else:
                logger_service.log_event(
                    "INFO", "ai_linkedin.tab_chat",
                    "send_done_ok", reply_chars=len(assistant_text or ""),
                )
                pipeline.append_chat_message("assistant", assistant_text)
            REFS.request_context_refresh()
            REFS.dispatch(_request_full_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    attach_btn = ft.IconButton(
        icon=ft.Icons.ATTACH_FILE,
        icon_color=theme.text_muted,
        icon_size=20,
        tooltip=txt["chat_attachments_label"],
        on_click=_open_picker,
    )
    send_btn = ft.IconButton(
        icon=ft.Icons.SEND,
        icon_color=ft.Colors.WHITE,
        icon_size=18,
        bgcolor=theme.primary,
        on_click=_send,
        tooltip=txt["sections_run_button"],
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
    input_row_holder.border = ft.border.all(
        1.5, ft.Colors.with_opacity(0.55, theme.border),
    )

    drop_hint_holder.content = ft.Row(
        controls=[
            ft.Icon(ft.Icons.UPLOAD_FILE_OUTLINED, color=theme.primary, size=14),
            ft.Text(
                txt["chat_attachments_label"],
                color=theme.text_muted,
                size=11,
                italic=True,
            ),
        ],
        spacing=6,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    drop_hint_holder.padding = ft.padding.symmetric(horizontal=10, vertical=6)
    drop_hint_holder.border_radius = 10
    drop_hint_holder.border = ft.border.all(
        1, ft.Colors.with_opacity(0.35, theme.primary),
    )
    drop_hint_holder.bgcolor = ft.Colors.with_opacity(0.06, theme.primary)
    drop_hint_holder.ink = True
    drop_hint_holder.tooltip = txt["chat_attachments_label"]
    drop_hint_holder.on_click = _open_picker

    running_text = ft.Text(
        txt["chat_running"] if STATE.chat_running else "",
        color=theme.text_muted, size=11, italic=True,
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
            try:
                assistant_text, error = pipeline.send_chat_message(
                    output_lang=lang, user_text=prompt_text,
                )
            except Exception as exc:
                logger_service.log_exception(
                    "ai_linkedin.tab_chat", "quick_send_worker_failed", exc,
                )
                assistant_text = ""
                error = str(exc) or "unexpected error"
            STATE.chat_running = False
            if error:
                STATE.chat_last_error = error
                pipeline.append_chat_message(
                    "assistant", f"_Error_: {error}",
                )
            else:
                pipeline.append_chat_message("assistant", assistant_text)
            REFS.request_context_refresh()
            REFS.dispatch(_request_full_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    return ft.Row(
        controls=[
            _quick_action_chip(
                theme,
                txt["chat_qa_improve_headline"],
                ft.Icons.TITLE,
                lambda e: _send_canned(txt["chat_qa_improve_headline"]),
            ),
            _quick_action_chip(
                theme,
                txt["chat_qa_write_learning_post"],
                ft.Icons.EDIT_OUTLINED,
                lambda e: _send_canned(txt["chat_qa_write_learning_post"]),
            ),
            _quick_action_chip(
                theme,
                txt["chat_qa_critique_about"],
                ft.Icons.SUBJECT,
                lambda e: _send_canned(txt["chat_qa_critique_about"]),
            ),
            _quick_action_chip(
                theme,
                txt["chat_qa_recruiter_dm"],
                ft.Icons.MAIL_OUTLINE,
                lambda e: _send_canned(txt["chat_qa_recruiter_dm"]),
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
    on_switch_to_builder: Callable[[], None],
) -> ft.Control:
    txt = s(lang)

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
        except Exception as exc:
            logger_service.log_exception(
                "ai_linkedin.tab_chat", "scroll_to_bottom_failed", exc,
            )

    REFS.dispatch(_scroll_to_bottom_when_ready)

    def _open_builder(_e: ft.ControlEvent) -> None:
        STATE.mode = MODE_BUILDER
        STATE.active_tab = TAB_SETUP
        on_switch_to_builder()

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
                                txt["menu_new_build"],
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
                                txt["mode_tab_builder"],
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
                    on_click=_open_builder,
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
