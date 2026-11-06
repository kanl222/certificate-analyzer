"""Inline employee suggestions with stable employee identity."""
import tkinter as tk
from tkinter import ttk


class EmployeeAutocomplete(ttk.Entry):
    def __init__(self, parent, *, employees, on_select, **kwargs):
        super().__init__(parent, **kwargs)
        self.employees = employees
        self.on_select = on_select
        self.matches = []
        self.popup = tk.Toplevel(self)
        self.popup.withdraw()
        self.popup.overrideredirect(True)
        self.popup.transient(self.winfo_toplevel())
        self.listbox = tk.Listbox(self.popup, exportselection=False, height=6)
        self.listbox.pack(fill="both", expand=True)
        self.bind("<KeyRelease>", self.suggest)
        self.bind("<Down>", self.move)
        self.bind("<Up>", lambda event: self.move(event, -1))
        self.bind("<Return>", self.choose)
        self.bind("<Escape>", self.hide)
        self.bind("<FocusOut>", lambda event: self.after(150, self.hide))
        self.listbox.bind("<ButtonRelease-1>", self.choose)
        self.listbox.bind("<Return>", self.choose)
        self.listbox.bind("<Escape>", self.hide)
        self.bind("<Destroy>", lambda event: self.popup.destroy() if event.widget is self else None)

    def set(self, text):
        self.delete(0, "end")
        self.insert(0, text)

    def hide(self, event=None):
        self.popup.withdraw()
        return "break" if event else None

    def suggest(self, event=None):
        if event and event.keysym in ("Up", "Down", "Return", "Escape", "Tab"):
            return
        query = self.get().strip().casefold()
        self.matches = [e for e in self.employees if query and e.full_name.casefold().startswith(query)][:30]
        self.listbox.delete(0, "end")
        for employee in self.matches:
            self.listbox.insert("end", f"{employee.full_name} — {employee.department or 'Без подразделения'} (№ {employee.id or '—'})")
        if not self.matches:
            self.hide()
            return
        self.popup.geometry(f"{max(420, self.winfo_width())}x{min(6, len(self.matches)) * 22 + 6}+{self.winfo_rootx()}+{self.winfo_rooty() + self.winfo_height()}")
        self.popup.deiconify()
        self.popup.lift()

    def move(self, event=None, step=1):
        if not self.matches:
            self.suggest()
        if self.matches:
            selection = self.listbox.curselection()
            index = max(0, min(len(self.matches) - 1, selection[0] + step if selection else 0))
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(index)
            self.listbox.see(index)
        return "break"

    def choose(self, event=None):
        selection = self.listbox.curselection()
        if self.popup.state() != "withdrawn" and selection:
            self.on_select(self.matches[selection[0]])
            self.hide()
            self.focus_set()
            return "break"
