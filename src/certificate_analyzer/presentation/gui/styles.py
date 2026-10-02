import sys
from tkinter import ttk


BG_COLOR = "#F5F7FA"
UI_FONT = "Segoe UI" if sys.platform == "win32" else "Noto Sans"
MONO_FONT = "Consolas" if sys.platform == "win32" else "DejaVu Sans Mono"
HEADER_COLOR = "#FFFFFF"
TEXT_COLOR = "#263238"
SECONDARY_TEXT_COLOR = "#78909C"
ACCENT_COLOR = "#6C5CE7"
BUTTON_COLOR = "#6C5CE7"
BUTTON_HOVER = "#5B4BC4"
DANGER_COLOR = "#D9534F"
SUCCESS_COLOR = "#2E7D32"

EXPIRED_COLOR = "#D9534F"
WARNING_COLOR = "#F9A825"
NORMAL_COLOR = "#2E7D32"

EXPIRED_TEXT = "#FFFFFF"
WARNING_TEXT = TEXT_COLOR
NORMAL_TEXT = "#FFFFFF"

GRAPH_EXPIRED = "#D9534F"
GRAPH_WARNING = "#F9A825"
GRAPH_NORMAL = "#2E7D32"

SIDEBAR_COLOR = "#26384A"
SIDEBAR_TEXT_COLOR = "#F5F7FA"

CARD_BG_COLOR = "#FFFFFF"
CARD_BORDER_COLOR = "#E1E8ED"
CARD_TITLE_COLOR = "#78909C"
CARD_VALUE_COLOR = "#263238"

MCHD_COLOR = "#9B59B6"
MCHD_LIGHT_COLOR = "#F3E5F5"

CAL_EXPIRED_BG = "#D9534F"
CAL_EXPIRED_FG = "#FFFFFF"
CAL_WARNING_BG = "#F9A825"
CAL_WARNING_FG = "#263238"
CAL_NORMAL_BG = "#2E7D32"
CAL_NORMAL_FG = "#FFFFFF"
CAL_TODAY_BG = "#6C5CE7"
CAL_TODAY_FG = "#FFFFFF"


def configure_gui_styles(root) -> None:
    """Настраивает единый внешний вид основных панелей приложения."""
    style = ttk.Style(root)
    root.configure(background=BG_COLOR)

    # Не подменяем системную тему: вкладки и остальные стандартные элементы
    # должны выглядеть привычно для текущей операционной системы.
    style.configure(".", font=(UI_FONT, 10), foreground=TEXT_COLOR)
    style.configure("App.TFrame", background=BG_COLOR)
    style.configure("TNotebook", background=BG_COLOR, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        font=(UI_FONT, 10),
        padding=(14, 8),
    )
    style.configure(
        "Treeview",
        rowheight=30,
        background=CARD_BG_COLOR,
        fieldbackground=CARD_BG_COLOR,
        borderwidth=0,
    )
    style.map(
        "Treeview",
        background=[("selected", "#DCE8FF")],
        foreground=[("selected", TEXT_COLOR)],
    )
    style.configure(
        "Treeview.Heading",
        font=(UI_FONT, 10, "bold"),
        padding=(8, 7),
    )

    style.configure(
        "Panel.TFrame",
        background=CARD_BG_COLOR,
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "Panel.TLabel", background=CARD_BG_COLOR, foreground=TEXT_COLOR
    )
    style.configure("Panel.TLabelframe", background=CARD_BG_COLOR)
    style.configure(
        "Panel.TLabelframe.Label",
        background=CARD_BG_COLOR,
        foreground=TEXT_COLOR,
    )
    style.configure("Status.TFrame", background=CARD_BG_COLOR)
    style.configure(
        "Status.TLabel", background=CARD_BG_COLOR, foreground=TEXT_COLOR
    )
    style.configure(
        "Summary.TLabel",
        background=BG_COLOR,
        foreground=TEXT_COLOR,
        font=(UI_FONT, 10, "bold"),
        padding=(2, 4),
    )
    style.configure(
        "Muted.TLabel",
        background=BG_COLOR,
        foreground=SECONDARY_TEXT_COLOR,
        font=(UI_FONT, 9),
    )
    style.configure("Toolbar.TButton", padding=(10, 6))
    style.configure(
        "Accent.TButton",
        padding=(12, 6),
        font=(UI_FONT, 10, "bold"),
    )
