"""Password-protected export/import dialogs; all data operations go through IPC."""

import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

LABELS = {"certificates": "Сертификаты", "employees": "Сотрудники", "mchds": "МЧД"}
CHOICES = {"Сохранить текущую": "current", "Использовать из архива": "incoming", "Пропустить": "skip"}


class ExportArchiveWizard(tk.Toplevel):
    """Choose individual records, then protect the archive with a password."""

    def __init__(self, handler, records):
        super().__init__(handler.root)
        self.handler, self.records = handler, records
        self.title("Экспорт защищённого архива")
        self.geometry("780x560")
        self.minsize(600, 420)
        self.transient(handler.root)
        self.step = 0
        self.password = tk.StringVar(master=self)
        self.confirm = tk.StringVar(master=self)
        self.variables = {category: {str(row["id"]): tk.BooleanVar(master=self, value=False) for row in rows} for category, rows in records.items()}
        self.body = ttk.Frame(self, padding=16)
        self.body.pack(fill="both", expand=True)
        self.render()

    def required_employees(self):
        return {str(row["employee_id"]) for row in self.records["certificates"] if row.get("employee_id") is not None and self.variables["certificates"][str(row["id"])].get()}

    def toggle_all(self, category, value):
        required = self.required_employees() if category == "employees" else set()
        for identifier, variable in self.variables[category].items():
            variable.set(value or identifier in required)

    def move(self, offset):
        self.step += offset
        self.render()

    def render(self):
        for widget in self.body.winfo_children():
            widget.destroy()
        stages = list(LABELS)
        title = LABELS[stages[self.step]] if self.step < 3 else "Пароль и сохранение"
        ttk.Label(self.body, text=f"Шаг {self.step + 1} из 4 — {title}", font=("", 13, "bold")).pack(anchor="w", pady=(0, 12))
        if self.step < 3:
            category = stages[self.step]
            controls = ttk.Frame(self.body)
            controls.pack(fill="x", pady=(0, 8))
            ttk.Button(controls, text="Выбрать всё", command=lambda: self.toggle_all(category, True)).pack(side="left")
            ttk.Button(controls, text="Снять выбор", command=lambda: self.toggle_all(category, False)).pack(side="left", padx=8)
            required = self.required_employees() if category == "employees" else set()
            if required:
                ttk.Label(self.body, text="Сотрудники, связанные с выбранными сертификатами, включаются для сохранения связей.", wraplength=700).pack(anchor="w", pady=5)
            area = ttk.Frame(self.body)
            area.pack(fill="both", expand=True)
            canvas = tk.Canvas(area, highlightthickness=0)
            scroll = ttk.Scrollbar(area, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=scroll.set)
            scroll.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)
            rows = ttk.Frame(canvas)
            window_id = canvas.create_window((0, 0), window=rows, anchor="nw")
            rows.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
            if not self.records[category]:
                ttk.Label(rows, text="Нет записей для экспорта").pack(anchor="w", pady=16)
            for row in self.records[category]:
                identifier = str(row["id"])
                linked = identifier in required
                if linked:
                    self.variables[category][identifier].set(True)
                ttk.Checkbutton(rows, text=row["label"] + (" (связан с сертификатом)" if linked else ""), variable=self.variables[category][identifier], state="disabled" if linked else "normal").pack(anchor="w", fill="x", pady=4)
        else:
            for category, label in LABELS.items():
                count = sum(variable.get() for variable in self.variables[category].values())
                ttk.Label(self.body, text=f"{label}: {count}").pack(anchor="w", pady=3)
            for label, variable in (("Пароль (не менее 12 символов)", self.password), ("Повторите пароль", self.confirm)):
                ttk.Label(self.body, text=label).pack(anchor="w", pady=(12, 4))
                ttk.Entry(self.body, textvariable=variable, show="•", width=44).pack(anchor="w")
        navigation = ttk.Frame(self.body)
        navigation.pack(side="bottom", fill="x", pady=(12, 0))
        ttk.Button(navigation, text="Отмена", command=self.destroy).pack(side="left")
        ttk.Button(navigation, text="Назад", command=lambda: self.move(-1), state="disabled" if self.step == 0 else "normal").pack(side="left", padx=8)
        ttk.Button(navigation, text="Далее" if self.step < 3 else "Сохранить архив…", command=(lambda: self.move(1)) if self.step < 3 else self.save).pack(side="right")

    def save(self):
        selected = {category: [row["id"] for row in self.records[category] if self.variables[category][str(row["id"])].get()] for category in LABELS}
        if not any(selected.values()):
            messagebox.showerror("Экспорт", "Выберите хотя бы одну запись", parent=self)
            return
        password = self.password.get()
        if len(password) < 12 or password != self.confirm.get():
            messagebox.showerror("Пароль", "Пароль должен содержать минимум 12 символов; повтор должен совпадать.", parent=self)
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".cat", filetypes=[("Защищённый архив", "*.cat")])
        categories = [category for category, values in selected.items() if values]
        if path and self.handler._submit(lambda: self.handler.app.archive.export(path, password, categories, selected), lambda result: messagebox.showinfo("Экспорт завершён", result["path"], parent=self.handler.root)):
            self.destroy()


class ArchiveDialog(tk.Toplevel):
    def __init__(self, handler, *, importing=False):
        super().__init__(handler.root)
        self.handler = handler
        self.importing = importing
        self.title("Импорт защищённого архива" if importing else "Экспорт защищённого архива")
        self.transient(handler.root)
        self.resizable(False, False)
        self.password = tk.StringVar()
        self.confirm = tk.StringVar()
        self.mode = tk.StringVar(value="add")
        self.selected = {}
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)
        if importing:
            ttk.Radiobutton(frame, text="Добавить к существующим данным", variable=self.mode, value="add").pack(anchor="w")
            ttk.Radiobutton(frame, text="Заменить текущие данные", variable=self.mode, value="replace").pack(anchor="w")
            ttk.Label(frame, text="Перед импортом будет создана защищённая резервная копия.\nДля неё используется пароль импортируемого архива.").pack(anchor="w", pady=8)
        else:
            for category, label in LABELS.items():
                variable = tk.BooleanVar(value=True)
                self.selected[category] = variable
                ttk.Checkbutton(frame, text=label, variable=variable).pack(anchor="w")
            ttk.Label(frame, text="Сертификаты включают сотрудников.\nЗаявки включают сертификаты и сотрудников.").pack(anchor="w", pady=8)
        ttk.Label(frame, text="Пароль архива (не менее 12 символов)").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.password, show="•", width=44).pack(fill="x", pady=4)
        if not importing:
            ttk.Label(frame, text="Повторите пароль").pack(anchor="w")
            ttk.Entry(frame, textvariable=self.confirm, show="•").pack(fill="x", pady=4)
        self.button = ttk.Button(frame, text="Выбрать архив…" if importing else "Сохранить архив…", command=self.submit)
        self.button.pack(pady=10)

    def submit(self):
        password = self.password.get()
        if len(password) < 12 or (not self.importing and password != self.confirm.get()):
            messagebox.showerror("Пароль", "Пароль должен содержать минимум 12 символов; повтор должен совпадать.", parent=self)
            return
        if self.importing:
            path = filedialog.askopenfilename(parent=self, filetypes=[("Защищённый архив", "*.cat"), ("Все файлы", "*")])
            if not path:
                return
            mode = self.mode.get()
            if mode == "replace":
                if not messagebox.askyesno("Замена данных", "Текущие записи будут заменены содержимым архива.\nКатегории, отсутствующие в архиве, останутся пустыми.\nПродолжить с созданием резервной копии?", parent=self):
                    return
                self._restore(path, password, mode, {})
            else:
                if self.handler._submit(lambda: self.handler.app.archive.inspect(path, password), lambda result: self._preview(path, password, result)):
                    self.destroy()
        else:
            categories = [key for key, variable in self.selected.items() if variable.get()]
            if not categories:
                messagebox.showerror("Экспорт", "Выберите хотя бы одну категорию", parent=self)
                return
            path = filedialog.asksaveasfilename(parent=self, defaultextension=".cat", filetypes=[("Защищённый архив", "*.cat")])
            if path and self.handler._submit(lambda: self.handler.app.archive.export(path, password, categories), lambda result: messagebox.showinfo("Экспорт завершён", result["path"], parent=self.handler.root)):
                self.destroy()

    def _restore(self, path, password, mode, decisions, digest=None, revision=None):
        def finished(result):
            self.handler.refresh()
            messagebox.showinfo("Импорт завершён", "Данные обновлены.\nРезервная копия:\n" + result["backup"], parent=self.handler.root)
        if self.handler._submit(lambda: self.handler.app.archive.restore(path, password, mode, decisions, digest, revision), finished) and self.winfo_exists():
            self.destroy()

    def _preview(self, path, password, result):
        if not result["conflicts"]:
            # TaskRunner clears its completed future after this callback returns.
            self.handler.root.after(0, lambda: self._restore(path, password, "add", {}, result["digest"], result["revision"]))
            return
        window = tk.Toplevel(self.handler.root)
        window.title("Разрешение конфликтов")
        window.geometry("850x550")
        frame = ttk.Frame(window, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Выберите действие для каждой совпадающей записи.").pack(anchor="w")
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        rows = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=rows, anchor="nw")
        rows.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        decisions = {}
        for conflict in result["conflicts"]:
            box = ttk.LabelFrame(rows, text=conflict["label"], padding=8)
            box.pack(fill="x", pady=4)
            for title, key in (("Текущая", "current"), ("Из архива", "incoming")):
                ttk.Label(box, text=title + ": " + json.dumps(conflict[key], ensure_ascii=False), wraplength=750).pack(anchor="w")
            variable = tk.StringVar(value="Сохранить текущую")
            decisions[conflict["key"]] = variable
            ttk.Combobox(box, state="readonly", values=list(CHOICES), textvariable=variable, width=30).pack(anchor="w")
        def accept():
            choices = {key: CHOICES[value.get()] for key, value in decisions.items()}
            window.destroy()
            self._restore(path, password, "add", choices, result["digest"], result["revision"])
        ttk.Button(frame, text="Добавить данные", command=accept).pack(pady=8)
