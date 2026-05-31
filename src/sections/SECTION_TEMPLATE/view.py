"""Center view for this section.

Most sections will want to compose:

* :func:`src.components.header.header`
* :func:`src.components.tab_bar.tab_bar`
* :func:`src.components.chat_message.chat_message`
* :func:`src.components.chat_input.chat_input`

See ``src/sections/ai_cv/view.py`` for a chat-style example or
``src/sections/ai_marketing/view.py`` for a richer custom layout.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from src.components.placeholder import placeholder_view
from src.sections.SECTION_TEMPLATE.strings import s
from src.theme import Theme


def build_view(theme: Theme, lang: str) -> QWidget:
    return placeholder_view(theme, lang, title=s(lang)["title"])
