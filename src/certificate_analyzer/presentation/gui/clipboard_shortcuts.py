"""Clipboard shortcuts shared by all current and future Tk text widgets."""

import tkinter as tk

WINDOWS_KEYS = {67: "<<Copy>>", 86: "<<Paste>>", 88: "<<Cut>>", 65: "<<SelectAll>>"}
SYMBOLS = {
    "c": "<<Copy>>", "cyrillic_es": "<<Copy>>", "с": "<<Copy>>", "u0441": "<<Copy>>",
    "v": "<<Paste>>", "cyrillic_em": "<<Paste>>", "м": "<<Paste>>", "u043c": "<<Paste>>",
    "x": "<<Cut>>", "cyrillic_che": "<<Cut>>", "ч": "<<Cut>>", "u0447": "<<Cut>>",
    "a": "<<SelectAll>>", "cyrillic_ef": "<<SelectAll>>", "ф": "<<SelectAll>>", "u0444": "<<SelectAll>>",
}


def handle_clipboard_shortcut(event, windowing_system):
    state = getattr(event, "state", 0)
    # AltGr often arrives as Ctrl+Alt; it must remain ordinary text input.
    if not state & 4 or state & (8 | 0x20000):
        return None
    virtual = WINDOWS_KEYS.get(getattr(event, "keycode", None)) if windowing_system == "win32" else None
    virtual = virtual or SYMBOLS.get(str(getattr(event, "keysym", "")).lower())
    if virtual is None:
        return None
    widget = event.widget
    try:
        if virtual == "<<SelectAll>>":
            if widget.winfo_class() == "Text":
                widget.tag_add("sel", "1.0", "end-1c")
                widget.mark_set("insert", "end-1c")
            else:
                widget.selection_range(0, "end")
                widget.icursor("end")
        else:
            # Native virtual events preserve widget selection/state semantics.
            widget.event_generate(virtual)
    except tk.TclError:
        return "break"
    return "break"


def install_clipboard_shortcuts(root):
    """Class bindings also cover fields created later in settings/import dialogs.

    Tk's more specific built-in Latin key bindings take precedence over this
    generic fallback, so one key press cannot paste twice.
    """
    if getattr(root, "_clipboard_shortcuts_installed", False):
        return
    system = root.tk.call("tk", "windowingsystem")
    for widget_class in ("Entry", "TEntry", "Text", "TCombobox", "Spinbox", "TSpinbox"):
        root.bind_class(widget_class, "<Control-KeyPress>", lambda event, system=system: handle_clipboard_shortcut(event, system), add="+")
    root._clipboard_shortcuts_installed = True
