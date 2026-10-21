"""Settings layout uses one surface and scrolls only when content overflows."""

import os
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from types import SimpleNamespace

import pytest

from certificate_analyzer.infrastructure.config.settings import Settings
from certificate_analyzer.presentation.gui.styles import CARD_BG_COLOR, configure_gui_styles
from certificate_analyzer.presentation.gui.views.settings_view import SettingsDialog
from certificate_analyzer.presentation.gui.widgets.scrollable_panel import ScrollablePanel

pytestmark = pytest.mark.skipif(
    os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST") != "1", reason="Desktop session required"
)


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


@pytest.fixture(scope="module")
def settings_runtime():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.mark.parametrize("scale", [96 / 72, 144 / 72])
def test_settings_surface_and_scrollbar_follow_content(settings_runtime, scale):
    root = tk.Toplevel(settings_runtime)
    root.geometry("300x200+20+20")
    root.tk.call("tk", "scaling", scale)
    configure_gui_styles(root)
    application = SimpleNamespace(
        settings=Settings(folders={f"Папка {i}": "C:/Certificates" for i in range(12)}),
        certificates=SimpleNamespace(storage=SimpleNamespace(folder=Path("C:/Certificates"))),
        database=SimpleNamespace(path=Path("C:/Certificates/data.db")),
    )
    dialog = SettingsDialog(root, application)
    style = ttk.Style(root)
    try:
        dialog.geometry("760x420")
        dialog.notebook.select(2)
        root.update()
        panel = next(item for item in descendants(dialog.nametowidget(dialog.notebook.select()))
                     if isinstance(item, ScrollablePanel))
        scrollbar = next(item for item in panel.winfo_children() if isinstance(item, ttk.Scrollbar))
        assert bool(scrollbar.winfo_ismapped()) == (panel.body.winfo_height() > panel.canvas.winfo_height())
        if scale == 96 / 72:
            assert not scrollbar.winfo_ismapped(), "Short certificate tab must not show a scrollbar"
        for label in (item for item in descendants(panel.body) if isinstance(item, ttk.Label)):
            assert style.lookup(label.cget("style") or "TLabel", "background") == CARD_BG_COLOR
            assert label.winfo_width() <= panel.body.winfo_width()
        spinbox = next(item for item in descendants(panel.body) if isinstance(item, ttk.Spinbox))
        assert spinbox.winfo_height() >= 28
        dialog.notebook.select(1)
        root.update()
        panel = next(item for item in descendants(dialog.nametowidget(dialog.notebook.select()))
                     if isinstance(item, ScrollablePanel))
        scrollbar = next(item for item in panel.winfo_children() if isinstance(item, ttk.Scrollbar))
        assert scrollbar.winfo_ismapped(), "Long folder lists must remain scrollable"
        panel.canvas.yview_moveto(1)
        root.update()
        assert panel.canvas.yview()[1] == pytest.approx(1)
        for button in (item for item in descendants(dialog)
                       if isinstance(item, ttk.Button) and item.cget("text") in ("Сохранить", "Отмена")):
            assert button.winfo_ismapped()
            assert button.winfo_rooty() + button.winfo_height() <= dialog.winfo_rooty() + dialog.winfo_height()
    finally:
        dialog.destroy()
        root.destroy()
