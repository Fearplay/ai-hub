"""One chat bubble (user or assistant).

Sections drive this with the data they own. Custom rich content can be
injected via ``extra`` (any Flet control appended at the end of the bubble).
"""

from __future__ import annotations

from typing import Optional, Sequence

import flet as ft

from src.components.document_chip import file_badge
from src.i18n import t
from src.theme import Theme


def _action_chip(theme: Theme, icon: str, label: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=theme.primary, size=14),
                ft.Text(
                    label,
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
        on_click=lambda e: None,
    )


def _attachment_card(theme: Theme, lang: str, attachment: dict) -> ft.Container:
    download_btn = ft.Container(
        content=ft.Row(
            controls=[
                ft.Text(t("download", lang), color=theme.text, size=12, weight=ft.FontWeight.W_500),
                ft.Icon(ft.Icons.FILE_DOWNLOAD_OUTLINED, color=theme.text, size=14),
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
        on_click=lambda e: None,
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                file_badge(theme, attachment["type"], size=40),
                ft.Column(
                    controls=[
                        ft.Text(
                            attachment["name"],
                            color=theme.text,
                            size=13,
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Text(
                            f"{attachment['type']} • {attachment['size']}",
                            color=theme.text_muted,
                            size=11,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                download_btn,
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=10,
        bgcolor=theme.surface,
        border_radius=10,
        border=ft.border.all(1, theme.border),
    )


def _bullet_row(theme: Theme, text: str, *, marker: str = "•") -> ft.Row:
    return ft.Row(
        controls=[
            ft.Container(
                content=ft.Text(
                    marker,
                    color=theme.primary if marker != "•" else theme.text,
                    size=14,
                    weight=ft.FontWeight.W_700,
                ),
                width=18,
                alignment=ft.Alignment.CENTER,
            ),
            ft.Text(
                text,
                color=theme.text,
                size=14,
                expand=True,
                selectable=True,
            ),
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def _user_message(
    theme: Theme,
    *,
    time: str,
    text: str,
) -> ft.Row:
    bubble = ft.Container(
        content=ft.Text(
            text,
            color=theme.user_bubble_text,
            size=14,
            selectable=True,
        ),
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
                        content=ft.Text(time, color=theme.text_muted, size=11),
                        padding=ft.padding.only(right=4),
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


def _assistant_message(
    theme: Theme,
    lang: str,
    *,
    avatar_icon: str,
    time: str,
    text: Optional[str] = None,
    bullets: Optional[Sequence[str]] = None,
    bullet_marker: str = "•",
    sections: Optional[Sequence[dict]] = None,
    footer: Optional[str] = None,
    actions: Optional[Sequence[dict]] = None,
    attachment: Optional[dict] = None,
    extra: Optional[ft.Control] = None,
) -> ft.Row:
    bubble_children: list[ft.Control] = []

    if text:
        bubble_children.append(
            ft.Text(text, color=theme.text, size=14, selectable=True)
        )

    if sections:
        for section in sections:
            heading = ft.Row(
                controls=[
                    ft.Icon(
                        section.get("icon", ft.Icons.AUTO_AWESOME),
                        color=theme.primary,
                        size=16,
                    ),
                    ft.Text(
                        section["title"],
                        color=theme.primary,
                        size=13,
                        weight=ft.FontWeight.W_700,
                    ),
                ],
                spacing=6,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            block_children: list[ft.Control] = [heading]
            if section.get("text"):
                block_children.append(
                    ft.Text(section["text"], color=theme.text, size=14, selectable=True)
                )
            if section.get("bullets"):
                block_children.append(
                    ft.Column(
                        controls=[
                            _bullet_row(theme, b, marker=section.get("marker", "•"))
                            for b in section["bullets"]
                        ],
                        spacing=4,
                        tight=True,
                    )
                )
            bubble_children.append(
                ft.Column(controls=block_children, spacing=8, tight=True)
            )

    if bullets:
        bubble_children.append(
            ft.Column(
                controls=[_bullet_row(theme, b, marker=bullet_marker) for b in bullets],
                spacing=4,
                tight=True,
            )
        )

    if footer:
        bubble_children.append(
            ft.Text(footer, color=theme.text, size=14, selectable=True)
        )

    if extra is not None:
        bubble_children.append(extra)

    if attachment:
        bubble_children.append(_attachment_card(theme, lang, attachment))

    if actions:
        bubble_children.append(
            ft.Row(
                controls=[_action_chip(theme, a["icon"], a["label"]) for a in actions],
                spacing=8,
                wrap=True,
                run_spacing=8,
            )
        )

    bubble = ft.Container(
        content=ft.Column(
            controls=bubble_children,
            spacing=12,
            tight=True,
        ),
        padding=14,
        bgcolor=theme.assistant_bubble,
        border_radius=14,
    )

    avatar = ft.Container(
        content=ft.Icon(avatar_icon, color=ft.Colors.WHITE, size=18),
        width=36,
        height=36,
        bgcolor=theme.primary,
        border_radius=10,
        alignment=ft.Alignment.CENTER,
    )

    body = ft.Column(
        controls=[
            ft.Container(
                content=ft.Text(time, color=theme.text_muted, size=11),
                padding=ft.padding.only(left=4),
            ),
            bubble,
        ],
        spacing=4,
        expand=True,
        tight=True,
    )

    return ft.Row(
        controls=[avatar, body],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def chat_message(
    theme: Theme,
    lang: str,
    *,
    avatar_icon: str,
    role: str,
    time: str,
    text: Optional[str] = None,
    bullets: Optional[Sequence[str]] = None,
    bullet_marker: str = "•",
    sections: Optional[Sequence[dict]] = None,
    footer: Optional[str] = None,
    actions: Optional[Sequence[dict]] = None,
    attachment: Optional[dict] = None,
    extra: Optional[ft.Control] = None,
) -> ft.Row:
    if role == "user":
        return _user_message(theme, time=time, text=text or "")
    return _assistant_message(
        theme,
        lang,
        avatar_icon=avatar_icon,
        time=time,
        text=text,
        bullets=bullets,
        bullet_marker=bullet_marker,
        sections=sections,
        footer=footer,
        actions=actions,
        attachment=attachment,
        extra=extra,
    )
