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
import pkgutil

from src.sections._base import Section
from src.services import logger as logger_service
from src.services import settings_store


def _discover() -> list[Section]:
    """Enumerate every ``src.sections.<key>`` subpackage and pull its SECTION.

    Uses :func:`pkgutil.iter_modules` instead of a raw ``Path.iterdir``
    walk so the discovery works identically in dev mode (running from
    source) and inside a PyInstaller ``--onefile`` bundle. In the
    frozen ``.exe`` the section ``.py`` files live inside the PYZ
    archive and the package folder does **not** exist on disk under
    ``sys._MEIPASS\\src\\sections\\``, which made the previous
    ``iterdir()`` raise ``FileNotFoundError`` at import time and the
    whole application failed to start.

    For ``pkgutil.iter_modules`` to actually see the subpackages in a
    frozen bundle, ``build_exe.bat`` passes
    ``--collect-submodules src.sections`` to PyInstaller.
    """
    sections: list[Section] = []
    discovered: list[str] = sorted(
        info.name
        for info in pkgutil.iter_modules(__path__)
        if info.ispkg
        and not info.name.startswith("_")
        and not info.name.startswith(".")
        and info.name != "SECTION_TEMPLATE"
    )

    for name in discovered:
        module_name = f"src.sections.{name}.section"
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


def _apply_user_order(primary: list[Section]) -> list[Section]:
    """Reorder the primary sidebar list per the user's drag-and-drop save.

    Sections present in ``settings_store.get_sidebar_order()`` come first
    in the saved order. Anything missing (e.g. a newly added section that
    the user has not seen yet) is appended at the end in the default
    ``(order, key)`` sort so authoring intent still wins for newcomers.
    Stale keys (saved orders that reference a deleted section folder)
    are silently dropped.
    """
    try:
        saved = settings_store.get_sidebar_order()
    except Exception as exc:
        logger_service.log_exception(
            "sections", "apply_user_order_read_failed", exc,
        )
        return primary
    if not saved:
        return primary

    by_key = {s.key: s for s in primary}
    ordered: list[Section] = []
    seen: set[str] = set()
    for key in saved:
        section = by_key.get(key)
        if section is None or key in seen:
            continue
        ordered.append(section)
        seen.add(key)
    for section in primary:
        if section.key in seen:
            continue
        ordered.append(section)
    return ordered


SECTIONS: list[Section] = _discover()
SECTION_BY_KEY: dict[str, Section] = {s.key: s for s in SECTIONS}

# Hidden sections stay in ``SECTIONS`` / ``SECTION_BY_KEY`` so a stale
# ``set_section("dashboard")`` deep-link still resolves to the safe-build
# panel - they just do not appear in the sidebar lists below.
_VISIBLE: list[Section] = [s for s in SECTIONS if not s.hidden]
_PRIMARY_DEFAULT: list[Section] = [s for s in _VISIBLE if s.nav_group == "primary"]
PRIMARY_SECTIONS: list[Section] = _apply_user_order(_PRIMARY_DEFAULT)
SECONDARY_SECTIONS: list[Section] = [s for s in _VISIBLE if s.nav_group == "secondary"]


def reload_primary_order() -> None:
    """Reapply the persisted sidebar order in place.

    Called by :mod:`src.components.sidebar` after a drag-and-drop reorder
    so ``PRIMARY_SECTIONS`` reflects the new layout without an app
    restart. The list object identity is preserved on purpose - other
    modules import this name directly and we want their reference to
    stay valid.
    """
    PRIMARY_SECTIONS[:] = _apply_user_order(_PRIMARY_DEFAULT)


__all__ = [
    "Section",
    "SECTIONS",
    "SECTION_BY_KEY",
    "PRIMARY_SECTIONS",
    "SECONDARY_SECTIONS",
    "reload_primary_order",
]
