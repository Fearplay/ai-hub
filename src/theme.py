"""Designové tokeny aplikace.

Centrální místo pro barvy a další konstanty. Komponenty si berou instanci
:class:`Theme` a barvy aplikují přímo na ovládací prvky Fletu - tím se
vyhneme komplikované interakci s vestavěným ``ft.Theme``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str

    bg: str
    sidebar_bg: str
    surface: str
    surface_2: str
    border: str

    primary: str
    primary_soft: str
    primary_hover: str
    primary_tint: str

    text: str
    text_muted: str
    text_subtle: str

    user_bubble: str
    user_bubble_text: str
    assistant_bubble: str

    badge: str

    file_pdf: str
    file_docx: str


DARK = Theme(
    name="dark",
    bg="#0E1525",
    sidebar_bg="#121A2E",
    surface="#161E36",
    surface_2="#1E2845",
    border="#28324F",
    primary="#7C5CFC",
    primary_soft="#6B5BFF",
    primary_hover="#9277FF",
    primary_tint="#1F1B3F",
    text="#E5E7EB",
    text_muted="#9CA3AF",
    text_subtle="#6B7280",
    user_bubble="#6B5BFF",
    user_bubble_text="#FFFFFF",
    assistant_bubble="#1B2440",
    badge="#7C5CFC",
    file_pdf="#EF4444",
    file_docx="#3B82F6",
)


LIGHT = Theme(
    name="light",
    bg="#F5F6FA",
    sidebar_bg="#FFFFFF",
    surface="#FFFFFF",
    surface_2="#F1F2F9",
    border="#E5E7EB",
    primary="#7C5CFC",
    primary_soft="#7C5CFC",
    primary_hover="#6B4DEF",
    primary_tint="#EFEAFF",
    text="#1F2937",
    text_muted="#6B7280",
    text_subtle="#9CA3AF",
    user_bubble="#7C5CFC",
    user_bubble_text="#FFFFFF",
    assistant_bubble="#F1F2F9",
    badge="#7C5CFC",
    file_pdf="#EF4444",
    file_docx="#3B82F6",
)


def get_theme(mode: str) -> Theme:
    return LIGHT if mode == "light" else DARK
