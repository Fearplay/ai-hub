"""Click-to-browse drop zone for the AI Legal section.

We intentionally do **not** use ``flet-dropzone`` here. That package needs
the Flutter ``desktop_drop`` native plugin which is bundled by
``flet build windows`` but **not** by ``flet pack`` (PyInstaller). Our
distribution flow is ``flet pack``, so the native bridge would never be
present at runtime - rendering the dropzone control would surface as the
red "Unknown control: flet_dropzone" banner. We side-step the whole
problem by giving the visual zone a click handler that opens
``ft.FilePicker`` instead - the user attaches a PDF the conventional
way and ``STATE.uploaded_file`` ends up with the same shape it would
have had via OS drag-drop.
"""

from __future__ import annotations

import os
from typing import Callable, Optional

import flet as ft

from src.sections.ai_legal.strings import s
from src.theme import Theme


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

    return ft.Container(
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
