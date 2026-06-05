"""Designové tokeny aplikace.

Centrální místo pro barvy a další konstanty. Komponenty si berou instanci
:class:`Theme` a barvy aplikují přímo na ovládací prvky Fletu - tím se
vyhneme komplikované interakci s vestavěným ``ft.Theme``.

Sekce mohou mít vlastní akcentovou barvu (``Section.accent``); aplikace
pak zavolá :meth:`Theme.with_accent`, které vrátí klon témata s novou
primární paletou (logo, aktivní položka v sidebaru, bublina uživatele,
tlačítko odeslat...). Ostatní tokeny (pozadí, povrchy, text) zůstávají
beze změny.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


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

    def with_accent(self, accent: str) -> "Theme":
        """Return a copy of this theme with ``accent`` swapped in for the
        primary color family. Useful for per-section accents (Finance =
        green, etc.) without touching the rest of the design tokens."""
        tint = _accent_tint(accent, self.name)
        return replace(
            self,
            primary=accent,
            primary_soft=accent,
            primary_hover=_lighten(accent, 0.15),
            primary_tint=tint,
            user_bubble=accent,
            badge=accent,
        )


def _accent_tint(accent: str, theme_name: str) -> str:
    """Subtle background fill matching the accent (used for the active
    sidebar row). Light themes get a paler tint so text stays readable."""
    if theme_name == "light":
        return _mix(accent, "#FFFFFF", 0.85)
    return _mix(accent, "#0E1525", 0.78)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def _mix(color_a: str, color_b: str, weight_b: float) -> str:
    """Linear blend of two hex colors. ``weight_b`` is how much of B."""
    weight_b = max(0.0, min(1.0, weight_b))
    ar, ag, ab = _hex_to_rgb(color_a)
    br, bg, bb = _hex_to_rgb(color_b)
    r = round(ar * (1 - weight_b) + br * weight_b)
    g = round(ag * (1 - weight_b) + bg * weight_b)
    b = round(ab * (1 - weight_b) + bb * weight_b)
    return _rgb_to_hex(r, g, b)


def _lighten(color: str, amount: float) -> str:
    return _mix(color, "#FFFFFF", amount)


DARK = Theme(
    name="dark",
    bg="#0E1525",
    sidebar_bg="#121A2E",
    surface="#161E36",
    surface_2="#1E2845",
    border="#28324F",
    primary="#3B82F6",
    primary_soft="#4F8DF5",
    primary_hover="#5B9CFF",
    primary_tint="#182D53",
    text="#E5E7EB",
    text_muted="#9CA3AF",
    text_subtle="#6B7280",
    user_bubble="#3B82F6",
    user_bubble_text="#FFFFFF",
    assistant_bubble="#1B2440",
    badge="#3B82F6",
    file_pdf="#EF4444",
    file_docx="#60A5FA",
)


LIGHT = Theme(
    name="light",
    bg="#F5F6FA",
    sidebar_bg="#FFFFFF",
    surface="#FFFFFF",
    surface_2="#F1F2F9",
    border="#E5E7EB",
    primary="#3B82F6",
    primary_soft="#3B82F6",
    primary_hover="#2C6FE0",
    primary_tint="#E2ECFE",
    text="#1F2937",
    text_muted="#6B7280",
    text_subtle="#9CA3AF",
    user_bubble="#3B82F6",
    user_bubble_text="#FFFFFF",
    assistant_bubble="#F1F2F9",
    badge="#3B82F6",
    file_pdf="#EF4444",
    file_docx="#2563EB",
)


def get_theme(mode: str) -> Theme:
    return LIGHT if mode == "light" else DARK
