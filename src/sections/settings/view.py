"""Settings - main center view.

Three stacked cards:

* **Provider & model** - provider radio + model dropdown with a free-text
  override field for unknown / future model ids.
* **API keys** - three rows (OpenAI, Anthropic, GitHub). Each row holds an
  obscured text field, a Save button (writes to the OS keystore via
  :mod:`src.services.secrets`), a Delete button, and a status pill.
* **General** - demo-mode default toggle.

Status feedback is rendered inline next to each row so the user does not
miss it when the snackbar dismisses.
"""

from __future__ import annotations

import re
from typing import Callable

import flet as ft

from src.components.header import header
from src.services import clipboard, logger as logger_service
from src.services import secrets, settings_store
from src.sections.settings.data import SECTION_ICON, key_rows
from src.sections.settings.strings import s
from src.theme import Theme


MODE_MAIN = "main"
MODE_LOGS = "logs"


# Matches the timestamp + level prefix written by the rotating logger
# (see src/services/logger.py - _AlignedFormatter).
# Example match: ``2026-05-09 20:42:15.255 | ERROR | ...``
_LEVEL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\s+\|\s+(\w+)\s+\|"
)

# Per-level colours for the in-app debug logs viewer. ``None`` means
# "use theme.text" - we colour the *whole row* (timestamp included) by
# level so the eye can find ERROR / WARNING lines while skimming a long
# tail. Continuation lines (tracebacks, blank lines) inherit the colour
# of the previous classified row so a multi-line stack stays red.
_LEVEL_COLOURS: dict[str, str | None] = {
    "DEBUG": "#06B6D4",      # cyan
    "INFO": None,             # default text colour
    "WARNING": "#F59E0B",     # amber
    "ERROR": "#EF4444",       # red
    "CRITICAL": "#DC2626",    # bold red
}


def _colour_for_level(level: str | None, theme: Theme) -> str:
    if level is None:
        return theme.text
    colour = _LEVEL_COLOURS.get(level)
    if colour is None:
        return theme.text
    return colour


def _log_line_controls(text: str, theme: Theme) -> list[ft.Control]:
    """Turn the raw log tail into one coloured ``ft.Text`` per line.

    The per-row ``ft.Text`` controls are NOT marked ``selectable=True``
    on purpose - the parent :class:`ft.SelectionArea` (see
    :func:`_logs_view`) is what enables drag-select across rows.
    Mixing ``SelectableText`` widgets inside a ``SelectionArea`` makes
    Flutter ignore the area-level selection because each
    ``SelectableText`` claims its own selection scope.
    """
    if not text:
        return []
    rows: list[ft.Control] = []
    last_level: str | None = None
    for raw in text.split("\n"):
        match = _LEVEL_RE.match(raw)
        if match:
            level: str | None = match.group(1).upper()
            last_level = level
        else:
            level = last_level
        rows.append(
            ft.Text(
                raw if raw else " ",
                color=_colour_for_level(level, theme),
                size=12,
                font_family="Consolas, Menlo, monospace",
                weight=(
                    ft.FontWeight.W_700
                    if level == "CRITICAL"
                    else ft.FontWeight.W_400
                ),
                no_wrap=False,
            )
        )
    return rows


def _card(theme: Theme, *, icon: str, title: str, desc: str, body: ft.Control) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Icon(icon, color=theme.primary, size=18),
                            width=32,
                            height=32,
                            bgcolor=ft.Colors.with_opacity(0.14, theme.primary),
                            border_radius=8,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(title, color=theme.text, size=15, weight=ft.FontWeight.W_700),
                                ft.Text(desc, color=theme.text_muted, size=12),
                            ],
                            spacing=2,
                            tight=True,
                            expand=True,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                body,
            ],
            spacing=14,
            tight=True,
        ),
        padding=18,
        bgcolor=theme.surface,
        border_radius=16,
        border=ft.border.all(1, theme.border),
    )


def _status_pill(theme: Theme, *, ok: bool, label: str) -> ft.Container:
    color = "#22C55E" if ok else theme.text_muted
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.CHECK_CIRCLE if ok else ft.Icons.RADIO_BUTTON_UNCHECKED,
                    color=color,
                    size=14,
                ),
                ft.Text(label, color=color, size=12, weight=ft.FontWeight.W_500),
            ],
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        bgcolor=ft.Colors.with_opacity(0.12, color),
        border_radius=8,
    )


def _flat_button(
    theme: Theme,
    label: str,
    *,
    icon: str | None = None,
    primary: bool = False,
    danger: bool = False,
    on_click: Callable[[ft.ControlEvent], None],
) -> ft.Container:
    color = (
        ft.Colors.WHITE
        if primary
        else ("#EF4444" if danger else theme.text)
    )
    bg = (
        theme.primary
        if primary
        else (
            ft.Colors.with_opacity(0.10, "#EF4444") if danger else theme.surface_2
        )
    )
    border = (
        None
        if primary
        else ft.border.all(
            1, ft.Colors.with_opacity(0.40, "#EF4444") if danger else theme.border
        )
    )
    children: list[ft.Control] = []
    if icon:
        children.append(ft.Icon(icon, color=color, size=14))
    children.append(
        ft.Text(label, color=color, size=12, weight=ft.FontWeight.W_600)
    )
    return ft.Container(
        content=ft.Row(controls=children, spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        bgcolor=bg,
        border=border,
        border_radius=10,
        ink=True,
        on_click=on_click,
    )


def _provider_card(theme: Theme, lang: str, txt: dict, on_provider_change: Callable[[], None]) -> ft.Control:
    current_provider = settings_store.get_provider()

    model_field = ft.TextField(
        value=settings_store.get_model(current_provider),
        text_style=ft.TextStyle(color=theme.text, size=13),
        bgcolor=theme.surface_2,
        border=ft.InputBorder.NONE,
        filled=True,
        cursor_color=theme.primary,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=10,
        expand=True,
    )

    def _list_for(provider: str) -> tuple[str, ...]:
        return (
            settings_store.ANTHROPIC_MODELS
            if provider == settings_store.PROVIDER_ANTHROPIC
            else settings_store.OPENAI_MODELS
        )

    chip_row = ft.Row(spacing=8, wrap=True, run_spacing=8)

    def _refresh_chips(provider: str) -> None:
        chip_row.controls = [
            ft.Container(
                content=ft.Text(model, color=theme.text, size=11, weight=ft.FontWeight.W_500),
                padding=ft.padding.symmetric(horizontal=10, vertical=5),
                bgcolor=theme.surface_2,
                border=ft.border.all(1, theme.border),
                border_radius=8,
                ink=True,
                on_click=lambda e, m=model: _set_model_text(m),
            )
            for model in _list_for(provider)
        ]
        logger_service.try_update(chip_row)

    def _set_model_text(value: str) -> None:
        model_field.value = value
        logger_service.try_update(model_field)

    save_status = ft.Text("", color="#22C55E", size=12, weight=ft.FontWeight.W_500)

    def _save_model(_e: ft.ControlEvent) -> None:
        provider = settings_store.get_provider()
        value = (model_field.value or "").strip()
        if not value:
            save_status.value = txt["model_invalid"]
            save_status.color = "#EF4444"
            logger_service.log_event(
                "WARNING", "settings.view", "save_model_invalid", provider=provider
            )
        else:
            settings_store.set_model(provider, value)
            save_status.value = txt["model_saved"]
            save_status.color = "#22C55E"
            logger_service.log_event(
                "INFO", "settings.view", "save_model_ok", provider=provider, model=value
            )
        try:
            save_status.update()
        except Exception as exc:
            logger_service.log_exception("settings.view", "save_status_update", exc)

    def _on_radio_change(e: ft.ControlEvent) -> None:
        provider = e.control.value
        if provider not in (settings_store.PROVIDER_OPENAI, settings_store.PROVIDER_ANTHROPIC):
            logger_service.log_event(
                "WARNING", "settings.view", "provider_change_invalid", value=str(provider)
            )
            return
        settings_store.set_provider(provider)
        logger_service.log_event(
            "INFO", "settings.view", "provider_changed", provider=provider
        )
        model_field.value = settings_store.get_model(provider)
        try:
            model_field.update()
        except Exception as exc:
            logger_service.log_exception("settings.view", "model_field_update", exc)
        _refresh_chips(provider)
        on_provider_change()

    radio_group = ft.RadioGroup(
        value=current_provider,
        on_change=_on_radio_change,
        content=ft.Row(
            controls=[
                ft.Radio(
                    value=settings_store.PROVIDER_OPENAI,
                    label=txt["provider_openai"],
                    fill_color=theme.primary,
                    label_style=ft.TextStyle(color=theme.text, size=13),
                ),
                ft.Radio(
                    value=settings_store.PROVIDER_ANTHROPIC,
                    label=txt["provider_anthropic"],
                    fill_color=theme.primary,
                    label_style=ft.TextStyle(color=theme.text, size=13),
                ),
            ],
            spacing=18,
        ),
    )

    _refresh_chips(current_provider)

    body = ft.Column(
        controls=[
            ft.Text(txt["provider_label"], color=theme.text_muted, size=11, weight=ft.FontWeight.W_500),
            radio_group,
            ft.Container(height=4),
            ft.Text(txt["model_label"], color=theme.text_muted, size=11, weight=ft.FontWeight.W_500),
            ft.Row(
                controls=[
                    model_field,
                    _flat_button(theme, txt["model_save"], icon=ft.Icons.SAVE_OUTLINED, primary=True, on_click=_save_model),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text(txt["model_hint"], color=theme.text_subtle, size=11),
            chip_row,
            save_status,
        ],
        spacing=8,
        tight=True,
    )

    return _card(
        theme,
        icon=ft.Icons.AUTO_AWESOME,
        title=txt["provider_card_title"],
        desc=txt["provider_card_desc"],
        body=body,
    )


def _key_row(theme: Theme, txt: dict, key: dict, vault_ok: bool) -> ft.Control:
    name = key["name"]
    field = ft.TextField(
        password=True,
        can_reveal_password=True,
        hint_text=key["hint"],
        hint_style=ft.TextStyle(color=theme.text_subtle, size=12),
        text_style=ft.TextStyle(color=theme.text, size=13),
        bgcolor=theme.surface_2,
        border=ft.InputBorder.NONE,
        filled=True,
        cursor_color=theme.primary,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=10,
        expand=True,
        disabled=not vault_ok,
    )

    saved = secrets.has_secret(name) if vault_ok else False
    status_holder = ft.Container(
        content=_status_pill(
            theme,
            ok=saved,
            label=txt["key_status_set"] if saved else txt["key_status_unset"],
        )
    )

    feedback = ft.Text("", color=theme.text_muted, size=11)

    def _refresh_status() -> None:
        is_set = secrets.has_secret(name) if vault_ok else False
        status_holder.content = _status_pill(
            theme,
            ok=is_set,
            label=txt["key_status_set"] if is_set else txt["key_status_unset"],
        )
        logger_service.try_update(status_holder)

    def _set_feedback(message: str, *, ok: bool) -> None:
        feedback.value = message
        feedback.color = "#22C55E" if ok else "#EF4444"
        logger_service.try_update(feedback)

    def _on_save(_e: ft.ControlEvent) -> None:
        if not vault_ok:
            _set_feedback(txt["key_save_failed"], ok=False)
            logger_service.log_event(
                "WARNING", "settings.view", "key_save_no_vault", key_name=name
            )
            return
        value = (field.value or "").strip()
        if not value:
            _set_feedback(txt["key_save_empty"], ok=False)
            logger_service.log_event(
                "WARNING", "settings.view", "key_save_empty", key_name=name
            )
            return
        success = secrets.set_secret(name, value)
        if success:
            field.value = ""
            try:
                field.update()
            except Exception as exc:
                logger_service.log_exception("settings.view", "key_field_update", exc)
            _set_feedback(txt["key_save_ok"], ok=True)
            _refresh_status()
            logger_service.log_event("INFO", "settings.view", "key_saved", key_name=name)
        else:
            _set_feedback(txt["key_save_failed"], ok=False)
            logger_service.log_event(
                "ERROR", "settings.view", "key_save_failed", key_name=name
            )

    def _on_delete(_e: ft.ControlEvent) -> None:
        if not vault_ok or not secrets.has_secret(name):
            _set_feedback(txt["key_delete_failed"], ok=False)
            logger_service.log_event(
                "WARNING",
                "settings.view",
                "key_delete_unavailable",
                key_name=name,
                vault_ok=vault_ok,
            )
            return
        if secrets.delete_secret(name):
            _set_feedback(txt["key_delete_ok"], ok=True)
            _refresh_status()
            logger_service.log_event("INFO", "settings.view", "key_deleted", key_name=name)
        else:
            _set_feedback(txt["key_delete_failed"], ok=False)
            logger_service.log_event(
                "ERROR", "settings.view", "key_delete_failed", key_name=name
            )

    label_row = ft.Row(
        controls=[
            ft.Container(
                content=ft.Icon(key["icon"], color=key["color"], size=16),
                width=28,
                height=28,
                bgcolor=ft.Colors.with_opacity(0.15, key["color"]),
                border_radius=8,
                alignment=ft.Alignment.CENTER,
            ),
            ft.Text(key["label"], color=theme.text, size=13, weight=ft.FontWeight.W_600, expand=True),
            status_holder,
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    actions = ft.Row(
        controls=[
            field,
            _flat_button(theme, txt["key_save_btn"], icon=ft.Icons.LOCK_OUTLINE, primary=True, on_click=_on_save),
            _flat_button(theme, txt["key_delete_btn"], icon=ft.Icons.DELETE_OUTLINE, danger=True, on_click=_on_delete),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return ft.Container(
        content=ft.Column(
            controls=[label_row, actions, feedback],
            spacing=8,
            tight=True,
        ),
        padding=ft.padding.symmetric(horizontal=2, vertical=4),
    )


def _keys_card(theme: Theme, lang: str, txt: dict) -> ft.Control:
    vault_ok = secrets.is_available()
    rows: list[ft.Control] = []
    if not vault_ok:
        rows.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(txt["vault_unavailable_title"], color="#EF4444", size=13, weight=ft.FontWeight.W_700),
                        ft.Text(txt["vault_unavailable_desc"], color=theme.text_muted, size=12),
                    ],
                    spacing=4,
                    tight=True,
                ),
                padding=12,
                bgcolor=ft.Colors.with_opacity(0.10, "#EF4444"),
                border_radius=10,
                border=ft.border.all(1, ft.Colors.with_opacity(0.40, "#EF4444")),
            )
        )
    for key in key_rows(txt):
        rows.append(_key_row(theme, txt, key, vault_ok))
        rows.append(
            ft.Container(height=1, bgcolor=theme.border, margin=ft.margin.only(top=4, bottom=4))
        )
    if rows and isinstance(rows[-1], ft.Container) and rows[-1].height == 1:
        rows.pop()

    desc = txt["keys_card_desc_template"].format(keystore=settings_store.keystore_label())

    return _card(
        theme,
        icon=ft.Icons.LOCK_OUTLINE,
        title=txt["keys_card_title"],
        desc=desc,
        body=ft.Column(controls=rows, spacing=6, tight=True),
    )


def _general_card(
    theme: Theme,
    lang: str,
    txt: dict,
    *,
    on_view_logs: Callable[[], None],
) -> ft.Control:
    def _on_demo_change(e: ft.ControlEvent) -> None:
        new_value = bool(e.control.value)
        settings_store.set_demo_default(new_value)
        logger_service.log_event(
            "INFO", "settings.view", "demo_default_changed", value=new_value
        )

    demo_switch = ft.Switch(
        value=settings_store.get_demo_default(),
        active_color=theme.primary,
        on_change=_on_demo_change,
        scale=0.9,
    )

    def _toggle_row(label: str, desc: str, switch: ft.Switch) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(label, color=theme.text, size=13, weight=ft.FontWeight.W_600),
                            ft.Text(desc, color=theme.text_muted, size=12),
                        ],
                        spacing=2,
                        tight=True,
                        expand=True,
                    ),
                    switch,
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=2, vertical=8),
        )

    def _on_open_log_folder(_e: ft.ControlEvent) -> None:
        logger_service.log_event("INFO", "settings.view", "open_log_folder")
        logger_service.open_log_dir_in_explorer()

    logs_row = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text(
                                    txt["logs_card_label"],
                                    color=theme.text,
                                    size=13,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Text(
                                    txt["logs_card_desc"],
                                    color=theme.text_muted,
                                    size=12,
                                ),
                            ],
                            spacing=2,
                            tight=True,
                            expand=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[
                        _flat_button(
                            theme,
                            txt["logs_view_btn"],
                            icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                            primary=True,
                            on_click=lambda e: on_view_logs(),
                        ),
                        _flat_button(
                            theme,
                            txt["logs_open_folder_btn"],
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=_on_open_log_folder,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=10,
            tight=True,
        ),
        padding=ft.padding.symmetric(horizontal=2, vertical=8),
    )

    body = ft.Column(
        controls=[
            _toggle_row(
                txt["general_demo_default_label"],
                txt["general_demo_default_desc"],
                demo_switch,
            ),
            ft.Container(
                height=1,
                bgcolor=theme.border,
                margin=ft.margin.only(top=2, bottom=2),
            ),
            logs_row,
        ],
        spacing=4,
        tight=True,
    )

    return _card(
        theme,
        icon=ft.Icons.TUNE,
        title=txt["general_card_title"],
        desc="",
        body=body,
    )


def _logs_view(
    theme: Theme,
    txt: dict,
    *,
    on_back: Callable[[], None],
) -> ft.Control:
    """Tail of ``app.log`` with Refresh / Copy / Open folder / Clear actions.

    UX choices:

    * One ``ft.Text`` per log line (so we can colour ERROR / WARNING
      rows red / amber for skim-friendliness).
    * Wrapped in ``ft.SelectionArea`` so mouse drag-select spans
      multiple rows - native ``selectable=True`` on each ``ft.Text``
      only selects within one line at a time, which is what the user
      hit before this refactor.
    * Copy goes through :mod:`src.services.clipboard`, a synchronous
      pyperclip-first helper. The previous implementation used
      ``ft.Clipboard().set(...)`` which dies with
      ``RuntimeError("Session closed")`` after the page session enters
      a half-closed state - users saw the Copy button doing nothing
      while the log filled with ``logs_copy_failed`` traces.
    """

    log_column = ft.Column(
        controls=[],
        spacing=0,
        tight=True,
    )
    selectable_log = ft.SelectionArea(content=log_column)
    scroll_holder = ft.Column(
        controls=[selectable_log],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=0,
        tight=True,
    )
    log_box = ft.Container(
        content=ft.Container(
            content=scroll_holder,
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            expand=True,
        ),
        bgcolor=theme.surface_2,
        border_radius=10,
        border=ft.border.all(1, theme.border),
        expand=True,
    )
    status_text = ft.Text("", color=theme.text_muted, size=11)

    def _refresh_log(*, after_action_message: str = "", after_color: str = "") -> None:
        body = logger_service.read_log()
        if body:
            controls = _log_line_controls(body, theme)
        else:
            controls = [
                ft.Text(
                    txt["logs_empty"],
                    color=theme.text_muted,
                    size=12,
                    font_family="Consolas, Menlo, monospace",
                )
            ]
        log_column.controls = controls
        # During the initial build of the Logs view we set ``controls``
        # and call ``update()`` before the column is mounted on the
        # page. Flet 0.84 raises ``RuntimeError`` in that case; the
        # ``try_update`` helper silences the expected mount error so
        # the log file does not fill with bogus traces (real update
        # errors still raise).
        logger_service.try_update(log_column)
        if after_action_message:
            status_text.value = after_action_message
            status_text.color = after_color or theme.text_muted
        else:
            status_text.value = ""
            status_text.color = theme.text_muted
        logger_service.try_update(status_text)

    def _on_refresh(_e: ft.ControlEvent) -> None:
        logger_service.log_event("INFO", "settings.view", "logs_refresh")
        _refresh_log()

    def _on_copy(_e: ft.ControlEvent) -> None:
        body = logger_service.read_log()
        if not body:
            _refresh_log(
                after_action_message=txt["logs_empty"],
                after_color=theme.text_muted,
            )
            return
        # Synchronous pyperclip-backed helper; no asyncio, no Flet
        # session involved, so the previous "Session closed" race
        # cannot happen any more.
        ok = clipboard.copy(body)
        if ok:
            logger_service.log_event(
                "INFO", "settings.view", "logs_copied",
                chars=len(body), backend=clipboard.backend_name(),
            )
            _refresh_log(
                after_action_message=txt["logs_copy_done"],
                after_color="#22C55E",
            )
        else:
            logger_service.log_event(
                "ERROR", "settings.view", "logs_copy_failed_sync",
                backend=clipboard.backend_name(),
            )
            _refresh_log(
                after_action_message=txt["logs_copy_failed"],
                after_color="#EF4444",
            )

    def _on_clear(_e: ft.ControlEvent) -> None:
        ok = logger_service.clear_log()
        if ok:
            _refresh_log(after_action_message=txt["logs_clear_done"], after_color="#22C55E")
        else:
            _refresh_log(after_action_message=txt["logs_clear_failed"], after_color="#EF4444")

    def _on_open_folder(_e: ft.ControlEvent) -> None:
        logger_service.log_event("INFO", "settings.view", "open_log_folder")
        logger_service.open_log_dir_in_explorer()

    def _on_back(_e: ft.ControlEvent) -> None:
        logger_service.log_event("INFO", "settings.view", "logs_back")
        on_back()

    header_row = ft.Row(
        controls=[
            _flat_button(
                theme,
                txt["logs_back_btn"],
                icon=ft.Icons.ARROW_BACK,
                on_click=_on_back,
            ),
            ft.Container(
                content=ft.Text(
                    txt["logs_view_title"],
                    color=theme.text,
                    size=15,
                    weight=ft.FontWeight.W_700,
                ),
                padding=ft.padding.only(left=10),
                expand=True,
            ),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    description = ft.Text(txt["logs_view_desc"], color=theme.text_muted, size=12)
    log_path_text = ft.Text(
        txt["logs_path_template"].format(path=str(logger_service.log_path())),
        color=theme.text_subtle,
        size=11,
        italic=True,
        selectable=True,
    )
    selection_hint = ft.Text(
        txt["logs_selection_hint"],
        color=theme.text_subtle,
        size=11,
        italic=True,
    )

    actions = ft.Row(
        controls=[
            _flat_button(
                theme,
                txt["logs_refresh_btn"],
                icon=ft.Icons.REFRESH,
                primary=True,
                on_click=_on_refresh,
            ),
            _flat_button(
                theme,
                txt["logs_copy_btn"],
                icon=ft.Icons.COPY_ALL,
                on_click=_on_copy,
            ),
            _flat_button(
                theme,
                txt["logs_open_folder_btn"],
                icon=ft.Icons.FOLDER_OPEN,
                on_click=_on_open_folder,
            ),
            _flat_button(
                theme,
                txt["logs_clear_btn"],
                icon=ft.Icons.DELETE_SWEEP_OUTLINED,
                danger=True,
                on_click=_on_clear,
            ),
            ft.Container(expand=True),
            status_text,
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    _refresh_log()

    body = ft.Column(
        controls=[
            header_row,
            description,
            log_path_text,
            selection_hint,
            actions,
            log_box,
        ],
        spacing=12,
        expand=True,
    )

    return ft.Container(
        content=body,
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        bgcolor=theme.surface,
        border_radius=16,
        border=ft.border.all(1, theme.border),
        expand=True,
    )


def build_view(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)

    body_holder = ft.Container(expand=True)
    mode_holder = {"value": MODE_MAIN}

    def _rerender_body() -> None:
        if mode_holder["value"] == MODE_LOGS:
            body_holder.content = ft.Container(
                content=_logs_view(theme, txt, on_back=_show_main),
                padding=ft.padding.symmetric(horizontal=24, vertical=20),
                expand=True,
            )
        else:
            body_holder.content = ft.ListView(
                controls=[
                    _provider_card(theme, lang, txt, on_provider_change=_rerender_body),
                    _keys_card(theme, lang, txt),
                    _general_card(theme, lang, txt, on_view_logs=_show_logs),
                ],
                spacing=16,
                padding=ft.padding.symmetric(horizontal=24, vertical=20),
                expand=True,
            )
        # ``_rerender_body`` is also called once during the initial
        # ``build_view`` run (line at the bottom of this function) - at
        # that point ``body_holder`` is not yet on the page and
        # ``update()`` raises ``RuntimeError``. ``try_update`` swallows
        # only that case so the first paint stays quiet.
        logger_service.try_update(body_holder)

    def _show_logs() -> None:
        logger_service.log_event("INFO", "settings.view", "logs_view_open")
        mode_holder["value"] = MODE_LOGS
        _rerender_body()

    def _show_main() -> None:
        logger_service.log_event("INFO", "settings.view", "logs_view_close")
        mode_holder["value"] = MODE_MAIN
        _rerender_body()

    _rerender_body()

    return ft.Column(
        controls=[
            header(
                theme,
                lang,
                icon=SECTION_ICON,
                title=txt["title"],
                subtitle=txt["subtitle"],
            ),
            body_holder,
        ],
        spacing=0,
        expand=True,
        tight=True,
    )
