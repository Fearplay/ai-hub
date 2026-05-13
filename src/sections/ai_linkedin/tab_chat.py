"""Chat-mode body for the AI LinkedIn section (PySide6 port)."""

from __future__ import annotations

import os
import threading
from datetime import datetime
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from src.qt.icons import Icons
from src.qt.runtime import dispatch as runtime_dispatch
from src.qt.runtime import get_main_window
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    ClickFrame,
    GhostButton,
    IconLabel,
    IconOnlyButton,
    MutedLabel,
    SubtleLabel,
    custom_label,
    hbox,
    vbox,
)
from src.services import logger as logger_service
from src.services.file_parser import ParsedFile, parse_file
from src.sections.ai_linkedin import pipeline
from src.sections.ai_linkedin.refs import REFS
from src.sections.ai_linkedin.state import (
    MODE_BUILDER,
    STATE,
    TAB_SETUP,
)
from src.sections.ai_linkedin.strings import s
from src.theme import Theme


_RESUME_EXTENSIONS = ("pdf", "docx", "txt", "md", "html", "htm")


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_linkedin.tab_chat", "request_full_refresh_import", exc,
        )
        return
    request_section_refresh()


def _user_bubble(theme: Theme, *, text: str, time_label: str, attachment_name: str = "") -> QWidget:
    bubble = QFrame()
    bubble.setStyleSheet(f"background-color: {theme.user_bubble}; border-radius: 14px;")
    bubble_layout = vbox(spacing=6, margins=(14, 10, 14, 10))
    bubble.setLayout(bubble_layout)
    if text:
        bubble_layout.addWidget(custom_label(text, color=theme.user_bubble_text, size=14, selectable=True))
    if attachment_name:
        att = QFrame()
        att.setStyleSheet("background: transparent;")
        att_layout = hbox(spacing=6, margins=(0, 0, 0, 0))
        att.setLayout(att_layout)
        att_layout.addWidget(IconLabel(Icons.ATTACH_FILE, color=theme.user_bubble_text, size=14))
        att_layout.addWidget(custom_label(attachment_name, color=theme.user_bubble_text, size=12, weight=QFont.Weight.Medium))
        bubble_layout.addWidget(att)

    avatar = QFrame()
    avatar.setFixedSize(28, 28)
    avatar.setStyleSheet(f"background-color: {theme.primary_soft}; border-radius: 14px;")
    al = hbox(spacing=0, margins=(0, 0, 0, 0))
    al.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(al)
    al.addWidget(IconLabel(Icons.PERSON, color="#FFFFFF", size=16),
                 alignment=Qt.AlignmentFlag.AlignCenter)

    bubble_row = QFrame()
    bubble_row.setStyleSheet("background: transparent;")
    bl = hbox(spacing=10, margins=(0, 0, 0, 0))
    bl.setAlignment(Qt.AlignmentFlag.AlignBottom)
    bubble_row.setLayout(bl)
    bl.addWidget(bubble)
    bl.addWidget(avatar)

    inner = QFrame()
    inner.setStyleSheet("background: transparent;")
    inner_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    inner.setLayout(inner_layout)
    time_holder = QFrame()
    time_holder.setStyleSheet("background: transparent;")
    tl = hbox(spacing=0, margins=(0, 0, 4, 0))
    tl.setAlignment(Qt.AlignmentFlag.AlignRight)
    time_holder.setLayout(tl)
    tl.addWidget(MutedLabel(time_label, theme=theme, size=11))
    inner_layout.addWidget(time_holder)
    inner_layout.addWidget(bubble_row, 0, Qt.AlignmentFlag.AlignRight)

    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wl = QHBoxLayout(wrapper)
    wl.setContentsMargins(0, 0, 0, 0)
    wl.setSpacing(0)
    wl.addStretch(1)
    wl.addWidget(inner)
    return wrapper


def _assistant_bubble(theme: Theme, *, text: str, time_label: str) -> QWidget:
    bubble = QFrame()
    bubble.setStyleSheet(f"background-color: {theme.assistant_bubble}; border-radius: 14px;")
    bubble_layout = vbox(spacing=0, margins=(14, 14, 14, 14))
    bubble.setLayout(bubble_layout)
    text_label = BodyLabel(text or "", theme=theme, size=14, selectable=True)
    text_label.setTextFormat(Qt.TextFormat.MarkdownText)
    bubble_layout.addWidget(text_label)

    avatar = QFrame()
    avatar.setFixedSize(36, 36)
    avatar.setStyleSheet(f"background-color: {theme.primary}; border-radius: 10px;")
    al = hbox(spacing=0, margins=(0, 0, 0, 0))
    al.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(al)
    al.addWidget(IconLabel(Icons.HUB_OUTLINED, color="#FFFFFF", size=18),
                 alignment=Qt.AlignmentFlag.AlignCenter)

    body = QFrame()
    body.setStyleSheet("background: transparent;")
    body_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)
    body_layout.addWidget(MutedLabel(time_label, theme=theme, size=11))
    body_layout.addWidget(bubble)

    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wl = QHBoxLayout(wrapper)
    wl.setContentsMargins(0, 0, 0, 0)
    wl.setSpacing(12)
    wl.setAlignment(Qt.AlignmentFlag.AlignTop)
    wl.addWidget(avatar)
    wl.addWidget(body, 1)
    return wrapper


def _quick_action_chip(theme: Theme, label: str, icon: str, on_click: Callable[[], None]) -> ClickFrame:
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
    layout.addWidget(IconLabel(icon, color=theme.primary, size=14))
    layout.addWidget(BodyLabel(label, theme=theme, size=12, weight=QFont.Weight.Medium))
    chip.clicked.connect(on_click)
    return chip


def _intro_bubble(theme: Theme) -> QWidget:
    return _assistant_bubble(
        theme,
        text=(
            "Hi! I'm your LinkedIn voice expert. Ask me to improve your headline, "
            "critique your About, draft a learning-update post or write a "
            "recruiter outreach DM. Switch to **Builder** mode whenever you "
            "want me to run a full profile pass."
        ),
        time_label=datetime.now().strftime("%H:%M"),
    )


def _build_input_bar(
    theme: Theme,
    lang: str,
    txt: dict,
    on_after_send: Callable[[], None],
) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=6, margins=(24, 10, 24, 14))
    holder.setLayout(layout)

    pending_attachment: dict[str, Optional[ParsedFile]] = {"file": None}

    chip_holder = QFrame()
    chip_holder.setStyleSheet("background: transparent;")
    chip_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    chip_holder.setLayout(chip_layout)
    chip_holder.hide()
    layout.addWidget(chip_holder)

    input_row = QFrame()
    input_row.setObjectName("ChatInputRow")
    input_row.setStyleSheet(
        f"""
        QFrame#ChatInputRow {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        """
    )
    input_layout = hbox(spacing=8, margins=(10, 4, 10, 4))
    input_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    input_row.setLayout(input_layout)

    attach_btn = IconOnlyButton(Icons.ATTACH_FILE, color=theme.text_muted, size=20, bg_hover=theme.surface_2, tooltip=txt["chat_attachments_label"])
    input_layout.addWidget(attach_btn)

    field = QLineEdit()
    field.setPlaceholderText(txt["chat_placeholder"])
    field.setStyleSheet(
        f"""
        QLineEdit {{
            background: transparent;
            color: {theme.text};
            border: none;
            padding: 12px 4px;
            selection-background-color: {rgba(theme.primary, 0.30)};
            font-size: 14px;
        }}
        """
    )
    input_layout.addWidget(field, 1)

    send_btn = IconOnlyButton(Icons.SEND, color="#FFFFFF", size=18, bg=theme.primary, bg_hover=theme.primary_hover, radius=10, tooltip=txt["sections_run_button"])
    send_btn.setFixedSize(40, 40)
    input_layout.addWidget(send_btn)

    layout.addWidget(input_row)

    status_label = MutedLabel("", theme=theme, size=11)

    footer = QFrame()
    footer.setStyleSheet("background: transparent;")
    footer_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    footer.setLayout(footer_layout)
    if STATE.chat_running:
        footer_layout.addWidget(SubtleLabel(txt["chat_running"], theme=theme, size=11, italic=True))
    footer_layout.addStretch(1)
    footer_layout.addWidget(status_label)
    layout.addWidget(footer)

    def _set_status(msg: str, *, error: bool = False) -> None:
        status_label.setText(msg)
        status_label.setStyleSheet(
            f"color: {'#EF4444' if error else theme.text_muted}; background: transparent;"
        )

    def _refresh_chip() -> None:
        while chip_layout.count():
            item = chip_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        attachment = pending_attachment["file"]
        if attachment is None:
            chip_holder.hide()
            _set_status("")
            return
        chip = QFrame()
        chip.setObjectName("LinkedInChatAttachmentChip")
        chip.setStyleSheet(
            f"""
            QFrame#LinkedInChatAttachmentChip {{
                background-color: {theme.assistant_bubble};
                border: 1px solid {theme.border};
                border-radius: 999px;
            }}
            """
        )
        c_layout = hbox(spacing=4, margins=(10, 2, 2, 2))
        chip.setLayout(c_layout)
        c_layout.addWidget(IconLabel(Icons.DESCRIPTION_OUTLINED, color=theme.primary, size=14))
        c_layout.addWidget(BodyLabel(attachment.name, theme=theme, size=12, weight=QFont.Weight.Medium))
        clear = IconOnlyButton(Icons.CLOSE, color=theme.text_muted, size=14, bg_hover=theme.surface)
        clear.clicked.connect(_remove_attachment)
        c_layout.addWidget(clear)
        chip_layout.addWidget(chip)
        chip_layout.addStretch(1)
        chip_holder.show()
        _set_status(attachment.name)

    def _remove_attachment() -> None:
        pending_attachment["file"] = None
        _refresh_chip()

    def _stage_file(path: str) -> None:
        if not path:
            return
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext not in _RESUME_EXTENSIONS:
            _set_status(f"Unsupported file: .{ext}", error=True)
            return
        parsed = parse_file(path)
        if not parsed.ok:
            _set_status(parsed.error or "Could not parse file", error=True)
            return
        pending_attachment["file"] = parsed
        _refresh_chip()

    def _open_picker() -> None:
        path, _ = QFileDialog.getOpenFileName(
            get_main_window(),
            txt["chat_attachments_label"],
            "",
            "Documents (*.pdf *.docx *.txt *.md *.html *.htm)",
        )
        if path:
            _stage_file(path)

    attach_btn.clicked.connect(_open_picker)

    def _send() -> None:
        if STATE.chat_running:
            return
        text_value = field.text().strip()
        attachment = pending_attachment["file"]
        if not text_value and attachment is None:
            return
        attachment_label = ""
        if attachment is not None:
            STATE.chat_attachments[attachment.name] = attachment.text
            attachment_label = attachment.name

        pipeline.append_chat_message("user", text_value, attachment_name=attachment_label)
        field.clear()
        pending_attachment["file"] = None
        _refresh_chip()
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
                pipeline.append_chat_message("assistant", f"_Error_: {error}")
            else:
                pipeline.append_chat_message("assistant", assistant_text)
            REFS.request_context_refresh()
            REFS.dispatch(_request_full_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    field.returnPressed.connect(_send)
    send_btn.clicked.connect(_send)
    return holder


def _quick_actions(theme: Theme, lang: str, txt: dict, on_after_send: Callable[[], None]) -> QFrame:
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
    holder.setLayout(layout)

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
                pipeline.append_chat_message("assistant", f"_Error_: {error}")
            else:
                pipeline.append_chat_message("assistant", assistant_text)
            REFS.request_context_refresh()
            REFS.dispatch(_request_full_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    layout.addWidget(_quick_action_chip(theme, txt["chat_qa_improve_headline"], Icons.TITLE, lambda: _send_canned(txt["chat_qa_improve_headline"])))
    layout.addWidget(_quick_action_chip(theme, txt["chat_qa_write_learning_post"], Icons.EDIT_OUTLINED, lambda: _send_canned(txt["chat_qa_write_learning_post"])))
    layout.addWidget(_quick_action_chip(theme, txt["chat_qa_critique_about"], Icons.SUBJECT, lambda: _send_canned(txt["chat_qa_critique_about"])))
    layout.addWidget(_quick_action_chip(theme, txt["chat_qa_recruiter_dm"], Icons.MAIL_OUTLINE, lambda: _send_canned(txt["chat_qa_recruiter_dm"])))
    layout.addStretch(1)
    return holder


def build_chat_tab(
    theme: Theme,
    lang: str,
    *,
    on_request_rerender: Callable[[], None],
    on_navigate_tab: Callable[[int], None],
    on_switch_to_builder: Callable[[], None],
) -> QWidget:
    txt = s(lang)

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    header_row = QFrame()
    header_row.setStyleSheet("background: transparent;")
    header_layout = hbox(spacing=8, margins=(24, 12, 24, 4))
    header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    header_row.setLayout(header_layout)
    header_layout.addStretch(1)

    def _clear_chat() -> None:
        STATE.reset_chat()
        on_request_rerender()

    def _open_builder() -> None:
        STATE.mode = MODE_BUILDER
        STATE.active_tab = TAB_SETUP
        on_switch_to_builder()

    new_btn = GhostButton(txt["menu_new_build"], theme=theme, icon=Icons.RESTART_ALT)
    new_btn.clicked.connect(_clear_chat)
    header_layout.addWidget(new_btn)
    builder_btn = GhostButton(txt["mode_tab_builder"], theme=theme, icon=Icons.GRID_VIEW_OUTLINED)
    builder_btn.clicked.connect(_open_builder)
    header_layout.addWidget(builder_btn)
    layout.addWidget(header_row)

    messages_holder = QWidget()
    messages_holder.setStyleSheet(f"background-color: {theme.bg};")
    msgs_layout = vbox(spacing=18, margins=(24, 20, 24, 20))
    messages_holder.setLayout(msgs_layout)
    if not STATE.chat_messages:
        msgs_layout.addWidget(_intro_bubble(theme))
    else:
        for msg in STATE.chat_messages:
            if msg.role == "user":
                msgs_layout.addWidget(_user_bubble(theme, text=msg.text, time_label=msg.time, attachment_name=msg.attachment_name))
            else:
                msgs_layout.addWidget(_assistant_bubble(theme, text=msg.text, time_label=msg.time))
    msgs_layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
    scroll.setWidget(messages_holder)
    layout.addWidget(scroll, 1)

    qa_holder = QFrame()
    qa_holder.setStyleSheet("background: transparent;")
    qa_layout = hbox(spacing=0, margins=(24, 4, 24, 4))
    qa_holder.setLayout(qa_layout)
    qa_layout.addWidget(_quick_actions(theme, lang, txt, on_request_rerender))
    layout.addWidget(qa_holder)

    layout.addWidget(_build_input_bar(theme, lang, txt, on_request_rerender))

    def _scroll_to_bottom() -> None:
        bar = scroll.verticalScrollBar()
        if bar is not None:
            bar.setValue(bar.maximum())

    runtime_dispatch(_scroll_to_bottom)
    return container
