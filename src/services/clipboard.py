"""Synchronous OS-level clipboard helper.

Why a custom helper instead of ``ft.Clipboard``?

In Flet 0.84 the built-in ``Clipboard`` is a ``Service`` control that
needs to be mounted on the page and goes through the Python<->Flutter
session for every call. In practice that is fragile:

* Each ``await clipboard.set(...)`` becomes ``page.session.invoke_method``
  - the session can be in a half-closed state after a navigation /
  dialog dismiss and the call dies with ``RuntimeError("Session
  closed")``. Users see the Copy button doing nothing while
  ``settings.view -> logs_copy_failed`` lines pile up in the debug log.
* Creating a fresh ``ft.Clipboard()`` per click and registering it via
  ``page._services.register_service(...)`` does not actually fix the
  race - the registered service still binds to the same session that
  is closed.
* The async coroutine has to be scheduled with ``page.run_task``. From
  background pipeline threads (where many of our copy buttons live)
  there is no event loop, so we end up bouncing through callbacks and
  losing error context.

A direct OS clipboard call sidesteps all of this. We try, in order:

1. ``pyperclip`` - bundled in ``requirements.txt``, lazy-imported so
  importing this module never fails. Works on Windows / macOS /
  Linux (with ``xclip``/``wl-copy``).
2. Platform-specific fallbacks (``win32clipboard`` from ``pywin32``
  on Windows, ``pbcopy`` on macOS, ``xclip``/``xsel`` on Linux). All
  optional - if none exist we fall back to the shipped Flet
  service so the worst case is "behaves like before".

Public API is intentionally minimal:

* :func:`copy(text)` - returns ``True`` on success, ``False`` otherwise.
  Never raises - all errors are logged through
  :mod:`src.services.logger` so failures still show up in
  Settings -> Debug logs.
* :func:`paste()` - returns the clipboard text (or ``""``). Never
  raises.
* :func:`available()` - returns ``True`` when at least one backend is
  ready. Lets the UI dim/disable buttons that wouldn't work.

Both helpers are safe to call from any thread.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from typing import Optional

from src.services import logger as logger_service


_LOG_AREA = "clipboard"


# ---------------------------------------------------------------------------
# Backend probing
# ---------------------------------------------------------------------------

# We probe the available backends lazily and cache the result. Probing
# is cheap (just a couple of import attempts) but we don't want to log
# the same "pyperclip not installed" warning on every keystroke.

_PROBE_LOCK = threading.Lock()
_PROBE_DONE = False
_BACKEND: str = "none"


def _probe_pyperclip() -> bool:
    try:
        import pyperclip  # type: ignore[import-not-found]
    except ImportError:
        return False
    # pyperclip lazily picks a backend on first call; ``determine_clipboard``
    # is the safest way to verify a real backend is reachable. On Windows
    # it returns the win32 backend if pywin32 is installed, otherwise it
    # uses the cmd.exe ``clip`` shell command. Both are fine for us.
    try:
        copy_fn, _paste_fn = pyperclip.determine_clipboard()
        if copy_fn is None:
            return False
    except Exception:
        return False
    return True


def _probe_win32() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import win32clipboard  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        return False
    return True


def _probe_macos() -> bool:
    if sys.platform != "darwin":
        return False
    return shutil.which("pbcopy") is not None and shutil.which("pbpaste") is not None


def _probe_linux() -> bool:
    if sys.platform.startswith("linux"):
        for tool in ("wl-copy", "xclip", "xsel"):
            if shutil.which(tool):
                return True
    return False


def _probe_tk() -> bool:
    try:
        import tkinter  # noqa: F401
    except ImportError:
        return False
    return True


def _select_backend() -> str:
    """Pick the first backend whose probe succeeds.

    Order is chosen so the most reliable / least intrusive backend wins:

    1. ``pyperclip`` - cross-platform, no UI side effects.
    2. ``win32`` - direct ``win32clipboard`` calls (faster than spawning
      ``clip.exe``, no console window flash).
    3. ``macos`` / ``linux`` - subprocess to ``pbcopy`` / ``xclip`` /
      ``wl-copy`` / ``xsel``.
    4. ``tk`` - last-resort using ``tkinter`` (creates a hidden root
      window for one tick).
    """
    if _probe_pyperclip():
        return "pyperclip"
    if _probe_win32():
        return "win32"
    if _probe_macos():
        return "macos"
    if _probe_linux():
        return "linux"
    if _probe_tk():
        return "tk"
    return "none"


def _ensure_probed() -> str:
    global _PROBE_DONE, _BACKEND
    if _PROBE_DONE:
        return _BACKEND
    with _PROBE_LOCK:
        if _PROBE_DONE:
            return _BACKEND
        _BACKEND = _select_backend()
        _PROBE_DONE = True
        logger_service.log_event(
            "INFO", _LOG_AREA, "backend_selected", backend=_BACKEND, platform=sys.platform,
        )
        return _BACKEND


# ---------------------------------------------------------------------------
# Backend-specific copy / paste implementations
# ---------------------------------------------------------------------------


def _copy_pyperclip(text: str) -> None:
    import pyperclip  # type: ignore[import-not-found]

    pyperclip.copy(text)


def _paste_pyperclip() -> str:
    import pyperclip  # type: ignore[import-not-found]

    return pyperclip.paste() or ""


def _copy_win32(text: str) -> None:
    import win32clipboard  # type: ignore[import-not-found]
    import win32con  # type: ignore[import-not-found]

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    finally:
        win32clipboard.CloseClipboard()


def _paste_win32() -> str:
    import win32clipboard  # type: ignore[import-not-found]
    import win32con  # type: ignore[import-not-found]

    win32clipboard.OpenClipboard()
    try:
        if not win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            return ""
        data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()
    return data or ""


def _copy_macos(text: str) -> None:
    proc = subprocess.Popen(
        ["pbcopy"],
        stdin=subprocess.PIPE,
        env={**os.environ, "LANG": "en_US.UTF-8"},
    )
    proc.communicate(text.encode("utf-8"))


def _paste_macos() -> str:
    proc = subprocess.run(
        ["pbpaste"],
        capture_output=True,
        env={**os.environ, "LANG": "en_US.UTF-8"},
        check=False,
    )
    return (proc.stdout or b"").decode("utf-8", errors="replace")


def _copy_linux(text: str) -> None:
    if shutil.which("wl-copy"):
        cmd = ["wl-copy"]
    elif shutil.which("xclip"):
        cmd = ["xclip", "-selection", "clipboard"]
    else:
        cmd = ["xsel", "--clipboard", "--input"]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    proc.communicate(text.encode("utf-8"))


def _paste_linux() -> str:
    if shutil.which("wl-paste"):
        cmd = ["wl-paste"]
    elif shutil.which("xclip"):
        cmd = ["xclip", "-selection", "clipboard", "-o"]
    else:
        cmd = ["xsel", "--clipboard", "--output"]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    return (proc.stdout or b"").decode("utf-8", errors="replace")


def _copy_tk(text: str) -> None:
    import tkinter

    root = tkinter.Tk()
    try:
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        # ``update`` flushes the X / Win32 event queue so the clipboard
        # actually receives the data before we destroy the toplevel.
        root.update()
    finally:
        root.destroy()


def _paste_tk() -> str:
    import tkinter

    root = tkinter.Tk()
    try:
        root.withdraw()
        try:
            return root.clipboard_get()
        except tkinter.TclError:
            return ""
    finally:
        root.destroy()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def available() -> bool:
    """Return ``True`` when at least one OS-level backend is reachable."""
    return _ensure_probed() != "none"


def backend_name() -> str:
    """Return the backend identifier (``pyperclip`` / ``win32`` / ...)."""
    return _ensure_probed()


def copy(text: Optional[str]) -> bool:
    """Copy ``text`` to the OS clipboard.

    Returns ``True`` on success, ``False`` on failure (and logs the
    error via :func:`logger.log_exception` so the user can see what went
    wrong in Settings -> Debug logs).

    ``None`` is treated as the empty string so callers don't have to
    pre-coalesce.
    """
    payload = "" if text is None else str(text)
    backend = _ensure_probed()
    if backend == "none":
        logger_service.log_event(
            "WARNING", _LOG_AREA, "copy_no_backend", chars=len(payload),
        )
        return False
    try:
        if backend == "pyperclip":
            _copy_pyperclip(payload)
        elif backend == "win32":
            _copy_win32(payload)
        elif backend == "macos":
            _copy_macos(payload)
        elif backend == "linux":
            _copy_linux(payload)
        elif backend == "tk":
            _copy_tk(payload)
        else:
            return False
    except Exception as exc:
        logger_service.log_exception(
            _LOG_AREA, "copy_failed", exc, backend=backend, chars=len(payload),
        )
        return False
    logger_service.log_event(
        "INFO", _LOG_AREA, "copy_ok", backend=backend, chars=len(payload),
    )
    return True


def paste() -> str:
    """Return the current OS clipboard text (or ``""`` on any failure)."""
    backend = _ensure_probed()
    if backend == "none":
        logger_service.log_event(
            "WARNING", _LOG_AREA, "paste_no_backend",
        )
        return ""
    try:
        if backend == "pyperclip":
            text = _paste_pyperclip()
        elif backend == "win32":
            text = _paste_win32()
        elif backend == "macos":
            text = _paste_macos()
        elif backend == "linux":
            text = _paste_linux()
        elif backend == "tk":
            text = _paste_tk()
        else:
            return ""
    except Exception as exc:
        logger_service.log_exception(
            _LOG_AREA, "paste_failed", exc, backend=backend,
        )
        return ""
    logger_service.log_event(
        "DEBUG", _LOG_AREA, "paste_ok", backend=backend, chars=len(text or ""),
    )
    return text or ""


__all__ = [
    "available",
    "backend_name",
    "copy",
    "paste",
]
