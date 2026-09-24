import tkinter as tk
from tkinter import ttk


class StatCard(ttk.Frame):
    def __init__(self, parent, title, value, color=None, **kwargs):
        super().__init__(parent, style="Card.TFrame", padding=12, **kwargs)
        self.title_label = ttk.Label(self, text=title, style="CardTitle.TLabel")
        self.title_label.pack(anchor=tk.W)
        self.value_label = ttk.Label(self, text=value, style="CardValue.TLabel")
        self.value_label.pack(anchor=tk.W)
        if color:
            self.value_label.configure(foreground=color)

    def set_value(self, value):
        self.value_label.config(text=value)
