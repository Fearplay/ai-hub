"""Settings - main center view (PySide6 port).

Three stacked cards:

* **Provider & model** - provider radio + model field with chip row.
* **API keys** - three rows (OpenAI, Anthropic, GitHub). Each row holds an
  obscured text field, a Save button (writes to the OS keystore via
  :mod:`src.services.secrets`), a Delete button, and a status pill.
* **General** - demo-mode default toggle + debug logs viewer.
"""

from __future__ import annotations

import re
from typing import Callable, Optional

from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.components.header import header
from src.qt.icons import Icons
from src.qt.theme import rgba
from src.qt.widgets import (
    BodyLabel,
    DangerButton,
    GhostButton,
    HSeparator,
    IconLabel,
    MutedLabel,
    Pill,
    PrimaryButton,
    SubtleLabel,
    TitleLabel,
    custom_label,
    hbox,
    themed_line_edit,
    vbox,
)
from src.services import clipboard, logger as logger_service
from src.services import secrets, settings_store
from src.sections.settings.data import SECTION_ICON, key_rows
from src.sections.settings.strings import s
from src.theme import Theme


MODE_MAIN = "main"
MODE_LOGS = "logs"


_LEVEL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\s+\|\s+(\w+)\s+\|"
)

_LEVEL_COLOURS: dict[str, str] = {
    "DEBUG": "#06B6D4",
    "WARNING": "#F59E0B",
    "ERROR": "#EF4444",
    "CRITICAL": "#DC2626",
}


class _LogHighlighter(QSyntaxHighlighter):
    """Per-level colouring for the debug log viewer.

    The highlighter pattern matches the timestamp prefix written by
    ``src/services/logger.py`` (see ``_AlignedFormatter``). Continuation
    lines (tracebacks, blank lines) inherit the colour of the previous
    classified row using ``previousBlockState`` so a multi-line stack
    stays red.
    """

    _LEVEL_TO_STATE = {
        "DEBUG": 1,
        "INFO": 2,
        "WARNING": 3,
        "ERROR": 4,
        "CRITICAL": 5,
    }
    _STATE_TO_LEVEL = {v: k for k, v in _LEVEL_TO_STATE.items()}

    def __init__(self, document: QTextDocument, theme: Theme) -> None:
        super().__init__(document)
        self._regex = QRegularExpression(
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\s+\|\s+(\w+)\s+\|"
        )
        self._formats: dict[str, QTextCharFormat] = {}
        for level, colour in _LEVEL_COLOURS.items():
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(colour))
            if level == "CRITICAL":
                fmt.setFontWeight(QFont.Weight.Bold)
            self._formats[level] = fmt
        info_fmt = QTextCharFormat()
        info_fmt.setForeground(QColor(theme.text))
        self._formats["INFO"] = info_fmt

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        match = self._regex.match(text)
        level: Optional[str] = None
        if match.hasMatch():
            level = match.captured(1).upper()
        if level is None:
            prev = self.previousBlockState()
            level = self._STATE_TO_LEVEL.get(prev)
        if level and level in self._formats:
            self.setFormat(0, len(text), self._formats[level])
        if level is not None:
            self.setCurrentBlockState(self._LEVEL_TO_STATE.get(level, 2))
        else:
            self.setCurrentBlockState(0)


def _card(
    theme: Theme,
    *,
    icon: str,
    title: str,
    desc: str,
    body: QWidget,
) -> QFrame:
    card = QFrame()
    card.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 16px;
        }}
        """
    )
    card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
    layout = vbox(spacing=14, margins=(18, 18, 18, 18))
    card.setLayout(layout)

    head_row = QFrame()
    head_row.setStyleSheet("background: transparent; border: none;")
    head_layout = hbox(spacing=12, margins=(0, 0, 0, 0))
    head_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    head_row.setLayout(head_layout)

    icon_box = QFrame()
    icon_box.setFixedSize(32, 32)
    icon_box.setStyleSheet(
        f"background-color: {rgba(theme.primary, 0.14)}; border-radius: 8px;"
    )
    ib_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    ib_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setLayout(ib_layout)
    ib_layout.addWidget(IconLabel(icon, color=theme.primary, size=18),
                        alignment=Qt.AlignmentFlag.AlignCenter)
    head_layout.addWidget(icon_box)

    text_col = QFrame()
    text_col.setStyleSheet("background: transparent; border: none;")
    tc_layout = vbox(spacing=2, margins=(0, 0, 0, 0))
    text_col.setLayout(tc_layout)
    tc_layout.addWidget(TitleLabel(title, theme=theme, size=15, weight=QFont.Weight.Bold))
    if desc:
        tc_layout.addWidget(MutedLabel(desc, theme=theme, size=12))
    head_layout.addWidget(text_col, 1)
    layout.addWidget(head_row)
    layout.addWidget(body)
    return card


def _status_pill(theme: Theme, *, ok: bool, label: str) -> Pill:
    color = "#22C55E" if ok else theme.text_muted
    return Pill(
        text=label,
        bg=rgba(color, 0.12),
        fg=color,
        icon=Icons.CHECK_CIRCLE if ok else Icons.RADIO_BUTTON_UNCHECKED,
    )


def _provider_card(
    theme: Theme,
    lang: str,
    txt: dict,
    on_provider_change: Callable[[], None],
) -> QFrame:
    current_provider = settings_store.get_provider()

    body = QFrame()
    body.setStyleSheet("background: transparent; border: none;")
    body_layout = vbox(spacing=10, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    body_layout.addWidget(SubtleLabel(txt["provider_label"], theme=theme, size=11, weight=QFont.Weight.Medium))

    radio_row = QFrame()
    radio_row.setStyleSheet("background: transparent;")
    rr_layout = hbox(spacing=18, margins=(0, 0, 0, 0))
    rr_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    radio_row.setLayout(rr_layout)
    button_group = QButtonGroup(radio_row)

    radio_style = f"""
        QRadioButton {{
            color: {theme.text};
            spacing: 8px;
            background: transparent;
        }}
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
        }}
        QRadioButton::indicator:unchecked {{
            border: 2px solid {theme.border};
            border-radius: 9px;
            background: transparent;
        }}
        QRadioButton::indicator:checked {{
            border: 2px solid {theme.primary};
            border-radius: 9px;
            background: {theme.primary};
        }}
    """

    rb_openai = QRadioButton(txt["provider_openai"])
    rb_openai.setStyleSheet(radio_style)
    rb_anthropic = QRadioButton(txt["provider_anthropic"])
    rb_anthropic.setStyleSheet(radio_style)
    if current_provider == settings_store.PROVIDER_OPENAI:
        rb_openai.setChecked(True)
    else:
        rb_anthropic.setChecked(True)
    button_group.addButton(rb_openai, 0)
    button_group.addButton(rb_anthropic, 1)
    rr_layout.addWidget(rb_openai)
    rr_layout.addWidget(rb_anthropic)
    rr_layout.addStretch(1)
    body_layout.addWidget(radio_row)

    body_layout.addWidget(SubtleLabel(txt["model_label"], theme=theme, size=11, weight=QFont.Weight.Medium))

    model_row = QFrame()
    model_row.setStyleSheet("background: transparent;")
    mr_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    mr_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    model_row.setLayout(mr_layout)

    model_field = themed_line_edit(theme, placeholder="")
    model_field.setText(settings_store.get_model(current_provider))
    mr_layout.addWidget(model_field, 1)

    save_btn = PrimaryButton(txt["model_save"], theme=theme, icon=Icons.SAVE_OUTLINED)
    mr_layout.addWidget(save_btn)
    body_layout.addWidget(model_row)

    body_layout.addWidget(SubtleLabel(txt["model_hint"], theme=theme, size=11))

    chip_holder = QFrame()
    chip_holder.setStyleSheet("background: transparent;")
    chip_layout = hbox(spacing=6, margins=(0, 0, 0, 0))
    chip_holder.setLayout(chip_layout)
    body_layout.addWidget(chip_holder)

    save_status = SubtleLabel("", theme=theme, size=12, weight=QFont.Weight.Medium)
    body_layout.addWidget(save_status)

    def _list_for(provider: str) -> tuple[str, ...]:
        return (
            settings_store.ANTHROPIC_MODELS
            if provider == settings_store.PROVIDER_ANTHROPIC
            else settings_store.OPENAI_MODELS
        )

    def _refresh_chips(provider: str) -> None:
        while chip_layout.count():
            item = chip_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for model in _list_for(provider):
            chip = GhostButton(model, theme=theme)
            chip.clicked.connect(lambda _=False, m=model: model_field.setText(m))
            chip_layout.addWidget(chip)
        chip_layout.addStretch(1)

    def _save_model() -> None:
        provider = settings_store.get_provider()
        value = (model_field.text() or "").strip()
        if not value:
            save_status.setText(txt["model_invalid"])
            save_status.setStyleSheet("color: #EF4444; background: transparent;")
            logger_service.log_event(
                "WARNING", "settings.view", "save_model_invalid", provider=provider,
            )
            return
        settings_store.set_model(provider, value)
        save_status.setText(txt["model_saved"])
        save_status.setStyleSheet("color: #22C55E; background: transparent;")
        logger_service.log_event(
            "INFO", "settings.view", "save_model_ok", provider=provider, model=value,
        )

    def _on_provider_btn(provider: str) -> None:
        if provider not in (settings_store.PROVIDER_OPENAI, settings_store.PROVIDER_ANTHROPIC):
            return
        settings_store.set_provider(provider)
        logger_service.log_event(
            "INFO", "settings.view", "provider_changed", provider=provider,
        )
        model_field.setText(settings_store.get_model(provider))
        _refresh_chips(provider)
        on_provider_change()

    rb_openai.toggled.connect(
        lambda checked: _on_provider_btn(settings_store.PROVIDER_OPENAI) if checked else None
    )
    rb_anthropic.toggled.connect(
        lambda checked: _on_provider_btn(settings_store.PROVIDER_ANTHROPIC) if checked else None
    )
    save_btn.clicked.connect(_save_model)
    _refresh_chips(current_provider)

    return _card(
        theme,
        icon=Icons.AUTO_AWESOME,
        title=txt["provider_card_title"],
        desc=txt["provider_card_desc"],
        body=body,
    )


def _key_row(theme: Theme, txt: dict, key: dict, vault_ok: bool) -> QFrame:
    name = key["name"]

    holder = QFrame()
    holder.setStyleSheet("background: transparent; border: none;")
    holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
    layout = vbox(spacing=8, margins=(2, 4, 2, 4))
    holder.setLayout(layout)

    label_row = QFrame()
    label_row.setStyleSheet("background: transparent;")
    lr_layout = hbox(spacing=10, margins=(0, 0, 0, 0))
    lr_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    label_row.setLayout(lr_layout)

    icon_box = QFrame()
    icon_box.setFixedSize(28, 28)
    icon_box.setStyleSheet(
        f"background-color: {rgba(key['color'], 0.15)}; border-radius: 8px;"
    )
    ib_layout = hbox(spacing=0, margins=(0, 0, 0, 0))
    ib_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setLayout(ib_layout)
    ib_layout.addWidget(IconLabel(key["icon"], color=key["color"], size=16),
                        alignment=Qt.AlignmentFlag.AlignCenter)
    lr_layout.addWidget(icon_box)

    lr_layout.addWidget(BodyLabel(key["label"], theme=theme, size=13, weight=QFont.Weight.DemiBold), 1)

    saved = secrets.has_secret(name) if vault_ok else False
    status_pill = _status_pill(
        theme, ok=saved,
        label=txt["key_status_set"] if saved else txt["key_status_unset"],
    )
    lr_layout.addWidget(status_pill)

    layout.addWidget(label_row)

    actions_row = QFrame()
    actions_row.setStyleSheet("background: transparent;")
    ar_layout = hbox(spacing=8, margins=(0, 0, 0, 0))
    ar_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    actions_row.setLayout(ar_layout)

    field = themed_line_edit(theme, placeholder=key["hint"], password=True)
    field.setEnabled(vault_ok)
    ar_layout.addWidget(field, 1)

    show_btn = GhostButton(txt["key_show_btn"], theme=theme, icon=Icons.VISIBILITY_OFF_OUTLINED)
    show_btn.setEnabled(vault_ok)
    ar_layout.addWidget(show_btn)

    save_btn = PrimaryButton(txt["key_save_btn"], theme=theme, icon=Icons.LOCK_OUTLINE)
    save_btn.setEnabled(vault_ok)
    ar_layout.addWidget(save_btn)

    delete_btn = DangerButton(txt["key_delete_btn"], theme=theme, icon=Icons.DELETE_OUTLINE)
    delete_btn.setEnabled(vault_ok)
    ar_layout.addWidget(delete_btn)

    layout.addWidget(actions_row)

    feedback = SubtleLabel("", theme=theme, size=11)
    layout.addWidget(feedback)

    is_revealed = {"value": False}

    def _toggle_show() -> None:
        is_revealed["value"] = not is_revealed["value"]
        if is_revealed["value"]:
            field.setEchoMode(QLineEdit.EchoMode.Normal)
            show_btn.setText(txt["key_hide_btn"])
        else:
            field.setEchoMode(QLineEdit.EchoMode.Password)
            show_btn.setText(txt["key_show_btn"])

    def _refresh_status() -> None:
        is_set = secrets.has_secret(name) if vault_ok else False
        if is_set:
            status_pill.set_palette(
                bg=rgba("#22C55E", 0.12), fg="#22C55E", icon=Icons.CHECK_CIRCLE,
            )
            status_pill.set_text(txt["key_status_set"])
        else:
            status_pill.set_palette(
                bg=rgba(theme.text_muted, 0.12), fg=theme.text_muted,
                icon=Icons.RADIO_BUTTON_UNCHECKED,
            )
            status_pill.set_text(txt["key_status_unset"])

    def _set_feedback(message: str, *, ok: bool) -> None:
        feedback.setText(message)
        feedback.setStyleSheet(
            f"color: {'#22C55E' if ok else '#EF4444'}; background: transparent;"
        )

    def _on_save() -> None:
        if not vault_ok:
            _set_feedback(txt["key_save_failed"], ok=False)
            logger_service.log_event(
                "WARNING", "settings.view", "key_save_no_vault", key_name=name,
            )
            return
        value = (field.text() or "").strip()
        if not value:
            _set_feedback(txt["key_save_empty"], ok=False)
            logger_service.log_event(
                "WARNING", "settings.view", "key_save_empty", key_name=name,
            )
            return
        success = secrets.set_secret(name, value)
        if success:
            field.clear()
            _set_feedback(txt["key_save_ok"], ok=True)
            _refresh_status()
            logger_service.log_event("INFO", "settings.view", "key_saved", key_name=name)
        else:
            _set_feedback(txt["key_save_failed"], ok=False)
            logger_service.log_event(
                "ERROR", "settings.view", "key_save_failed", key_name=name,
            )

    def _on_delete() -> None:
        if not vault_ok or not secrets.has_secret(name):
            _set_feedback(txt["key_delete_failed"], ok=False)
            logger_service.log_event(
                "WARNING", "settings.view", "key_delete_unavailable",
                key_name=name, vault_ok=vault_ok,
            )
            return
        if secrets.delete_secret(name):
            _set_feedback(txt["key_delete_ok"], ok=True)
            _refresh_status()
            logger_service.log_event("INFO", "settings.view", "key_deleted", key_name=name)
        else:
            _set_feedback(txt["key_delete_failed"], ok=False)
            logger_service.log_event(
                "ERROR", "settings.view", "key_delete_failed", key_name=name,
            )

    show_btn.clicked.connect(_toggle_show)
    save_btn.clicked.connect(_on_save)
    delete_btn.clicked.connect(_on_delete)
    return holder


def _keys_card(theme: Theme, lang: str, txt: dict) -> QFrame:
    vault_ok = secrets.is_available()

    body = QFrame()
    body.setStyleSheet("background: transparent; border: none;")
    body_layout = vbox(spacing=6, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    if not vault_ok:
        warning = QFrame()
        warning.setStyleSheet(
            f"""
            QFrame {{
                background-color: {rgba("#EF4444", 0.10)};
                border: 1px solid {rgba("#EF4444", 0.40)};
                border-radius: 10px;
            }}
            """
        )
        wl = vbox(spacing=4, margins=(12, 12, 12, 12))
        warning.setLayout(wl)
        wl.addWidget(custom_label(
            txt["vault_unavailable_title"], color="#EF4444", size=13, weight=QFont.Weight.Bold,
        ))
        wl.addWidget(MutedLabel(txt["vault_unavailable_desc"], theme=theme, size=12))
        body_layout.addWidget(warning)

    rows = key_rows(txt)
    for idx, key in enumerate(rows):
        body_layout.addWidget(_key_row(theme, txt, key, vault_ok))
        if idx < len(rows) - 1:
            body_layout.addWidget(HSeparator(theme))

    desc = txt["keys_card_desc_template"].format(keystore=settings_store.keystore_label())
    return _card(
        theme,
        icon=Icons.LOCK_OUTLINE,
        title=txt["keys_card_title"],
        desc=desc,
        body=body,
    )


def _toggle_switch(theme: Theme, *, checked: bool, on_change: Callable[[bool], None]) -> QCheckBox:
    """A QCheckBox styled as a Material-style toggle switch.

    Uses a styled indicator so it visually mirrors the Flet ``Switch``
    used in the original UI.
    """
    cb = QCheckBox()
    cb.setChecked(checked)
    cb.setCursor(Qt.CursorShape.PointingHandCursor)
    cb.setStyleSheet(
        f"""
        QCheckBox {{
            spacing: 0;
            background: transparent;
        }}
        QCheckBox::indicator {{
            width: 36px;
            height: 20px;
            border-radius: 10px;
            border: 1px solid {theme.border};
            background-color: {theme.surface_2};
        }}
        QCheckBox::indicator:checked {{
            background-color: {theme.primary};
            border: 1px solid {theme.primary};
            image: none;
        }}
        """
    )
    cb.toggled.connect(on_change)
    return cb


def _general_card(
    theme: Theme,
    lang: str,
    txt: dict,
    *,
    on_view_logs: Callable[[], None],
) -> QFrame:
    body = QFrame()
    body.setStyleSheet("background: transparent; border: none;")
    body_layout = vbox(spacing=4, margins=(0, 0, 0, 0))
    body.setLayout(body_layout)

    def _on_demo_change(value: bool) -> None:
        settings_store.set_demo_default(bool(value))
        logger_service.log_event(
            "INFO", "settings.view", "demo_default_changed", value=bool(value),
        )

    demo_row = QFrame()
    demo_row.setStyleSheet("background: transparent;")
    drl = hbox(spacing=10, margins=(2, 8, 2, 8))
    drl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    demo_row.setLayout(drl)

    demo_text = QFrame()
    demo_text.setStyleSheet("background: transparent;")
    dtl = vbox(spacing=2, margins=(0, 0, 0, 0))
    demo_text.setLayout(dtl)
    dtl.addWidget(BodyLabel(txt["general_demo_default_label"], theme=theme, size=13, weight=QFont.Weight.DemiBold))
    dtl.addWidget(MutedLabel(txt["general_demo_default_desc"], theme=theme, size=12))
    drl.addWidget(demo_text, 1)
    drl.addWidget(_toggle_switch(theme, checked=settings_store.get_demo_default(), on_change=_on_demo_change))
    body_layout.addWidget(demo_row)

    body_layout.addWidget(HSeparator(theme))

    logs_row = QFrame()
    logs_row.setStyleSheet("background: transparent;")
    lrl = vbox(spacing=10, margins=(2, 8, 2, 8))
    logs_row.setLayout(lrl)

    logs_text = QFrame()
    logs_text.setStyleSheet("background: transparent;")
    ltl = vbox(spacing=2, margins=(0, 0, 0, 0))
    logs_text.setLayout(ltl)
    ltl.addWidget(BodyLabel(txt["logs_card_label"], theme=theme, size=13, weight=QFont.Weight.DemiBold))
    ltl.addWidget(MutedLabel(txt["logs_card_desc"], theme=theme, size=12))
    lrl.addWidget(logs_text)

    btn_row = QFrame()
    btn_row.setStyleSheet("background: transparent;")
    brl = hbox(spacing=8, margins=(0, 0, 0, 0))
    brl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    btn_row.setLayout(brl)
    view_btn = PrimaryButton(txt["logs_view_btn"], theme=theme, icon=Icons.RECEIPT_LONG_OUTLINED)
    view_btn.clicked.connect(on_view_logs)
    brl.addWidget(view_btn)
    folder_btn = GhostButton(txt["logs_open_folder_btn"], theme=theme, icon=Icons.FOLDER_OPEN)
    def _on_open_log_folder() -> None:
        logger_service.log_event("INFO", "settings.view", "open_log_folder")
        logger_service.open_log_dir_in_explorer()
    folder_btn.clicked.connect(_on_open_log_folder)
    brl.addWidget(folder_btn)
    brl.addStretch(1)
    lrl.addWidget(btn_row)
    body_layout.addWidget(logs_row)

    return _card(
        theme,
        icon=Icons.TUNE,
        title=txt["general_card_title"],
        desc="",
        body=body,
    )


def _logs_view(
    theme: Theme,
    txt: dict,
    *,
    on_back: Callable[[], None],
) -> QFrame:
    container = QFrame()
    container.setStyleSheet(
        f"""
        QFrame {{
            background-color: {theme.surface};
            border: 1px solid {theme.border};
            border-radius: 16px;
        }}
        """
    )
    container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    layout = vbox(spacing=12, margins=(24, 20, 24, 20))
    container.setLayout(layout)

    header_row = QFrame()
    header_row.setStyleSheet("background: transparent; border: none;")
    hrl = hbox(spacing=8, margins=(0, 0, 0, 0))
    hrl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    header_row.setLayout(hrl)
    back_btn = GhostButton(txt["logs_back_btn"], theme=theme, icon=Icons.ARROW_BACK)
    back_btn.clicked.connect(lambda: (logger_service.log_event("INFO", "settings.view", "logs_back"), on_back()))
    hrl.addWidget(back_btn)
    title_holder = QFrame()
    title_holder.setStyleSheet("background: transparent; border: none;")
    thl = hbox(spacing=0, margins=(10, 0, 0, 0))
    title_holder.setLayout(thl)
    thl.addWidget(TitleLabel(txt["logs_view_title"], theme=theme, size=15, weight=QFont.Weight.Bold))
    thl.addStretch(1)
    hrl.addWidget(title_holder, 1)
    layout.addWidget(header_row)

    layout.addWidget(MutedLabel(txt["logs_view_desc"], theme=theme, size=12))
    path_label = custom_label(
        txt["logs_path_template"].format(path=str(logger_service.log_path())),
        color=theme.text_subtle, size=11, italic=True, selectable=True,
    )
    layout.addWidget(path_label)
    layout.addWidget(custom_label(txt["logs_selection_hint"],
                                  color=theme.text_subtle, size=11, italic=True))

    actions_row = QFrame()
    actions_row.setStyleSheet("background: transparent; border: none;")
    arl = hbox(spacing=8, margins=(0, 0, 0, 0))
    arl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    actions_row.setLayout(arl)
    refresh_btn = PrimaryButton(txt["logs_refresh_btn"], theme=theme, icon=Icons.REFRESH)
    arl.addWidget(refresh_btn)
    copy_btn = GhostButton(txt["logs_copy_btn"], theme=theme, icon=Icons.COPY_ALL)
    arl.addWidget(copy_btn)
    folder_btn = GhostButton(txt["logs_open_folder_btn"], theme=theme, icon=Icons.FOLDER_OPEN)
    arl.addWidget(folder_btn)
    clear_btn = DangerButton(txt["logs_clear_btn"], theme=theme, icon=Icons.DELETE_SWEEP_OUTLINED)
    arl.addWidget(clear_btn)
    arl.addStretch(1)
    status_label = SubtleLabel("", theme=theme, size=11)
    arl.addWidget(status_label)
    layout.addWidget(actions_row)

    log_box = QPlainTextEdit()
    log_box.setReadOnly(True)
    log_box.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    log_box.setStyleSheet(
        f"""
        QPlainTextEdit {{
            background-color: {theme.surface_2};
            color: {theme.text};
            border: 1px solid {theme.border};
            border-radius: 10px;
            padding: 12px;
            font-family: Consolas, Menlo, monospace;
            font-size: 12px;
            selection-background-color: {rgba(theme.primary, 0.30)};
        }}
        """
    )
    log_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    _highlighter = _LogHighlighter(log_box.document(), theme)
    layout.addWidget(log_box, 1)

    def _refresh(message: str = "", color: str = "") -> None:
        body = logger_service.read_log()
        if body:
            log_box.setPlainText(body)
            cursor = log_box.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            log_box.setTextCursor(cursor)
        else:
            log_box.setPlainText(txt["logs_empty"])
        if message:
            status_label.setText(message)
            status_label.setStyleSheet(f"color: {color or theme.text_muted}; background: transparent;")
        else:
            status_label.setText("")
            status_label.setStyleSheet(f"color: {theme.text_muted}; background: transparent;")

    def _on_refresh() -> None:
        logger_service.log_event("INFO", "settings.view", "logs_refresh")
        _refresh()

    def _on_copy() -> None:
        body = logger_service.read_log()
        if not body:
            _refresh(message=txt["logs_empty"], color=theme.text_muted)
            return
        ok = clipboard.copy(body)
        if ok:
            logger_service.log_event(
                "INFO", "settings.view", "logs_copied",
                chars=len(body), backend=clipboard.backend_name(),
            )
            _refresh(message=txt["logs_copy_done"], color="#22C55E")
        else:
            logger_service.log_event(
                "ERROR", "settings.view", "logs_copy_failed_sync",
                backend=clipboard.backend_name(),
            )
            _refresh(message=txt["logs_copy_failed"], color="#EF4444")

    def _on_clear() -> None:
        ok = logger_service.clear_log()
        if ok:
            _refresh(message=txt["logs_clear_done"], color="#22C55E")
        else:
            _refresh(message=txt["logs_clear_failed"], color="#EF4444")

    def _on_open_folder() -> None:
        logger_service.log_event("INFO", "settings.view", "open_log_folder")
        logger_service.open_log_dir_in_explorer()

    refresh_btn.clicked.connect(_on_refresh)
    copy_btn.clicked.connect(_on_copy)
    folder_btn.clicked.connect(_on_open_folder)
    clear_btn.clicked.connect(_on_clear)

    _refresh()
    container._highlighter = _highlighter  # type: ignore[attr-defined]
    return container


def build_view(theme: Theme, lang: str) -> QWidget:
    txt = s(lang)

    container = QWidget()
    container.setStyleSheet(f"background-color: {theme.bg};")
    layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    container.setLayout(layout)

    layout.addWidget(header(
        theme,
        lang,
        icon=SECTION_ICON,
        title=txt["title"],
        subtitle=txt["subtitle"],
    ))

    body_holder = QWidget()
    body_holder.setStyleSheet(f"background-color: {theme.bg};")
    body_layout = vbox(spacing=0, margins=(0, 0, 0, 0))
    body_holder.setLayout(body_layout)
    layout.addWidget(body_holder, 1)

    mode = {"value": MODE_MAIN}

    def _rerender_body() -> None:
        while body_layout.count():
            item = body_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
        if mode["value"] == MODE_LOGS:
            outer = QFrame()
            outer.setStyleSheet("background: transparent;")
            ol = vbox(spacing=0, margins=(24, 20, 24, 20))
            outer.setLayout(ol)
            ol.addWidget(_logs_view(theme, txt, on_back=_show_main))
            body_layout.addWidget(outer)
        else:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.bg}; border: none; }}")
            inner = QFrame()
            inner.setStyleSheet(f"background-color: {theme.bg};")
            il = vbox(spacing=16, margins=(24, 20, 24, 20))
            inner.setLayout(il)
            il.addWidget(_provider_card(theme, lang, txt, on_provider_change=_rerender_body))
            il.addWidget(_keys_card(theme, lang, txt))
            il.addWidget(_general_card(theme, lang, txt, on_view_logs=_show_logs))
            il.addStretch(1)
            scroll.setWidget(inner)
            body_layout.addWidget(scroll)

    def _show_logs() -> None:
        logger_service.log_event("INFO", "settings.view", "logs_view_open")
        mode["value"] = MODE_LOGS
        _rerender_body()

    def _show_main() -> None:
        logger_service.log_event("INFO", "settings.view", "logs_view_close")
        mode["value"] = MODE_MAIN
        _rerender_body()

    _rerender_body()
    return container
