"""Settings - main center view.

Three stacked cards:

* **Provider & model** - provider radio + model dropdown with a free-text
  override field for unknown / future model ids.
* **API keys** - three rows (OpenAI, Anthropic, GitHub). Each row holds an
  obscured text field, a Save button (writes to the OS keystore via
  :mod:`src.services.secrets`), a Delete button, and a status pill.
* **General** - demo-mode default and follow-up question toggles.

Status feedback is rendered inline next to each row so the user does not
miss it when the snackbar dismisses.
"""

from __future__ import annotations

from typing import Callable

import flet as ft

from src.components.header import header
from src.services import secrets, settings_store
from src.sections.settings.data import SECTION_ICON, key_rows
from src.sections.settings.strings import s
from src.theme import Theme


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
        try:
            chip_row.update()
        except Exception:
            pass

    def _set_model_text(value: str) -> None:
        model_field.value = value
        try:
            model_field.update()
        except Exception:
            pass

    save_status = ft.Text("", color="#22C55E", size=12, weight=ft.FontWeight.W_500)

    def _save_model(_e: ft.ControlEvent) -> None:
        provider = settings_store.get_provider()
        value = (model_field.value or "").strip()
        if not value:
            save_status.value = txt["model_invalid"]
            save_status.color = "#EF4444"
        else:
            settings_store.set_model(provider, value)
            save_status.value = txt["model_saved"]
            save_status.color = "#22C55E"
        try:
            save_status.update()
        except Exception:
            pass

    def _on_radio_change(e: ft.ControlEvent) -> None:
        provider = e.control.value
        if provider not in (settings_store.PROVIDER_OPENAI, settings_store.PROVIDER_ANTHROPIC):
            return
        settings_store.set_provider(provider)
        model_field.value = settings_store.get_model(provider)
        try:
            model_field.update()
        except Exception:
            pass
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
        try:
            status_holder.update()
        except Exception:
            pass

    def _set_feedback(message: str, *, ok: bool) -> None:
        feedback.value = message
        feedback.color = "#22C55E" if ok else "#EF4444"
        try:
            feedback.update()
        except Exception:
            pass

    def _on_save(_e: ft.ControlEvent) -> None:
        if not vault_ok:
            _set_feedback(txt["key_save_failed"], ok=False)
            return
        value = (field.value or "").strip()
        if not value:
            _set_feedback(txt["key_save_empty"], ok=False)
            return
        success = secrets.set_secret(name, value)
        if success:
            field.value = ""
            try:
                field.update()
            except Exception:
                pass
            _set_feedback(txt["key_save_ok"], ok=True)
            _refresh_status()
        else:
            _set_feedback(txt["key_save_failed"], ok=False)

    def _on_delete(_e: ft.ControlEvent) -> None:
        if not vault_ok or not secrets.has_secret(name):
            _set_feedback(txt["key_delete_failed"], ok=False)
            return
        if secrets.delete_secret(name):
            _set_feedback(txt["key_delete_ok"], ok=True)
            _refresh_status()
        else:
            _set_feedback(txt["key_delete_failed"], ok=False)

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


def _general_card(theme: Theme, lang: str, txt: dict) -> ft.Control:
    demo_switch = ft.Switch(
        value=settings_store.get_demo_default(),
        active_color=theme.primary,
        on_change=lambda e: settings_store.set_demo_default(bool(e.control.value)),
        scale=0.9,
    )
    followups_switch = ft.Switch(
        value=settings_store.get_ask_followups(),
        active_color=theme.primary,
        on_change=lambda e: settings_store.set_ask_followups(bool(e.control.value)),
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

    body = ft.Column(
        controls=[
            _toggle_row(txt["general_demo_default_label"], txt["general_demo_default_desc"], demo_switch),
            ft.Container(height=1, bgcolor=theme.border),
            _toggle_row(txt["general_followups_label"], txt["general_followups_desc"], followups_switch),
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


def build_view(theme: Theme, lang: str) -> ft.Column:
    txt = s(lang)

    body_holder = ft.Container(expand=True)

    def _rerender_body() -> None:
        body_holder.content = ft.ListView(
            controls=[
                _provider_card(theme, lang, txt, on_provider_change=_rerender_body),
                _keys_card(theme, lang, txt),
                _general_card(theme, lang, txt),
            ],
            spacing=16,
            padding=ft.padding.symmetric(horizontal=24, vertical=20),
            expand=True,
        )
        try:
            body_holder.update()
        except Exception:
            pass

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
