"""Section auto-discovery.

Every subfolder of ``src/sections/`` whose name does not start with ``_`` is
imported and expected to expose a ``SECTION`` constant in its ``section.py``
module. Sections are sorted by ``(order, key)`` so two contributors who pick
the same ``order`` value still get a deterministic layout (and no merge
conflict on a shared registry list).

We expose two convenience views:

* :data:`PRIMARY_SECTIONS` — feature sections rendered in the upper sidebar
  list (Dashboard, AI Career, AI Legal, …).
* :data:`SECONDARY_SECTIONS` — auxiliary sections rendered under a divider
  at the bottom of the sidebar (History, Favorites, Settings).

Both are filtered slices of :data:`SECTIONS`, which keeps every section
addressable by key for ``app.set_section``.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from src.sections._base import Section
from src.services import logger as logger_service


def _discover() -> list[Section]:
    sections: list[Section] = []
    package_dir = Path(__file__).parent

    for entry in sorted(package_dir.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue
        if entry.name.startswith("_") or entry.name.startswith("."):
            continue
        if entry.name == "SECTION_TEMPLATE":
            continue

        module_name = f"src.sections.{entry.name}.section"
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
        except Exception as exc:
            logger_service.log_exception(
                "sections", "discover_import_failed", exc,
                module=module_name,
            )
            continue

        section = getattr(module, "SECTION", None)
        if isinstance(section, Section):
            sections.append(section)
        else:
            logger_service.log_event(
                "ERROR",
                "sections",
                "discover_no_section_constant",
                module=module_name,
                found=type(section).__name__ if section is not None else "None",
            )

    logger_service.log_event(
        "INFO", "sections", "discover_done",
        count=len(sections),
        keys=[s.key for s in sections],
    )
    sections.sort(key=lambda s: (s.order, s.key))
    return sections


SECTIONS: list[Section] = _discover()
SECTION_BY_KEY: dict[str, Section] = {s.key: s for s in SECTIONS}

PRIMARY_SECTIONS: list[Section] = [s for s in SECTIONS if s.nav_group == "primary"]
SECONDARY_SECTIONS: list[Section] = [s for s in SECTIONS if s.nav_group == "secondary"]


__all__ = [
    "Section",
    "SECTIONS",
    "SECTION_BY_KEY",
    "PRIMARY_SECTIONS",
    "SECONDARY_SECTIONS",
]
