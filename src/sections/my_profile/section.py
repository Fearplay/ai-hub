"""My Profile section registration.

The shared career profile lives at the top of the primary sidebar list
(``order=10``) because it is the data source the AI Career / AI Job Search
/ AI LinkedIn sections read from - the user fills it once, then the rest
reuse it.
"""

from __future__ import annotations

from src.sections._base import Section
from src.sections.my_profile.context import build_context
from src.sections.my_profile.data import ACCENT, SECTION_ICON
from src.sections.my_profile.strings import STRINGS
from src.sections.my_profile.view import build_view


SECTION = Section(
    key="my_profile",
    icon=SECTION_ICON,
    labels={lang: STRINGS[lang]["nav_label"] for lang in STRINGS},
    build_view=build_view,
    build_context=build_context,
    accent=ACCENT,  # teal - the shared-profile brand colour
    order=10,
    # Not a standalone nav row anymore - it is reached through the
    # account card pinned at the bottom of the sidebar (see
    # ``src/components/profile_card.py``). ``hidden`` keeps the section
    # in ``SECTION_BY_KEY`` so ``set_section("my_profile")`` still works
    # and it drops out of both the sidebar nav and the dashboard grid.
    hidden=True,
)
