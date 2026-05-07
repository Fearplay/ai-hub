"""Drop zone for the AI Legal section.

Real OS drag-and-drop is provided by the community ``flet-dropzone``
extension which wraps the Flutter ``desktop_drop`` package. The Python
side ships with the app (``flet-dropzone`` is in ``requirements.txt``)
but the native bridge only fires ``on_dropped`` once the user has run
``flet build windows`` (or ``macos`` / ``linux``) at least once - see
the README. To keep the app friendly even *before* that build, we wrap
the same visual zone in a click handler that opens ``ft.FilePicker``,
so users who haven't built yet can still attach a PDF the conventional
way. Behaviour is identical from ``STATE.uploaded_file``'s point of
view.
"""

from __future__ import annotations

import os
from typing import Callable, Optional

import flet as ft

from src.sections.ai_legal.strings import s
from src.theme import Theme


try:
    import flet_dropzone as ftd  # type: ignore[import-not-found]
    _DROPZONE_AVAILABLE = True
except Exception:  # pragma: no cover - extension import is best-effort
    ftd = None  # type: ignore[assignment]
    _DROPZONE_AVAILABLE = False


def _format_size(num_bytes: int) -> str:
    if num_bytes >= 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    if num_bytes >= 1024:
        return f"{num_bytes / 1024:.0f} kB"
    return f"{num_bytes} B"


def _path_to_file_dict(path: str) -> Optional[dict]:
    if not path:
        return None
    name = os.path.basename(path) or path
    ext = os.path.splitext(name)[1].lower().lstrip(".")
    if ext != "pdf":
        return None
    try:
        size = _format_size(os.path.getsize(path))
    except OSError:
        size = "?"
    return {"name": name, "type": "PDF", "size": size}


def _picker_to_file_dict(file: ft.FilePickerFile) -> Optional[dict]:
    if file.path:
        result = _path_to_file_dict(file.path)
        if result is not None:
            return result
    name = file.name or ""
    if not name.lower().endswith(".pdf"):
        return None
    size_str = _format_size(file.size) if isinstance(file.size, int) else "?"
    return {"name": name, "type": "PDF", "size": size_str}


def _idle_bg(theme: Theme) -> str:
    return ft.Colors.with_opacity(0.10, theme.primary)


def _idle_border(theme: Theme) -> ft.Border:
    return ft.border.all(2, ft.Colors.with_opacity(0.30, theme.primary))


def _active_bg(theme: Theme) -> str:
    return ft.Colors.with_opacity(0.22, theme.primary)


def _active_border(theme: Theme) -> ft.Border:
    return ft.border.all(2, ft.Colors.with_opacity(0.65, theme.primary))


def drop_zone(
    theme: Theme,
    lang: str,
    *,
    on_file_resolved: Callable[[dict], None],
    height: int = 132,
) -> ft.Control:
    txt = s(lang)
    file_picker = ft.FilePicker()
    picker_registered: dict[str, bool] = {"done": False}

    inner_ref = ft.Ref[ft.Container]()
    error_ref = ft.Ref[ft.Text]()

    def _set_active(active: bool) -> None:
        c = inner_ref.current
        if c is None:
            return
        c.bgcolor = _active_bg(theme) if active else _idle_bg(theme)
        c.border = _active_border(theme) if active else _idle_border(theme)
        try:
            c.update()
        except AssertionError:
            pass

    def _show_error(message: Optional[str]) -> None:
        e = error_ref.current
        if e is None:
            return
        e.value = message or ""
        e.visible = bool(message)
        try:
            e.update()
        except AssertionError:
            pass

    def _resolve_and_emit(resolved: Optional[dict]) -> None:
        if resolved is None:
            _show_error(txt["drop_zone_only_pdf"])
            return
        _show_error(None)
        on_file_resolved(resolved)

    async def _open_picker(e: ft.ControlEvent) -> None:
        page = e.page
        if page is None:
            return
        if not picker_registered["done"]:
            registry = getattr(page, "_services", None)
            if registry is not None:
                try:
                    registry.register_service(file_picker)
                except Exception:
                    pass
            picker_registered["done"] = True
        try:
            files = await file_picker.pick_files(
                dialog_title=txt["drop_zone_title"],
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["pdf"],
            )
        except Exception:
            files = []
        if not files:
            return
        _resolve_and_emit(_picker_to_file_dict(files[0]))

    def _on_dropped(event) -> None:
        _set_active(False)
        files = getattr(event, "files", None) or []
        if not files:
            return
        first = files[0]
        path = first if isinstance(first, str) else getattr(first, "path", "")
        _resolve_and_emit(_path_to_file_dict(path))

    icon = ft.Icon(ft.Icons.CLOUD_UPLOAD_OUTLINED, color=theme.primary, size=28)
    title = ft.Text(
        txt["drop_zone_title"],
        color=theme.text,
        size=13,
        weight=ft.FontWeight.W_600,
    )
    hint = ft.Text(txt["drop_zone_hint"], color=theme.text_muted, size=11)
    error = ft.Text(
        ref=error_ref,
        value="",
        color="#EF4444",
        size=11,
        weight=ft.FontWeight.W_500,
        visible=False,
    )

    inner = ft.Container(
        ref=inner_ref,
        content=ft.Column(
            controls=[icon, title, hint, error],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        padding=14,
        bgcolor=_idle_bg(theme),
        border=_idle_border(theme),
        border_radius=12,
        alignment=ft.Alignment.CENTER,
        height=height,
        ink=True,
        on_click=_open_picker,
    )

    if _DROPZONE_AVAILABLE and ftd is not None:
        return ftd.Dropzone(
            content=inner,
            allowed_file_types=["pdf"],
            on_dropped=_on_dropped,
            on_entered=lambda e: _set_active(True),
            on_exited=lambda e: _set_active(False),
        )
    return inner
