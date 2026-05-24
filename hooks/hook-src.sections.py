"""PyInstaller hook for the auto-discovered ``src.sections`` package.

Why this hook exists
====================

The runtime sidebar is populated by walking every ``src/sections/<key>/``
folder with :func:`pkgutil.iter_modules` and importing each
``<key>.section`` module dynamically (see ``src/sections/__init__.py``).

PyInstaller's static analyser cannot see those dynamic
``importlib.import_module(...)`` calls, so without help every section
module is left out of the bundle. We used to rely on
``--collect-submodules src.sections`` in ``build_exe.bat`` to fill that
gap, but adding ``--collect-all qtawesome`` for the new icon system
caused PyInstaller to silently drop our project-local submodule
collection (the bundled ``Analysis-00.toc`` ended up with only
``src.sections._base``, every section folder was missing, and the
frozen ``AIHub.exe`` booted with ``count=0`` in the discover log).

This hook makes the bundle deterministic: it enumerates the folders
that the runtime discovery will visit and explicitly lists every Python
file inside them as a hidden import. Adding a new section folder still
"just works" - the hook re-scans on every PyInstaller run, so
contributors do not have to remember to update ``build_exe.bat``.
"""

from __future__ import annotations

from pathlib import Path

# This file lives in ``<repo>/hooks/hook-src.sections.py`` and we need
# the ``<repo>/src/sections`` folder.
_HERE = Path(__file__).resolve().parent
_SECTIONS_DIR = _HERE.parent / "src" / "sections"

_SKIP_FOLDER_PREFIXES = ("_", ".")
_SKIP_FOLDER_NAMES = {"SECTION_TEMPLATE", "__pycache__"}

hiddenimports: list[str] = []

if _SECTIONS_DIR.is_dir():
    for section_dir in sorted(_SECTIONS_DIR.iterdir()):
        if not section_dir.is_dir():
            continue
        if section_dir.name in _SKIP_FOLDER_NAMES:
            continue
        if section_dir.name.startswith(_SKIP_FOLDER_PREFIXES):
            continue

        section_key = section_dir.name

        # Always pull in the package itself so ``importlib.import_module
        # ('src.sections.<key>.section')`` does not raise
        # ``ModuleNotFoundError`` even when the only thing the section
        # exports is ``section.py``.
        hiddenimports.append(f"src.sections.{section_key}")

        for member in sorted(section_dir.iterdir()):
            if member.suffix != ".py":
                continue
            stem = member.stem
            if stem.startswith("_") and stem != "__init__":
                continue
            if stem == "__init__":
                continue
            hiddenimports.append(f"src.sections.{section_key}.{stem}")
