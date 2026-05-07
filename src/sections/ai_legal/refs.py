"""Cross-callback bridge for the AI Legal section.

The center column (``view.py``) and the right context panel
(``context.py``) live in two separate calls from
:meth:`src.app.AIHubApp.build`. They both want to re-render in response
to events triggered inside the *other* one - e.g. clicking *Zobrazit
detailní analýzu* in the right panel must switch the center column to
the Analysis tab; dropping a PDF onto the drop zone in the right panel
must update the chat header (which mentions the file name) on the
left.

To avoid threading an awkward "controller" through every helper, each
build registers a no-arg ``rerender`` lambda on this module-level
:class:`LegalRefs` singleton. Callbacks then just invoke whichever
side they need to refresh. Re-binding on every rebuild keeps the
closures pointing at the latest theme / lang.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class LegalRefs:
    rerender_main: Optional[Callable[[], None]] = None
    rerender_tab_body: Optional[Callable[[], None]] = None
    rerender_context: Optional[Callable[[], None]] = field(default=None)


REFS = LegalRefs()
