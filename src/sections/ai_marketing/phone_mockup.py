"""Instagram-post phone preview, drawn purely with Flet primitives.

Lives in the right side of the AI Marketing assistant message bubble. No
external image is used - everything is plain ``ft.Container`` / ``ft.Text``.
"""

from __future__ import annotations

import flet as ft

from src.sections.ai_marketing.strings import s
from src.theme import Theme


PHONE_BG_TOP = "#1A1140"
PHONE_BG_BOTTOM = "#2D1568"
ACCENT = "#F0489E"
CARD_BG = "#FFFFFF"
CARD_TEXT = "#0F172A"
CHART_BAR = "#F59E0B"
CHART_BAR_DIM = "#FED7AA"
STORE_BG = "#0B0B14"


def _chart_bars() -> ft.Row:
    heights = [22, 30, 18, 36, 26, 42, 32]
    bars = []
    for i, h in enumerate(heights):
        bars.append(
            ft.Container(
                width=8,
                height=h,
                bgcolor=CHART_BAR if i % 2 == 0 else CHART_BAR_DIM,
                border_radius=2,
            )
        )
    return ft.Row(
        controls=bars,
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.END,
    )


def _balance_card(lang: str) -> ft.Container:
    txt = s(lang)
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            txt["phone_overview"],
                            color=CARD_TEXT,
                            size=10,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Container(expand=True),
                        ft.Icon(ft.Icons.MORE_HORIZ, color="#94A3B8", size=12),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(
                    txt["phone_balance"],
                    color=CARD_TEXT,
                    size=14,
                    weight=ft.FontWeight.W_700,
                ),
                ft.Container(height=2),
                _chart_bars(),
            ],
            spacing=4,
            tight=True,
        ),
        padding=10,
        bgcolor=CARD_BG,
        border_radius=10,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=8,
            color=ft.Colors.with_opacity(0.18, ft.Colors.BLACK),
            offset=ft.Offset(0, 2),
        ),
    )


def _cta_button(lang: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            s(lang)["phone_cta"],
            color=ft.Colors.WHITE,
            size=11,
            weight=ft.FontWeight.W_700,
        ),
        bgcolor=ACCENT,
        padding=ft.padding.symmetric(horizontal=14, vertical=8),
        border_radius=20,
        alignment=ft.Alignment.CENTER,
    )


def _store_badge(lang: str, *, kind: str) -> ft.Container:
    txt = s(lang)
    if kind == "apple":
        icon = ft.Icons.APPLE
        caption = txt["phone_app_store_caption"]
        store_name = txt["phone_app_store"]
    else:
        icon = ft.Icons.PLAY_ARROW_ROUNDED
        caption = txt["phone_play_store_caption"]
        store_name = txt["phone_play_store"]

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=ft.Colors.WHITE, size=14),
                ft.Column(
                    controls=[
                        ft.Text(caption, color=ft.Colors.WHITE, size=7),
                        ft.Text(
                            store_name,
                            color=ft.Colors.WHITE,
                            size=10,
                            weight=ft.FontWeight.W_700,
                        ),
                    ],
                    spacing=0,
                    tight=True,
                ),
            ],
            spacing=4,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        bgcolor=STORE_BG,
        border_radius=6,
    )


def _page_dots() -> ft.Row:
    dots = []
    for i in range(4):
        dots.append(
            ft.Container(
                width=6 if i == 0 else 4,
                height=4,
                bgcolor=ft.Colors.WHITE if i == 0 else ft.Colors.with_opacity(0.4, ft.Colors.WHITE),
                border_radius=2,
            )
        )
    return ft.Row(
        controls=dots,
        spacing=4,
        alignment=ft.MainAxisAlignment.CENTER,
        tight=True,
    )


def phone_mockup(theme: Theme, lang: str) -> ft.Container:
    txt = s(lang)

    headline = ft.Column(
        controls=[
            ft.Text(
                txt["phone_headline_top"],
                color=ft.Colors.WHITE,
                size=22,
                weight=ft.FontWeight.W_800,
            ),
            ft.Text(
                txt["phone_headline_bottom"],
                color=ACCENT,
                size=22,
                weight=ft.FontWeight.W_800,
            ),
        ],
        spacing=0,
        tight=True,
    )

    subtitle = ft.Text(
        txt["phone_subtitle"],
        color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE),
        size=10,
    )

    inner = ft.Container(
        content=ft.Column(
            controls=[
                headline,
                subtitle,
                ft.Container(height=2),
                _balance_card(lang),
                ft.Row(
                    controls=[_cta_button(lang)],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Row(
                    controls=[
                        _store_badge(lang, kind="apple"),
                        _store_badge(lang, kind="play"),
                    ],
                    spacing=6,
                ),
                ft.Container(expand=True),
                _page_dots(),
            ],
            spacing=8,
            tight=True,
            expand=True,
        ),
        padding=ft.padding.only(left=16, right=16, top=18, bottom=14),
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[PHONE_BG_TOP, PHONE_BG_BOTTOM],
        ),
        border_radius=22,
        width=210,
        height=320,
    )

    return ft.Container(
        content=inner,
        padding=4,
        bgcolor="#0B0B14",
        border_radius=26,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=22,
            color=ft.Colors.with_opacity(0.32, ft.Colors.BLACK),
            offset=ft.Offset(0, 10),
        ),
    )
