import tkinter as tk
from tkinter import ttk

from certificate_analyzer.presentation.gui.styles import (
    MONO_FONT,
    UI_FONT,
)
from certificate_analyzer.presentation.gui.widgets.scrollable_panel import ScrollablePanel


class CertificateDetails(ttk.LabelFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            text=" Свойства сертификата ",
            padding=10,
            style="Panel.TLabelframe",
            **kwargs,
        )

        self.scroll_panel = ScrollablePanel(self)
        self.scroll_panel.pack(fill="both", expand=True)
        body = self.scroll_panel.body
        self.fields = {
            "Subject": ttk.Label(
                body,
                font=(UI_FONT, 10),
                wraplength=240,
                style="Panel.TLabel",
            ),
            "Issuer": ttk.Label(
                body,
                font=(UI_FONT, 10),
                wraplength=240,
                style="Panel.TLabel",
            ),
            "Serial": ttk.Label(
                body, font=(MONO_FONT, 9), wraplength=240, style="Panel.TLabel"
            ),
            "Email": ttk.Label(body, font=(UI_FONT, 10), style="Panel.TLabel"),
            "SHA-256": ttk.Label(body, font=(MONO_FONT, 9), style="Panel.TLabel"),
            "Путь": ttk.Label(body, font=(UI_FONT, 9), style="Panel.TLabel"),
        }

        labels = {
            "Subject": "Владелец",
            "Issuer": "Издатель",
            "Serial": "Серийный номер",
            "Email": "Email",
            "SHA-256": "Отпечаток SHA-256",
            "Путь": "Расположение файла",
        }
        self.field_labels = labels
        self.row_widgets = {}
        self.selected_field = None
        ttk.Style(self).configure("Selected.Card.TLabel", background="#DCEAFF", foreground="#183153")
        self.copy_menu = tk.Menu(self, tearoff=0)
        self.copy_menu.add_command(label="Копировать значение")
        self.copy_menu.add_command(label="Копировать строку")
        self.copy_menu.add_separator()
        self.copy_menu.add_command(label="Копировать карточку", command=self.copy_card)
        body.columnconfigure(0, weight=1)

        for row, (label_text, widget) in enumerate(self.fields.items()):
            widget.configure(takefocus=True)
            widget.bind("<FocusIn>", lambda event, key=label_text: self.select_field(key))
            widget.bind("<Control-c>", lambda event, key=label_text: self.copy_field(key) or "break")
            title = ttk.Label(
                body,
                text=f"{labels[label_text]}:",
                font=(UI_FONT, 9, "bold"),
                style="Panel.TLabel",
            )
            title.grid(row=row * 2, column=0, sticky="w", pady=(10 if row else 0, 2))
            widget.grid(row=row * 2 + 1, column=0, sticky="ew")
            self.row_widgets[label_text] = (title, widget)
            for target in (title, widget):
                target.bind("<Button-1>", lambda event, key=label_text: self.select_field(key))
                target.bind("<Button-3>", lambda event, key=label_text: self._show_copy_menu(event, key))
            widget.bind("<Double-Button-1>", lambda event, key=label_text: self.copy_field(key))
        body.bind("<Configure>", self._resize_values, add="+")
        self.scroll_panel.bind_mousewheel()

    def select_field(self, key):
        if self.selected_field is not None:
            for widget in self.row_widgets[self.selected_field]:
                widget.configure(style="Panel.TLabel")
        self.selected_field = key
        if key is not None:
            for widget in self.row_widgets[key]:
                widget.configure(style="Selected.Card.TLabel")

    def _copy_text(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)

    def copy_field(self, key, *, include_label=False):
        value = str(self.fields[key].cget("text"))
        self._copy_text(f"{self.field_labels[key]}: {value}" if include_label else value)

    def copy_card(self):
        self._copy_text("\n".join(f"{self.field_labels[key]}: {widget.cget('text')}" for key, widget in self.fields.items()))

    def _show_copy_menu(self, event, key):
        self.select_field(key)
        self.copy_menu.entryconfigure(0, command=lambda: self.copy_field(key))
        self.copy_menu.entryconfigure(1, command=lambda: self.copy_field(key, include_label=True))
        try:
            self.copy_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.copy_menu.grab_release()

    def _resize_values(self, event):
        """Подстраивает перенос длинных значений под ширину панели."""
        wraplength = max(60, event.width - 8)
        for widget in self.fields.values():
            widget.config(wraplength=wraplength)

    def update_details(self, details: dict):
        for key, widget in self.fields.items():
            value = details.get(key, "—")
            widget.config(text=value)

    def clear(self):
        self.select_field(None)
        for widget in self.fields.values():
            widget.config(text="—")
