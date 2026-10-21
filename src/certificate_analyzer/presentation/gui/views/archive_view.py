"""Password-protected export/import dialogs; all data operations go through IPC."""

import json
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from certificate_analyzer.presentation.gui.widgets.table_sort import TreeviewSorter
from certificate_analyzer.presentation.gui.widgets.scrollable_panel import ScrollablePanel
from certificate_analyzer.domain.enums.certificate_request_status import CertificateRequestStatus

LABELS = {"certificates": "Сертификаты", "employees": "Сотрудники", "mchds": "МЧД", "requests": "Заявки"}
CHOICES = {"Сохранить текущую": "current", "Использовать из архива": "incoming", "Пропустить": "skip"}
TABLE_COLUMNS = {
    "certificates": {"subject": "ФИО", "original_name": "Название сертификата / файл", "valid_from": "Действителен с", "valid_to": "Действителен до", "department": "Подразделение", "status": "Статус", "issuer": "Издатель", "serial_number": "Серийный номер"},
    "employees": {"full_name": "ФИО", "department": "Подразделение", "position": "Должность", "email": "Email"},
    "mchds": {"id": "Номер МЧД", "representative_fio": "Представитель", "principal_name": "Доверитель", "valid_to": "Действует до", "status": "Статус"},
    "requests": {"request_number": "Номер заявки", "employee": "Сотрудник", "department": "Подразделение", "status": "Статус", "submitted_at": "Дата подачи"},
}


class ExportArchiveWizard(tk.Toplevel):
    """Choose individual records, then protect the archive with a password."""

    def __init__(self, handler, records):
        super().__init__(handler.root)
        self.handler = handler
        self.records = {category: records.get(category, []) for category in LABELS}
        self.title("Экспорт хранилища сертификатов")
        self.geometry("1050x620")
        self.minsize(600, 420)
        self.transient(handler.root)
        self.step = 0
        self.password = tk.StringVar(master=self)
        self.confirm = tk.StringVar(master=self)
        self.variables = {category: {str(row["id"]): tk.BooleanVar(master=self, value=False) for row in rows} for category, rows in self.records.items()}
        self.checkbox_images = self.create_checkbox_images()
        self.body = ttk.Frame(self, padding=16)
        self.body.pack(fill="both", expand=True)
        self.render()

    def required_employees(self):
        return {str(row["employee_id"]) for category in ("certificates", "requests") for row in self.records[category] if row.get("employee_id") is not None and self.variables[category][str(row["id"])].get()}

    def required_certificates(self):
        return {str(row["certificate_fingerprint"]) for row in self.records["requests"] if row.get("certificate_fingerprint") and self.variables["requests"][str(row["id"])].get()}

    def required_rows(self, category):
        return self.required_employees() if category == "employees" else self.required_certificates() if category == "certificates" else set()

    def sync_dependencies(self):
        for identifier in self.required_certificates():
            if identifier in self.variables["certificates"]:
                self.variables["certificates"][identifier].set(True)
        for identifier in self.required_employees():
            if identifier in self.variables["employees"]:
                self.variables["employees"][identifier].set(True)

    def create_checkbox_images(self):
        images = {}
        for name in ("empty", "checked", "linked"):
            image = tk.PhotoImage(master=self, width=18, height=18)
            color = "#969696" if name == "linked" else "#334155"
            image.put(color, to=(1, 1, 17, 2))
            image.put(color, to=(1, 16, 17, 17))
            image.put(color, to=(1, 1, 2, 17))
            image.put(color, to=(16, 1, 17, 17))
            if name != "empty":
                for x, y in ((4, 9), (5, 10), (6, 11), (7, 12), (8, 11), (9, 10), (10, 9), (11, 8), (12, 7), (13, 6)):
                    image.put(color, to=(x, y, x + 2, y + 2))
            images[name] = image
        return images

    def selection_image(self, category, identifier):
        if identifier in self.required_rows(category):
            return self.checkbox_images["linked"]
        return self.checkbox_images["checked" if self.variables[category][identifier].get() else "empty"]

    def toggle_row(self, category, identifier):
        if not identifier or identifier in self.required_rows(category):
            return
        variable = self.variables[category][identifier]
        variable.set(not variable.get())
        self.sync_dependencies()
        self.table.item(identifier, image=self.selection_image(category, identifier))

    @staticmethod
    def display_value(row, key):
        value = row.get(key) or "—"
        if key in ("valid_from", "valid_to", "submitted_at") and value != "—":
            try:
                return datetime.fromisoformat(str(value)).strftime("%d.%m.%Y")
            except ValueError:
                pass
        if key == "status":
            labels = {"ACTIVE": "Действует", "EXPIRED": "Просрочен", "EXPIRING_SOON": "Истекает", "INVALID": "Недействителен", "REVOKED": "Отозван"}
            try:
                return CertificateRequestStatus(value).label
            except ValueError:
                return labels.get(value, value)
        return value

    def toggle_all(self, category, value):
        required = self.required_rows(category)
        for identifier, variable in self.variables[category].items():
            variable.set(value or identifier in required)
        self.sync_dependencies()
        if hasattr(self, "table") and self.step < len(LABELS) and list(LABELS)[self.step] == category:
            for identifier in self.table.get_children():
                self.table.item(identifier, image=self.selection_image(category, identifier))

    def move(self, offset):
        self.step += offset
        self.render()

    def render(self):
        for widget in self.body.winfo_children():
            widget.destroy()
        stages = list(LABELS)
        self.sync_dependencies()
        title = LABELS[stages[self.step]] if self.step < len(LABELS) else "Пароль и сохранение"
        ttk.Label(self.body, text=f"Шаг {self.step + 1} из {len(LABELS) + 1} — {title}", font=("", 13, "bold")).pack(anchor="w", pady=(0, 12))
        navigation = ttk.Frame(self.body)
        navigation.pack(side="bottom", fill="x", pady=(12, 0))
        if self.step < len(LABELS):
            category = stages[self.step]
            controls = ttk.Frame(self.body)
            controls.pack(fill="x", pady=(0, 8))
            ttk.Button(controls, text="Выбрать всё", command=lambda: self.toggle_all(category, True)).pack(side="left")
            ttk.Button(controls, text="Снять выбор", command=lambda: self.toggle_all(category, False)).pack(side="left", padx=8)
            required = self.required_rows(category)
            if required:
                ttk.Label(self.body, text="Связанные записи включаются автоматически для сохранения связей.", wraplength=900).pack(anchor="w", pady=5)
            area = ttk.Frame(self.body)
            area.pack(fill="both", expand=True)
            columns = TABLE_COLUMNS[category]
            self.table = ttk.Treeview(area, columns=tuple(columns), show="tree headings", selectmode="browse")
            self.table.heading("#0", text="")
            self.table.column("#0", width=44, minwidth=44, stretch=False)
            for key, title in columns.items():
                self.table.heading(key, text=title)
                self.table.column(key, width=180, minwidth=110)
            vertical = ttk.Scrollbar(area, orient="vertical", command=self.table.yview)
            horizontal = ttk.Scrollbar(area, orient="horizontal", command=self.table.xview)
            self.table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
            self.table.grid(row=0, column=0, sticky="nsew")
            vertical.grid(row=0, column=1, sticky="ns")
            horizontal.grid(row=1, column=0, sticky="ew")
            area.rowconfigure(0, weight=1)
            area.columnconfigure(0, weight=1)
            for row in self.records[category]:
                identifier = str(row["id"])
                if identifier in required:
                    self.variables[category][identifier].set(True)
                self.table.insert("", "end", iid=identifier, image=self.selection_image(category, identifier), values=tuple(self.display_value(row, key) for key in columns))
            self.table_sorter = TreeviewSorter(self.table, kinds={"valid_from": "date", "valid_to": "date", "submitted_at": "date"})
            self.table.bind("<Button-1>", lambda event: self.toggle_row(category, self.table.identify_row(event.y)) if self.table.identify_region(event.x, event.y) in ("tree", "cell") and self.table.identify_column(event.x) == "#0" else None)
            self.table.bind("<space>", lambda event: self.toggle_row(category, self.table.focus()))
            ttk.Label(self.body, text="Отметьте нужные записи галочками. Серые галочки обозначают связанные записи.").pack(anchor="w", pady=5)
            if not self.records[category]:
                ttk.Label(self.body, text="Нет записей для экспорта").pack(anchor="w")
        else:
            form = ScrollablePanel(self.body)
            form.pack(fill="both", expand=True)
            for category, label in LABELS.items():
                count = sum(variable.get() for variable in self.variables[category].values())
                ttk.Label(form.body, text=f"{label}: {count}").pack(anchor="w", pady=3)
            for label, variable in (("Пароль (не менее 12 символов)", self.password), ("Повторите пароль", self.confirm)):
                ttk.Label(form.body, text=label).pack(anchor="w", pady=(12, 4))
                entry = ttk.Entry(form.body, textvariable=variable, show="•", width=32)
                entry.pack(fill="x")
                entry.bind("<FocusIn>", lambda _, entry=entry: form.canvas.yview_moveto(
                    min(1, entry.winfo_y() / max(1, form.body.winfo_height()))))
            form.bind_mousewheel()
        ttk.Button(navigation, text="Отмена", command=self.destroy).pack(side="left")
        ttk.Button(navigation, text="Назад", command=lambda: self.move(-1), state="disabled" if self.step == 0 else "normal").pack(side="left", padx=8)
        ttk.Button(navigation, text="Далее" if self.step < len(LABELS) else "Сохранить архив…", command=(lambda: self.move(1)) if self.step < len(LABELS) else self.save).pack(side="right")

    def save(self):
        self.sync_dependencies()
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
        self.title("Импорт хранилища сертификатов" if importing else "Экспорт хранилища сертификатов")
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
