import tkinter as tk
from tkinter import ttk

from certificate_analyzer.presentation.gui.styles import (
    MONO_FONT,
    UI_FONT,
)


class CertificateDetails(ttk.LabelFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, text=" Детали выбранного сертификата ", padding=10, **kwargs)
        
        self.fields = {
            "Subject": ttk.Label(self, font=(MONO_FONT, 9), wraplength=400),
            "Issuer": ttk.Label(self, font=(MONO_FONT, 9), wraplength=400),
            "Serial": ttk.Label(self, font=(MONO_FONT, 9)),
            "SHA-256": ttk.Label(self, font=(MONO_FONT, 9)),
            "Путь": ttk.Label(self, font=(UI_FONT, 9), wraplength=400),
            "Email": ttk.Label(self, font=(UI_FONT, 9)),
            "МЧД": ttk.Label(self, font=(UI_FONT, 9))
        }

        for row, (label_text, widget) in enumerate(self.fields.items()):
            ttk.Label(self, text=f"{label_text}:", font=(UI_FONT, 9, "bold")).grid(row=row, column=0, sticky=tk.W, pady=2, padx=(0, 10))
            widget.grid(row=row, column=1, sticky=tk.W, pady=2)

    def update_details(self, details: dict):
        for key, widget in self.fields.items():
            value = details.get(key, "—")
            widget.config(text=value)

    def clear(self):
        for widget in self.fields.values():
            widget.config(text="—")
