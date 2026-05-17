"""Chat tab for AI Finance.

Mirrors the AI Career chat pattern: assistant bubbles + a single input
bar at the bottom. The greeting starts as a friendly intro and only
upgrades to the donut + breakdown visual once the user has run the
Budget tab and ``STATE.budget`` is populated - the chat never paints
fabricated numbers.
"""

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
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
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
    wrap_label_slot,
)
from src.services import logger as logger_service
from src.services import settings_store
from src.services.file_parser import ParsedFile, parse_file
from src.sections.ai_finance import data as finance_data
from src.sections.ai_finance import pipeline
from src.sections.ai_finance._widgets import (
    budget_slices_from_plan,
    breakdown_table,
    card_title,
    donut_with_caption,
    legend_for_splits,
    section_card,
)
from src.sections.ai_finance.refs import REFS
from src.sections.ai_finance.state import (
    STATE,
    TAB_ANALYSIS,
    TAB_BUDGET,
    TAB_CALCULATORS,
    TAB_INVEST,
    TAB_TAXES,
)
from src.sections.ai_finance.strings import s
from src.theme import Theme


SUPPORTED_EXTENSIONS = ("pdf", "docx", "txt", "md", "html", "htm", "csv")


def _request_full_refresh() -> None:
    try:
        from src.app import request_section_refresh
    except Exception as exc:
        logger_service.log_exception(
            "ai_finance.tab_chat", "request_full_refresh_import", exc
        )
        return
    request_section_refresh()


def _user_bubble(theme: Theme, *, text: str, time_label: str, attachment_name: str = "") -> QWidget:
    bubble = QFrame()
    bubble.setStyleSheet(f"background-color: {theme.user_bubble}; border-radius: 14px;")
    bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
    bubble.setMaximumWidth(520)
    bubble_layout = vbox(spacing=6, margins=(14, 10, 14, 10))
    bubble.setLayout(bubble_layout)
    if text:
        bubble_layout.addWidget(
            custom_label(text, color=theme.user_bubble_text, size=14, selectable=True)
        )
    if attachment_name:
        att = QFrame()
        att.setStyleSheet("background: transparent;")
        att_layout = hbox(spacing=6, margins=(0, 0, 0, 0))
        att.setLayout(att_layout)
        att_layout.addWidget(IconLabel(Icons.ATTACH_FILE, color=theme.user_bubble_text, size=14))
        att_layout.addWidget(
            custom_label(attachment_name, color=theme.user_bubble_text, size=12, weight=QFont.Weight.Medium)
        )
        bubble_layout.addWidget(att)

    avatar = QFrame()
    avatar.setFixedSize(28, 28)
    avatar.setStyleSheet(f"background-color: {theme.primary_soft}; border-radius: 14px;")
    al = hbox(spacing=0, margins=(0, 0, 0, 0))
    al.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(al)
    al.addWidget(IconLabel(Icons.PERSON, color="#FFFFFF", size=16), alignment=Qt.AlignmentFlag.AlignCenter)

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


def _assistant_bubble(theme: Theme, *, text: str, time_label: str, extra: Optional[QWidget] = None) -> QWidget:
    bubble = QFrame()
    bubble.setStyleSheet(f"background-color: {theme.assistant_bubble}; border-radius: 14px;")
    bubble_layout = vbox(spacing=14, margins=(16, 14, 16, 14))
    bubble.setLayout(bubble_layout)
    if text:
        text_label = BodyLabel(text, theme=theme, size=14, selectable=True)
        text_label.setTextFormat(Qt.TextFormat.MarkdownText)
        text_label.setWordWrap(True)
        bubble_layout.addWidget(text_label)
    if extra is not None:
        bubble_layout.addWidget(extra)

    avatar = QFrame()
    avatar.setFixedSize(36, 36)
    avatar.setStyleSheet(f"background-color: {theme.primary}; border-radius: 10px;")
    al = hbox(spacing=0, margins=(0, 0, 0, 0))
    al.setAlignment(Qt.AlignmentFlag.AlignCenter)
    avatar.setLayout(al)
    al.addWidget(
        IconLabel(finance_data.SECTION_ICON, color="#FFFFFF", size=18),
        alignment=Qt.AlignmentFlag.AlignCenter,
    )

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


def _budget_visual(theme: Theme, lang: str, budget: dict) -> QWidget:
    """Donut + legend + breakdown for the greeting bubble."""
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=12, margins=(0, 0, 0, 0))
    holder.setLayout(layout)
    slices = budget_slices_from_plan(budget)
    currency = budget.get("currency") or txt["currency_code"]

    summary = budget.get("summary") or ""
    if summary:
        layout.addWidget(BodyLabel(summary, theme=theme, size=13, selectable=True))

    body = QFrame()
    body.setStyleSheet("background: transparent;")
    body_layout = hbox(spacing=18, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)
    body_layout.addWidget(
        donut_with_caption(
            theme,
            slices=slices,
            caption_top=txt["donut_caption_top"],
            caption_bottom=txt["donut_caption_bottom"],
        )
    )
    body_layout.addWidget(legend_for_splits(theme, slices, currency=currency), 1)
    layout.addWidget(body)

    breakdown = budget.get("breakdown") or []
    if breakdown:
        layout.addWidget(
            breakdown_table(
                theme,
                rows=breakdown,
                currency=currency,
                headers=[txt["col_category"], txt["col_recommended"], txt["col_amount"], txt["col_note"]],
            )
        )
    return holder


def _greeting(theme: Theme, lang: str) -> QWidget:
    """Greeting bubble.

    Shows the budget visual ONLY when the user has already produced a
    real budget plan via the Budget tab. Until then the chat opens with
    a friendly intro inviting the user to type a question or open a
    structured tab - we never invent numbers for them.
    """
    txt = s(lang)
    budget = STATE.budget
    extra = _budget_visual(theme, lang, budget) if budget else None
    text = txt["msg2_intro"] if budget else txt["chat_greeting"]
    return _assistant_bubble(
        theme,
        text=text,
        time_label=datetime.now().strftime("%H:%M"),
        extra=extra,
    )


def _quick_action_chip(theme: Theme, *, label: str, icon: str, on_click: Callable[[], None]) -> ClickFrame:
    chip = ClickFrame()
    chip.setStyleSheet(
        f"""
        ClickFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 14px;
        }}
        ClickFrame:hover {{
            background-color: {theme.surface_2};
        }}
        """
    )
    chip.setMinimumHeight(64)
    chip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    layout = hbox(spacing=10, margins=(12, 10, 12, 10))
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    chip.setLayout(layout)
    icon_box = QFrame()
    icon_box.setFixedSize(22, 22)
    icon_box.setStyleSheet(f"background-color: {rgba(theme.primary, 0.15)}; border-radius: 7px;")
    icon_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setLayout(icon_layout)
    icon_layout.addWidget(IconLabel(icon, color=theme.primary, size=13), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(icon_box, 0, Qt.AlignmentFlag.AlignTop)
    text_slot = QFrame()
    text_slot.setStyleSheet("background: transparent;")
    wrap_label_slot(text_slot)
    text_layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    text_slot.setLayout(text_layout)
    text_layout.addWidget(BodyLabel(label, theme=theme, size=12, weight=QFont.Weight.Medium))
    layout.addWidget(text_slot, 1)
    chip.clicked.connect(on_click)
    return chip


def _send_canned(prompt_text: str, lang: str) -> None:
    if STATE.chat_running or not prompt_text.strip():
        return

    def _worker() -> None:
        try:
            pipeline.send_chat_message(output_lang=lang, user_text=prompt_text)
        except Exception as exc:
            logger_service.log_exception("ai_finance.tab_chat", "canned_worker_failed", exc)
            STATE.chat_running = False
            STATE.chat_last_error = str(exc)
            pipeline.append_chat_assistant(f"_Error_: {exc}")
            REFS.dispatch(_request_full_refresh)

    threading.Thread(target=_worker, daemon=True).start()


def _quick_actions_row(
    theme: Theme,
    lang: str,
    *,
    on_navigate: Callable[[int], None],
) -> QFrame:
    """Quick-action chip row that wraps to a second line on narrow widths.

    Replaces the old fixed ``hbox`` so chips stack instead of sliding
    off-screen when the chat takes the full window (image 5).
    """
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = QGridLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setHorizontalSpacing(10)
    layout.setVerticalSpacing(10)
    layout.setColumnStretch(0, 1)
    layout.setColumnStretch(1, 1)

    actions = [
        (txt["chat_canned_budget"], Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, lambda: on_navigate(TAB_BUDGET)),
        (txt["chat_canned_savings"], Icons.SAVINGS_OUTLINED, lambda: _send_canned(txt["chat_canned_savings"], lang)),
        (txt["chat_canned_invest"], Icons.TRENDING_UP, lambda: on_navigate(TAB_INVEST)),
        (txt["chat_canned_taxes"], Icons.RECEIPT_LONG_OUTLINED, lambda: on_navigate(TAB_TAXES)),
        (txt["chat_canned_calc"], Icons.FUNCTIONS, lambda: on_navigate(TAB_CALCULATORS)),
    ]
    for index, (label, icon, handler) in enumerate(actions):
        row = index // 2
        col = index % 2
        layout.addWidget(
            _quick_action_chip(theme, label=label, icon=icon, on_click=handler),
            row,
            col,
        )
    return holder


def _toggle_web_search(button: GhostButton, theme: Theme, lang: str) -> None:
    txt = s(lang)
    current = settings_store.get_web_search_enabled()
    settings_store.set_web_search_enabled(not current)
    button.set_label(txt["web_search_off"] if current else txt["web_search_on"])
    logger_service.log_event(
        "INFO", "ai_finance.tab_chat", "web_search_toggle",
        enabled=not current,
    )


def _build_input_bar(theme: Theme, lang: str) -> QFrame:
    txt = s(lang)
    holder = QFrame()
    holder.setStyleSheet("background: transparent;")
    layout = vbox(spacing=6, margins=(24, 10, 24, 14))
    holder.setLayout(layout)

    pending: dict[str, Optional[ParsedFile]] = {"file": None}

    chip_holder = QFrame()
    chip_holder.setStyleSheet("background: transparent;")
    chip_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    chip_holder.setLayout(chip_layout)
    chip_holder.hide()
    layout.addWidget(chip_holder)

    input_row = QFrame()
    input_row.setObjectName("FinanceChatInputRow")
    input_row.setStyleSheet(
        f"""
        QFrame#FinanceChatInputRow {{
            background-color: {theme.surface};
            border: 1.5px solid {rgba(theme.border, 0.55)};
            border-radius: 14px;
        }}
        """
    )
    input_layout = hbox(spacing=8, margins=(10, 4, 10, 4))
    input_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    input_row.setLayout(input_layout)

    attach_btn = IconOnlyButton(
        Icons.UPLOAD_FILE_OUTLINED,
        color=theme.text_muted,
        size=18,
        bg_hover=theme.surface_2,
        tooltip=txt["input_attach_label"],
    )
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

    send_btn = IconOnlyButton(
        Icons.ARROW_FORWARD,
        color="#FFFFFF",
        size=16,
        bg=theme.primary,
        bg_hover=theme.primary_hover,
        radius=12,
    )
    send_btn.setFixedSize(40, 40)
    input_layout.addWidget(send_btn)
    layout.addWidget(input_row)

    footer = QFrame()
    footer.setStyleSheet("background: transparent;")
    footer_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    footer.setLayout(footer_layout)

    web_enabled = settings_store.get_web_search_enabled()
    web_button = GhostButton(
        txt["web_search_on"] if web_enabled else txt["web_search_off"],
        theme=theme,
        icon=Icons.PUBLIC,
    )
    web_button.clicked.connect(lambda: _toggle_web_search(web_button, theme, lang))
    footer_layout.addWidget(web_button)

    status_holder = QFrame()
    status_holder.setStyleSheet("background: transparent;")
    status_holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    status_layout = hbox(spacing=4, margins=(0, 0, 0, 0))
    status_holder.setLayout(status_layout)
    status_label = MutedLabel("", theme=theme, size=11)
    if STATE.chat_running:
        status_layout.addWidget(SubtleLabel(txt["chat_running_label"], theme=theme, size=11, italic=True))
    status_layout.addStretch(1)
    status_layout.addWidget(status_label)
    footer_layout.addWidget(status_holder, 1)
    footer_layout.addWidget(SubtleLabel(txt["disclaimer_short"], theme=theme, size=11, italic=True))
    layout.addWidget(footer)

    def _set_status(message: str, *, error: bool = False) -> None:
        status_label.setText(message)
        status_label.setStyleSheet(
            f"color: {'#EF4444' if error else theme.text_muted}; background: transparent;"
        )

    def _refresh_chip() -> None:
        while chip_layout.count():
            item = chip_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        attachment = pending["file"]
        if attachment is None:
            chip_holder.hide()
            _set_status("")
            return
        chip = QFrame()
        chip.setObjectName("FinanceAttachmentChip")
        chip.setStyleSheet(
            f"""
            QFrame#FinanceAttachmentChip {{
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
        clear.clicked.connect(lambda: (_set_attachment(None), _refresh_chip()))
        c_layout.addWidget(clear)
        chip_layout.addWidget(chip)
        chip_layout.addStretch(1)
        chip_holder.show()
        _set_status(attachment.name)

    def _set_attachment(parsed: Optional[ParsedFile]) -> None:
        pending["file"] = parsed

    def _open_picker() -> None:
        path, _ = QFileDialog.getOpenFileName(
            get_main_window(),
            txt["input_attach_label"],
            "",
            "Documents (*.pdf *.docx *.txt *.md *.html *.htm *.csv)",
        )
        if not path:
            return
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext not in SUPPORTED_EXTENSIONS:
            _set_status(f"Unsupported file: .{ext}", error=True)
            return
        parsed = parse_file(path)
        if not parsed.ok:
            _set_status(parsed.error or "Could not parse file", error=True)
            return
        _set_attachment(parsed)
        _refresh_chip()

    attach_btn.clicked.connect(_open_picker)

    def _send() -> None:
        if STATE.chat_running:
            return
        text_value = field.text().strip()
        attachment = pending["file"]
        if not text_value and attachment is None:
            return
        attachment_label = ""
        if attachment is not None:
            STATE.chat_attachments[attachment.name] = attachment.text
            attachment_label = attachment.name
        pipeline.append_chat_user(
            text_value or f"(Attached {attachment_label})",
            attachment_name=attachment_label,
        )
        field.clear()
        _set_attachment(None)
        _refresh_chip()
        STATE.chat_running = True
        STATE.chat_last_error = ""
        REFS.dispatch(_request_full_refresh)

        def _worker() -> None:
            try:
                pipeline.send_chat_message(
                    output_lang=lang,
                    user_text=text_value or f"(Attached {attachment_label})",
                )
            except Exception as exc:
                logger_service.log_exception(
                    "ai_finance.tab_chat", "send_worker_failed", exc
                )
                STATE.chat_running = False
                STATE.chat_last_error = str(exc)
                pipeline.append_chat_assistant(f"_Error_: {exc}")
                REFS.dispatch(_request_full_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    field.returnPressed.connect(_send)
    send_btn.clicked.connect(_send)
    return holder


def build_chat_tab(
    theme: Theme,
    lang: str,
    *,
    on_navigate: Callable[[int], None],
) -> QWidget:
    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    messages_holder = QWidget()
    messages_holder.setStyleSheet(f"background-color: {theme.bg};")
    msgs_layout = vbox(spacing=18, margins=(24, 20, 24, 20))
    messages_holder.setLayout(msgs_layout)
    msgs_layout.addWidget(_greeting(theme, lang))
    for msg in STATE.chat_messages:
        if msg.role == "user":
            msgs_layout.addWidget(
                _user_bubble(
                    theme,
                    text=msg.text,
                    time_label=msg.time,
                    attachment_name=msg.attachment_name,
                )
            )
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
    qa_layout.addWidget(_quick_actions_row(theme, lang, on_navigate=on_navigate))
    layout.addWidget(qa_holder)

    layout.addWidget(_build_input_bar(theme, lang))

    def _scroll_to_bottom() -> None:
        bar = scroll.verticalScrollBar()
        if bar is not None:
            bar.setValue(bar.maximum())

    runtime_dispatch(_scroll_to_bottom)
    return container
