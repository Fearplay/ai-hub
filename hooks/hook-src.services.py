"""PyInstaller hook for the ``src.services`` package.

The service layer is mostly statically imported, but a few helpers are
loaded lazily (``html_pdf`` reads its WeasyPrint / reportlab fallbacks
at first call; ``ai_provider`` defers ``openai`` / ``anthropic`` imports
to the first ``run()``). We previously relied on
``--collect-submodules src.services`` in ``build_exe.bat`` to bundle
everything, but the same PyInstaller quirk that swallowed our
``--collect-submodules src.sections`` flag (after we added
``--collect-all qtawesome``) also dropped most services. To keep the
frozen ``AIHub.exe`` self-contained, this hook explicitly lists every
``.py`` file under ``src/services/`` as a hidden import.
"""

from __future__ import annotations

from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SERVICES_DIR = _HERE.parent / "src" / "services"

hiddenimports: list[str] = []

if _SERVICES_DIR.is_dir():
    for member in sorted(_SERVICES_DIR.iterdir()):
        if member.suffix != ".py":
            continue
        stem = member.stem
        if stem.startswith("_"):
            continue
        hiddenimports.append(f"src.services.{stem}")
