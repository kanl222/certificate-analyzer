from types import SimpleNamespace
from unittest.mock import Mock
import os

import pytest


@pytest.mark.parametrize("keysym,keycode,virtual", [("Cyrillic_es", 67, "<<Copy>>"), ("Cyrillic_em", 86, "<<Paste>>"), ("Cyrillic_che", 88, "<<Cut>>"), ("c", 67, "<<Copy>>"), ("V", 86, "<<Paste>>"), ("??", 67, "<<Copy>>")])
def test_windows_shortcuts_ignore_keyboard_layout(keysym, keycode, virtual):
    from certificate_analyzer.presentation.gui.clipboard_shortcuts import handle_clipboard_shortcut
    widget = Mock()
    event = SimpleNamespace(widget=widget, state=4, keysym=keysym, keycode=keycode)
    assert handle_clipboard_shortcut(event, "win32") == "break"
    widget.event_generate.assert_called_once_with(virtual)


@pytest.mark.parametrize("state", [0, 4 | 8, 4 | 0x20000])
def test_typing_and_altgr_do_not_trigger_clipboard(state):
    from certificate_analyzer.presentation.gui.clipboard_shortcuts import handle_clipboard_shortcut
    widget = Mock()
    assert handle_clipboard_shortcut(SimpleNamespace(widget=widget, state=state, keysym="Cyrillic_es", keycode=67), "win32") is None
    widget.event_generate.assert_not_called()


def test_linux_uses_keysym_instead_of_windows_keycode():
    from certificate_analyzer.presentation.gui.clipboard_shortcuts import handle_clipboard_shortcut
    widget = Mock()
    event = SimpleNamespace(widget=widget, state=4, keysym="Cyrillic_em", keycode=55)
    assert handle_clipboard_shortcut(event, "x11") == "break"
    widget.event_generate.assert_called_once_with("<<Paste>>")


@pytest.mark.skipif(os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST") != "1", reason="Desktop clipboard test must be explicitly enabled")
def test_real_tk_copy_paste_cut_in_russian_layout():
    import sys
    from pathlib import Path
    import tkinter as tk
    from tkinter import ttk
    from certificate_analyzer.presentation.gui.clipboard_shortcuts import handle_clipboard_shortcut, install_clipboard_shortcuts

    tcl = Path(sys.base_prefix) / "tcl"
    if (tcl / "tcl8.6").is_dir():
        os.environ["TCL_LIBRARY"] = str(tcl / "tcl8.6")
        os.environ["TK_LIBRARY"] = str(tcl / "tk8.6")
    root = tk.Tk()
    root.withdraw()
    try:
        previous = root.clipboard_get()
    except tk.TclError:
        previous = None
    try:
        install_clipboard_shortcuts(root)
        widget = ttk.Entry(root)
        widget.insert(0, "Русский текст")
        widget.selection_range(0, "end")
        system = root.tk.call("tk", "windowingsystem")
        event = SimpleNamespace(widget=widget, state=4, keysym="Cyrillic_es", keycode=67)
        handle_clipboard_shortcut(event, system)
        assert root.clipboard_get() == "Русский текст"
        widget.delete(0, "end")
        event.keysym, event.keycode = "Cyrillic_em", 86
        handle_clipboard_shortcut(event, system)
        assert widget.get() == "Русский текст"
        widget.selection_range(0, "end")
        event.keysym, event.keycode = "Cyrillic_che", 88
        handle_clipboard_shortcut(event, system)
        assert widget.get() == ""
        assert root.clipboard_get() == "Русский текст"
    finally:
        root.clipboard_clear()
        if previous is not None:
            root.clipboard_append(previous)
        root.update()
        root.destroy()
