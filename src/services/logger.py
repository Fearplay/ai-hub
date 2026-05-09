"""Process-wide debug log used by the in-app Settings -> Logs viewer.

Why a custom helper instead of a bare ``logging.getLogger("aihub")``?

1. The user wants a single file they can open / copy / clear from the
   Settings UI, so we control the file path + rotation policy here
   instead of letting every caller configure handlers ad-hoc.
2. We want the lines to be skim-friendly without forcing every caller
   to pre-format the prefix. The custom format puts each piece in its
   own column so eyeballing 1k+ lines for "what crashed" is fast.
3. Most call sites use :func:`log_exception` instead of bare
   ``except: pass``; the helper keeps the ``except`` block silent for
   the user but writes a real traceback to disk so we can debug after
   the fact.

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

Format::

    2026-05-09 19:47:11.123 | INFO  | ai_career.pipeline   | activity_change       | prev=ready new=analyzing

The five columns are ``timestamp | level | area | event | data``. Area
is right-padded to 22 chars and event to 26 chars so adjacent rows line
up. Levels are colour-coded on the stream handler when possible (TTY +
``colorama`` not required - we only use ANSI codes that Windows 10+
PowerShell renders natively).

Helpers:

* :func:`log_event` - one INFO/DEBUG/ERROR/... line. Pass ``**kwargs``
  for the data payload; values are formatted via ``repr`` when they
  contain whitespace so ``message="hello world"`` round-trips.
* :func:`log_exception` - ERROR line + full traceback. Use from every
  ``except`` block instead of ``pass`` so the failure shows up in
  Settings -> Debug logs.
* :func:`log_state` - thin alias around :func:`log_event` with the
  intent "this is a snapshot of state X" (used by sections after
  mode / tab / palette changes so the log reads as a state machine).
* :func:`timed_call` - decorator that wraps a function with a
  ``*_start`` / ``*_done`` pair and reports ``elapsed_ms``. Use for
  AI calls and other long-running pipeline steps so the log doubles
  as a coarse profiler.
* :func:`try_update` - safe ``control.update()`` wrapper for sections.
"""

from __future__ import annotations

import functools
import logging
import os
import sys
import threading
import time
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, TypeVar


_LOGGER_NAME = "aihub"
_MAX_BYTES = 1 * 1024 * 1024  # 1 MB per file
_BACKUP_COUNT = 3

_INIT_LOCK = threading.Lock()
_INITIALIZED = False

# Column widths chosen so 95% of real area / event names fit. Anything
# longer pushes the right column out by a couple of chars - that is the
# correct trade-off vs. truncating identifiers we use to grep for bugs.
_AREA_WIDTH = 22
_EVENT_WIDTH = 26


_LEVEL_ANSI: dict[str, str] = {
    "DEBUG": "\x1b[36m",   # cyan
    "INFO": "\x1b[32m",    # green
    "WARNING": "\x1b[33m", # yellow
    "ERROR": "\x1b[31m",   # red
    "CRITICAL": "\x1b[1;31m",  # bold red
}
_ANSI_RESET = "\x1b[0m"


def log_dir() -> Path:
    return Path.home() / "AI Hub" / "logs"


def log_path() -> Path:
    return log_dir() / "app.log"


def _ensure_log_dir() -> Path:
    folder = log_dir()
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Disk is read-only or the parent directory cannot be created.
        # The stream handler still gives us console output so this is
        # not fatal - just leaves the file logger silent on this run.
        pass
    return folder


class _AlignedFormatter(logging.Formatter):
    """Custom formatter that lays out the message in fixed columns.

    Each :func:`log_event` call writes a record whose ``msg`` is the
    pre-formatted ``"area|event|payload"`` triplet. This formatter
    splits that triplet, pads area + event to fixed widths, and joins
    everything with ``" | "`` separators. Records that did not come
    through :func:`log_event` (e.g. raw ``logger.error("...")`` calls)
    pass through unchanged so we don't break Python's default logger
    behaviour for third-party libraries.
    """

    def __init__(self, *, use_colour: bool) -> None:
        super().__init__(
            fmt="%(asctime)s.%(msecs)03d | %(levelname)-5s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self._use_colour = use_colour

    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        if msg.startswith("\0aihub|"):
            # Triple sent by log_event (see the sentinel in _emit). The
            # marker keeps us from accidentally re-formatting random
            # third-party records that happen to contain pipes.
            try:
                _, area, event, payload = msg.split("|", 3)
            except ValueError:
                area = ""
                event = ""
                payload = msg
            area_col = (area or "")[:_AREA_WIDTH].ljust(_AREA_WIDTH)
            event_col = (event or "")[:_EVENT_WIDTH].ljust(_EVENT_WIDTH)
            record.msg = f"{area_col} | {event_col} | {payload}"
            record.args = ()
        formatted = super().format(record)
        if self._use_colour:
            ansi = _LEVEL_ANSI.get(record.levelname)
            if ansi:
                return f"{ansi}{formatted}{_ANSI_RESET}"
        return formatted


def _stream_supports_colour(stream: Any) -> bool:
    """Return True when ANSI sequences won't show up as garbage."""
    if stream is None:
        return False
    if not hasattr(stream, "isatty"):
        return False
    try:
        if not stream.isatty():
            return False
    except Exception:
        return False
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return True


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
                # The handler is already broken; just drop it.
                pass

        _ensure_log_dir()

        plain_formatter = _AlignedFormatter(use_colour=False)

        try:
            file_handler = RotatingFileHandler(
                str(log_path()),
                maxBytes=_MAX_BYTES,
                backupCount=_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(plain_formatter)
            logger.addHandler(file_handler)
        except OSError:
            # Disk is read-only or the AI Hub folder cannot be created.
            # The stream handler below still gives us console output.
            pass

        try:
            stream = sys.stdout
            stream_handler = logging.StreamHandler(stream)
            stream_handler.setLevel(logging.INFO)
            stream_handler.setFormatter(
                _AlignedFormatter(use_colour=_stream_supports_colour(stream))
            )
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
        if isinstance(value, str) and (" " in value or "=" in value or "|" in value):
            text = repr(value)
        elif isinstance(value, (int, float, bool)) or value is None:
            text = str(value)
        elif isinstance(value, (list, tuple, dict, set)):
            text = repr(value)
        else:
            text = str(value)
        parts.append(f"{key}={text}")
    return " ".join(parts)


def _resolve_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    name = (level or "").strip().upper() or "INFO"
    return logging._nameToLevel.get(name, logging.INFO)  # type: ignore[attr-defined]


def _emit(level: str | int, area: str, event: str, payload: str) -> None:
    """Write a single sentinel-prefixed line through the logger.

    The ``\\0aihub|`` prefix is what :class:`_AlignedFormatter`
    recognises so it can break the message back into columns. We use a
    NUL byte so any third-party code that legitimately needs to log a
    string starting with ``aihub|`` doesn't get accidentally rewritten.
    """
    logger = _ensure_initialized()
    line = f"\0aihub|{area}|{event}|{payload}"
    try:
        logger.log(_resolve_level(level), line)
    except Exception:
        # Logging itself failed (very unusual; e.g. a UnicodeError on a
        # broken handler). We have no better channel to report this on,
        # so swallow rather than crash the caller.
        pass


def log_event(level: str | int, area: str, event: str, **kwargs: Any) -> None:
    """Write a single structured line to ``app.log``.

    Example::

        log_event("INFO", "ai_career.view", "mode_change", index=1, new_mode="form")

    becomes::

        2026-05-09 13:47:11.123 | INFO  | ai_career.view         | mode_change                | index=1 new_mode='form'
    """
    _emit(level, area, event, _format_kwargs(kwargs))


def log_state(area: str, event: str, **state: Any) -> None:
    """Convenience alias for ``log_event("INFO", area, event, **state)``.

    Used at "snapshot the world after a user action" call sites so the
    intent reads obviously in code: ``log_state("ai_career.view",
    "mode_changed", mode=STATE.mode, tab=STATE.active_tab)``.
    """
    _emit("INFO", area, event, _format_kwargs(state))


def log_exception(area: str, event: str, exc: BaseException, **kwargs: Any) -> None:
    """Write an ERROR line + the traceback for ``exc``.

    Use from any ``except`` block that previously did ``pass``: the user
    keeps seeing the same UI behaviour but we get a stack trace inside
    ``app.log`` to diagnose silent failures.
    """
    payload_kwargs = {"error": repr(exc), **kwargs}
    _emit("ERROR", area, event, _format_kwargs(payload_kwargs))
    try:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    except Exception:
        tb = ""
    if tb:
        # Indent so the traceback is visually distinct from the column
        # layout above. Use a separate emit so each line still goes
        # through the rotating handler atomically.
        _emit("ERROR", area, f"{event}.traceback", tb.rstrip())


F = TypeVar("F", bound=Callable[..., Any])


def timed_call(area: str, event: str) -> Callable[[F], F]:
    """Decorator: log ``*_start`` / ``*_done`` with elapsed milliseconds.

    Usage::

        @timed_call("ai_career.pipeline", "extract_candidate")
        def extract_candidate(*, output_lang: str) -> PipelineResult:
            ...

    On entry we emit ``extract_candidate_start``; on a successful exit
    we emit ``extract_candidate_done elapsed_ms=...``; on an exception
    we emit ``extract_candidate_failed elapsed_ms=... error=...`` (plus
    the usual traceback via :func:`log_exception`) and re-raise so the
    caller sees the original error.

    Designed for pipeline functions: short, side-effectful, infrequent.
    Do *not* decorate hot helpers - the per-call overhead is small but
    not free.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            log_event("INFO", area, f"{event}_start")
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                log_exception(
                    area,
                    f"{event}_failed",
                    exc,
                    elapsed_ms=elapsed_ms,
                )
                raise
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            log_event(
                "INFO", area, f"{event}_done", elapsed_ms=elapsed_ms,
            )
            return result

        return wrapper  # type: ignore[return-value]

    return decorator


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
                    # Handler is already broken; we'll replace it below.
                    pass
        try:
            path.write_text("", encoding="utf-8")
        except OSError:
            return False

        # Rebuild the rotating file handler so subsequent log calls
        # land in the freshly truncated file (the closed handler above
        # is no longer hooked, so we add a new one and remove the dead).
        new_handlers: list[logging.Handler] = []
        for handler in list(logger.handlers):
            if isinstance(handler, RotatingFileHandler):
                try:
                    logger.removeHandler(handler)
                except Exception:
                    # Already detached; nothing to do.
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
            file_handler.setFormatter(_AlignedFormatter(use_colour=False))
            logger.addHandler(file_handler)
        except OSError:
            pass
        log_event("INFO", "logger", "log_cleared")
        return True
    except Exception as exc:
        # Final safety net: if the truncation flow itself errors out,
        # at least try to leave a breadcrumb in the file we still have.
        log_exception("logger", "clear_log_failed", exc)
        return False


def open_log_dir_in_explorer() -> bool:
    """Open the log directory in the OS file browser. Best-effort."""
    folder = _ensure_log_dir()
    try:
        if os.name == "nt":
            os.startfile(str(folder))  # type: ignore[attr-defined]
            return True
        import subprocess

        if sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])
        return True
    except Exception as exc:
        log_exception("logger", "open_log_dir_failed", exc)
        return False


__all__ = [
    "log_dir",
    "log_path",
    "log_event",
    "log_state",
    "log_exception",
    "timed_call",
    "try_update",
    "read_log",
    "clear_log",
    "open_log_dir_in_explorer",
]
