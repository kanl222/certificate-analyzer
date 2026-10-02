import tkinter as tk
from tkinter import ttk

from certificate_analyzer.presentation.gui.styles import (
    MONO_FONT,
    UI_FONT,
)


class CertificateDetails(ttk.LabelFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            text=" Детали выбранного сертификата ",
            padding=10,
            style="Panel.TLabelframe",
            **kwargs,
        )

        self.fields = {
            "Subject": ttk.Label(
                self,
                font=(MONO_FONT, 9),
                wraplength=240,
                style="Panel.TLabel",
            ),
            "Issuer": ttk.Label(
                self,
                font=(MONO_FONT, 9),
                wraplength=240,
                style="Panel.TLabel",
            ),
            "Serial": ttk.Label(
                self, font=(MONO_FONT, 9), wraplength=240, style="Panel.TLabel"
            ),
            "SHA-256": ttk.Label(
                self, font=(MONO_FONT, 9), wraplength=240, style="Panel.TLabel"
            ),
            "Путь": ttk.Label(
                self,
                font=(UI_FONT, 9),
                wraplength=240,
                style="Panel.TLabel",
            ),
            "Email": ttk.Label(self, font=(UI_FONT, 9), style="Panel.TLabel"),
            "МЧД": ttk.Label(self, font=(UI_FONT, 9), style="Panel.TLabel"),
        }

        labels = {
            "Subject": "Владелец",
            "Issuer": "Издатель",
            "Serial": "Серийный номер",
            "SHA-256": "SHA-256",
            "Путь": "Путь к файлу",
            "Email": "Email",
            "МЧД": "МЧД",
        }
        self.columnconfigure(1, weight=1)

        for row, (label_text, widget) in enumerate(self.fields.items()):
            ttk.Label(
                self,
                text=f"{labels[label_text]}:",
                font=(UI_FONT, 9, "bold"),
                style="Panel.TLabel",
            ).grid(row=row, column=0, sticky=tk.NW, pady=4, padx=(0, 10))
            widget.grid(row=row, column=1, sticky=tk.EW, pady=4)
        ttk.Label(self, text="Подлинность не проверена:\nподпись, доверие УЦ и отзыв", wraplength=240, style="Panel.TLabel").grid(row=len(self.fields), column=0, columnspan=2, sticky=tk.W, pady=8)
        self.bind("<Configure>", self._resize_values, add="+")

    def _resize_values(self, event):
        """Подстраивает перенос длинных значений под ширину панели."""
        wraplength = max(140, event.width - 150)
        for widget in self.fields.values():
            widget.config(wraplength=wraplength)

    def update_details(self, details: dict):
        for key, widget in self.fields.items():
            value = details.get(key, "—")
            widget.config(text=value)

    def clear(self):
        for widget in self.fields.values():
            widget.config(text="—")
