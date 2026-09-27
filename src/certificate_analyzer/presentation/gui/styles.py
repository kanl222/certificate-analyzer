from tkinter import ttk


BG_COLOR = "#F5F7FA"
UI_FONT = "Noto Sans"
MONO_FONT = "DejaVu Sans Mono"
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
WARNING_TEXT = "#FFFFFF"
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
    style.theme_use("clam")

    style.configure(
        ".", font=(UI_FONT, 10), background=BG_COLOR, foreground=TEXT_COLOR
    )
    style.configure("TNotebook", background=BG_COLOR, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        font=(UI_FONT, 10, "bold"),
        padding=(14, 8),
    )
    style.configure(
        "Treeview",
        rowheight=30,
        background=CARD_BG_COLOR,
        fieldbackground=CARD_BG_COLOR,
    )
    style.configure("Treeview.Heading", font=(UI_FONT, 10, "bold"))

    style.configure("Panel.TFrame", background=CARD_BG_COLOR)
    style.configure(
        "Panel.TLabel", background=CARD_BG_COLOR, foreground=TEXT_COLOR
    )
    style.configure("Toolbar.TButton", padding=(10, 6))
    style.configure(
        "Accent.TButton",
        background=ACCENT_COLOR,
        foreground="white",
        padding=(12, 6),
    )
    style.map(
        "Accent.TButton",
        background=[("active", BUTTON_HOVER), ("pressed", BUTTON_HOVER)],
        foreground=[("disabled", SECONDARY_TEXT_COLOR)],
    )
