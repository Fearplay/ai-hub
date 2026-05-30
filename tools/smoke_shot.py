"""Dev-only UI smoke test: screenshot a section at a target window size.

Boots the real :class:`src.app.AIHubApp`, navigates to a section, renders
it at a given window size, and saves a PNG so you (or the agent) can eyeball
overlapping widgets, clipped tiles, text cut off at the right edge, or
strikethrough *before* shipping. This mirrors the manual smoke pass we used
to do by hand.

This file lives **outside** ``src/`` on purpose so the PyInstaller hooks and
the section auto-discovery (``src/sections/__init__.py``) never pick it up -
it is a developer tool, not part of the shipped app.

See ``.cursor/rules/ui-smoke-test.mdc`` for when this must be run.

Usage (run from the repo root)::

    python tools/smoke_shot.py --section ai_linkedin
    python tools/smoke_shot.py --section ai_linkedin --lang cs --theme dark --size 1220x760
    python tools/smoke_shot.py --section my_profile --lang en --theme light
    python tools/smoke_shot.py --all

The default size is the application's minimum window size (1220x760), which
is where right-edge clipping shows up first. Screenshots are written to the
git-ignored ``.smoke/`` folder. On success the script prints each saved size
and a final ``SMOKE_PASS`` line.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make ``import src...`` work no matter the current working directory.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _parse_size(text: str) -> tuple[int, int]:
    try:
        raw_w, raw_h = text.lower().split("x", 1)
        return int(raw_w), int(raw_h)
    except Exception as exc:  # noqa: BLE001 - argparse surfaces the message
        raise argparse.ArgumentTypeError(
            f"invalid --size {text!r}, expected WxH like 1220x760"
        ) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI Hub UI smoke screenshot")
    parser.add_argument("--section", default="ai_linkedin", help="section key to render")
    parser.add_argument("--lang", default="cs", choices=["en", "cs"])
    parser.add_argument("--theme", default="dark", choices=["dark", "light"])
    parser.add_argument(
        "--size",
        default=(1220, 760),
        type=_parse_size,
        help="window size WxH (default 1220x760 = the app minimum)",
    )
    parser.add_argument("--out", default="", help="explicit output PNG path (single section only)")
    parser.add_argument("--settle-ms", default=700, type=int, help="event-loop settle time before grab")
    parser.add_argument("--all", action="store_true", help="shoot every visible section")
    args = parser.parse_args(argv)

    # Qt / app imports happen after the sys.path fix above.
    from PySide6.QtCore import Qt, QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication

    from src.app import AIHubApp
    from src.i18n import normalize_lang
    from src.sections import SECTION_BY_KEY, SECTIONS

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication.instance() or QApplication(sys.argv[:1])

    width, height = args.size
    out_dir = _REPO_ROOT / ".smoke"
    out_dir.mkdir(parents=True, exist_ok=True)

    def _settle(ms: int) -> None:
        loop = QEventLoop()
        QTimer.singleShot(max(0, ms), loop.quit)
        loop.exec()

    failures: list[str] = []

    def _shoot(section_key: str) -> None:
        if section_key not in SECTION_BY_KEY:
            print(f"!! unknown section {section_key!r} - skipping")
            failures.append(section_key)
            return
        window = AIHubApp()
        window.theme_mode = args.theme
        window.lang = normalize_lang(args.lang)
        window.active_section = section_key
        window.build()
        window.resize(width, height)
        window.show()
        _settle(args.settle_ms)

        pixmap = window.grab()
        if args.out and not args.all:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            out_path = out_dir / f"{section_key}-{args.lang}-{args.theme}-{width}x{height}.png"

        if pixmap.isNull() or not pixmap.save(str(out_path)):
            print(f"!! failed to save screenshot for {section_key} -> {out_path}")
            failures.append(section_key)
        else:
            print(f"{section_key}: {pixmap.size()} -> {out_path}")

        window.close()
        window.deleteLater()
        _settle(60)

    if args.all:
        targets = [s.key for s in SECTIONS if not s.hidden]
    else:
        targets = [args.section]

    for key in targets:
        _shoot(key)

    if failures:
        print(f"SMOKE_FAIL ({len(failures)}): {', '.join(failures)}")
        return 1

    print("SMOKE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
