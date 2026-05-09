"""Mini palette for the LinkedIn profile summary HTML.

Two presets:

* ``DEFAULT_THEME`` - neutral indigo accent that matches the rest of
  AI Hub's primary buttons.
* ``LINKEDIN_BLUE`` - the iconic LinkedIn blue, useful when the user
  wants a profile-summary HTML that visually echoes the LinkedIn UI
  (handy for sharing the file with a recruiter).

The HTML output uses CSS custom properties so swapping the theme is a
single ``--accent`` rewrite away.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProfileTheme:
    slug: str
    accent: str
    accent_dark: str
    bg: str
    bg_alt: str
    ink: str
    muted: str
    border: str


DEFAULT_THEME = ProfileTheme(
    slug="indigo",
    accent="#4F46E5",
    accent_dark="#3730A3",
    bg="#FFFFFF",
    bg_alt="#F8FAFC",
    ink="#0F172A",
    muted="#475569",
    border="#E2E8F0",
)


LINKEDIN_BLUE = ProfileTheme(
    slug="linkedin",
    accent="#0A66C2",
    accent_dark="#004182",
    bg="#FFFFFF",
    bg_alt="#F4F8FB",
    ink="#0B2545",
    muted="#475569",
    border="#D9E5F0",
)


_THEMES: dict[str, ProfileTheme] = {
    DEFAULT_THEME.slug: DEFAULT_THEME,
    LINKEDIN_BLUE.slug: LINKEDIN_BLUE,
}


def resolve_theme(slug: str | None) -> ProfileTheme:
    if not slug:
        return DEFAULT_THEME
    return _THEMES.get(slug, DEFAULT_THEME)
