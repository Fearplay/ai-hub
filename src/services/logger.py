"""Process-wide debug log used by the in-app Settings -> Logs viewer.

Why a custom helper instead of a bare ``logging.getLogger("aihub")``? Two
reasons:

1. The user wants a single file they can open / copy / clear from the
   Settings UI, so we control the file path + rotation policy here
   instead of letting every caller configure handlers ad-hoc.
2. Most call sites today swallow exceptions with ``try: ... except: pass``
   (see :mod:`src.app` and :mod:`src.sections.ai_career.view`). The
   :func:`log_exception` helper is a one-line replacement that keeps the
   ``except`` block silent for the user but writes the traceback to disk
   so we can debug after the fact.

Disk layout::

    ~/AI Hub/
        history.json
        settings.json
        logs/
            app.log         # current
            app.log.1       # rotated
            app.log.2
            app.log.3

Rotation kicks in at 1 MB per file; with three backups the worst-case
footprint is 4 MB, which is harmless on every supported OS.
"""

from __future__ import annotations

import logging
import os
import threading
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


_LOGGER_NAME = "aihub"
_MAX_BYTES = 1 * 1024 * 1024  # 1 MB per file
_BACKUP_COUNT = 3

_INIT_LOCK = threading.Lock()
_INITIALIZED = False


def log_dir() -> Path:
    return Path.home() / "AI Hub" / "logs"


def log_path() -> Path:
    return log_dir() / "app.log"


def _ensure_log_dir() -> Path:
    folder = log_dir()
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return folder


def _ensure_initialized() -> logging.Logger:
    """Lazy idempotent setup. Safe to call from any thread."""
    global _INITIALIZED
    logger = logging.getLogger(_LOGGER_NAME)
    if _INITIALIZED:
        return logger

    with _INIT_LOCK:
        if _INITIALIZED:
            return logger

        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        # Drop any handlers that survived a hot-reload during dev. The
        # rotating file handler in particular keeps a file descriptor
        # open, so we want exactly one of these per process.
        for existing in list(logger.handlers):
            try:
                logger.removeHandler(existing)
                existing.close()
            except Exception:
                pass

        _ensure_log_dir()

        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        try:
            file_handler = RotatingFileHandler(
                str(log_path()),
                maxBytes=_MAX_BYTES,
                backupCount=_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError:
            # Disk is read-only or the AI Hub folder cannot be created.
            # The stream handler below still gives us console output.
            pass

        try:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)
        except Exception:
            pass

        _INITIALIZED = True

    return logger


def _format_kwargs(kwargs: dict[str, Any]) -> str:
    if not kwargs:
        return ""
    parts: list[str] = []
    for key, value in kwargs.items():
        text = repr(value) if isinstance(value, str) and (" " in value or "=" in value) else str(value)
        parts.append(f"{key}={text}")
    return " " + " ".join(parts)


def _resolve_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    name = (level or "").strip().upper() or "INFO"
    return logging._nameToLevel.get(name, logging.INFO)  # type: ignore[attr-defined]


def log_event(level: str | int, area: str, event: str, **kwargs: Any) -> None:
    """Write a single structured line to ``app.log``.

    Example::

        log_event("INFO", "ai_career.view", "mode_change", index=1, new_mode="form")

    becomes::

        2026-05-09 13:47:11 INFO  [aihub] ai_career.view mode_change index=1 new_mode='form'
    """
    logger = _ensure_initialized()
    line = f"{area} {event}{_format_kwargs(kwargs)}"
    try:
        logger.log(_resolve_level(level), line)
    except Exception:
        pass


def log_exception(area: str, event: str, exc: BaseException, **kwargs: Any) -> None:
    """Write an ERROR line + the traceback for ``exc``.

    Use from any ``except`` block that previously did ``pass``: the user
    keeps seeing the same UI behaviour but we get a stack trace inside
    ``app.log`` to diagnose silent failures.
    """
    logger = _ensure_initialized()
    line = f"{area} {event} error={exc!r}{_format_kwargs(kwargs)}"
    try:
        logger.error(line)
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        if tb:
            logger.error("traceback:\n%s", tb.rstrip())
    except Exception:
        pass


def try_update(control: Any) -> bool:
    """Call ``control.update()`` best-effort and return whether it succeeded.

    In Flet 0.84 calling ``update()`` on a control that has not yet been
    mounted on the page raises ``RuntimeError("Control must be added to
    the page first")`` instead of silently no-oping like older versions.
    A bunch of our section views build holders, set their content and
    immediately call ``.update()`` on them - that update is harmless to
    skip on the *first* render (the parent's first paint will flush it
    anyway), but it spams the debug log with bogus error traces.

    Use this helper at every "set content + flush" call site that may
    run before the control is in the tree. Genuine update failures (like
    Flet rejecting a malformed property) still surface because we only
    swallow ``RuntimeError`` - everything else is re-raised so callers
    can choose to ``log_exception`` it.
    """
    try:
        control.update()
        return True
    except RuntimeError:
        return False


def read_log(max_chars: int = 200_000) -> str:
    """Return the tail of ``app.log`` (last ``max_chars`` characters).

    The rotated backup files are intentionally NOT concatenated - the
    in-app viewer shows the *current* file only, which is what users
    expect when they reproduce a bug and immediately open the log.
    """
    _ensure_initialized()
    path = log_path()
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if max_chars > 0 and len(text) > max_chars:
        return "... (truncated)\n" + text[-max_chars:]
    return text


def clear_log() -> bool:
    """Truncate ``app.log`` to zero bytes. Backups are kept untouched."""
    logger = _ensure_initialized()
    path = log_path()
    try:
        # Tell the rotating handler to release its descriptor first;
        # otherwise on Windows we cannot truncate the file from outside.
        for handler in logger.handlers:
            if isinstance(handler, RotatingFileHandler):
                try:
                    handler.flush()
                    handler.close()
                except Exception:
                    pass
        try:
            path.write_text("", encoding="utf-8")
        except OSError:
            return False

        # Rebuild the rotating file handler so subsequent log calls
        # land in the freshly truncated file (the closed handler above
        # is no longer hooked, so we add a new one and remove the dead).
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        new_handlers: list[logging.Handler] = []
        for handler in list(logger.handlers):
            if isinstance(handler, RotatingFileHandler):
                try:
                    logger.removeHandler(handler)
                except Exception:
                    pass
                continue
            new_handlers.append(handler)
        try:
            file_handler = RotatingFileHandler(
                str(path),
                maxBytes=_MAX_BYTES,
                backupCount=_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError:
            pass
        log_event("INFO", "logger", "log_cleared")
        return True
    except Exception:
        return False


def open_log_dir_in_explorer() -> bool:
    """Open the log directory in the OS file browser. Best-effort."""
    folder = _ensure_log_dir()
    try:
        if os.name == "nt":
            os.startfile(str(folder))  # type: ignore[attr-defined]
            return True
        import subprocess
        import sys

        if sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])
        return True
    except Exception:
        return False
