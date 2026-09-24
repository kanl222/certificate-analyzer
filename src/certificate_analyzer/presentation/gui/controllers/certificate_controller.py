import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Any

from certificate_analyzer.infrastructure.platform.base import open_path
from certificate_analyzer.presentation.gui.presenters.certificate_presenter import (
    CertificatePresenter,
)


class CertificateController:
    """Controller acting as an MVP View adapter that delegates to CertificatePresenter."""

    def get_certificate_presenter(self) -> CertificatePresenter:
        if not hasattr(self, "_certificate_presenter") or self._certificate_presenter is None:
            self._certificate_presenter = CertificatePresenter(view=self, model=self.core)
        return self._certificate_presenter

    @property
    def certificate_presenter(self) -> CertificatePresenter:
        return self.get_certificate_presenter()

    @certificate_presenter.setter
    def certificate_presenter(self, presenter: CertificatePresenter):
        self._certificate_presenter = presenter

    # --- ICertificateView Implementation ---

    def show_message(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message)

    def show_warning(self, title: str, message: str) -> None:
        messagebox.showwarning(title, message)

    def show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message)

    def ask_yes_no(self, title: str, message: str) -> bool:
        return messagebox.askyesno(title, message)

    def set_loaded_files(self, file_paths: list[str]) -> None:
        if hasattr(self, "listbox_files"):
            self.listbox_files.delete(0, tk.END)
            for f in file_paths:
                self.listbox_files.insert(tk.END, f)

    def display_certificates(self, data_list: list[dict[str, Any]]) -> None:
        self.cert_data_cache = data_list
        if hasattr(self, "tree"):
            for row in self.tree.get_children():
                self.tree.delete(row)
            self._insert_certificates_into_tree(data_list)
        if hasattr(self, "update_stats"):
            self.update_stats()

    def set_search_result_text(self, text: str) -> None:
        if hasattr(self, "search_result_label"):
            self.search_result_label.config(text=text)

    def clear_search_input(self) -> None:
        if hasattr(self, "search_var"):
            self.search_var.set("")

    def remove_tree_items(self, item_ids: list[Any]) -> None:
        if hasattr(self, "tree"):
            for item in item_ids:
                self.tree.delete(item)

    def update_stats_view(self, total: int, expired: int, warning: int, normal: int) -> None:
        if hasattr(self, "update_stats"):
            self.update_stats()

    # --- User Action Handlers (Delegating to Presenter) ---

    def load_phonebook(self):
        file_path = filedialog.askopenfilename(
            title="Выберите файл справочника",
            filetypes=[
                ("Документы Word", "*.docx"),
                ("Текстовые файлы", "*.txt"),
                ("Все файлы", "*.*"),
            ],
        )
        if file_path:
            if self.certificate_presenter.load_phonebook(file_path):
                self.refresh_all()

    def select_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с сертификатами")
        if folder:
            self.folder_path.set(folder)
            self.folder_history.append(folder)
            self.current_folder_label.config(text=f"Текущая: {os.path.basename(folder)}")
            self.scan_folder()

    def scan_folder(self):
        import threading
        path = self.folder_path.get()
        if not path:
            self.show_warning("Внимание", "Выберите папку!")
            return
            
        if hasattr(self, "progress_bar"):
            self.progress_bar.start()
        if hasattr(self, "status_label"):
            self.status_label.config(text="Сканирование...")

        def worker():
            try:
                # Backend business logic is now decoupled
                result = self.core.scan(path)
                
                # Update UI in main thread safely
                if hasattr(self, "root"):
                    self.root.after(0, lambda: after_scan(result))
            except Exception:
                if hasattr(self, "root"):
                    self.root.after(0, lambda: self.show_error("Ошибка", str(e)))

        def after_scan(result):
            if hasattr(self, "progress_bar"):
                self.progress_bar.stop()
            if hasattr(self, "status_label"):
                self.status_label.config(text="Готово")
                
            # Recreate view models
            self.core.loaded_files = result.loaded_files
            self.core.certificates = result.certificates
            self.core.errors = result.errors
            
            view_models = []
            from certificate_analyzer.presentation.gui.view_models.certificate_view_model import (
                create_certificate_view_model,
            )
            for cert in result.certificates:
                vm = create_certificate_view_model(cert, source_path=cert.source_path).to_dict()
                view_models.append(vm)
                
            self.certificate_presenter.cert_data_cache = view_models
            self.cert_data_cache = view_models
            
            # Update stats
            total = len(result.certificates)
            expired = len(result.expired)
            warning = len(result.expiring)
            normal = len(result.active)
            self.update_stats_view(total, expired, warning, normal)
            
            self.display_certificates(view_models)

        threading.Thread(target=worker, daemon=True).start()

    def parse_certificates(self):
        return self.cert_data_cache

    def on_search(self, *args):
        self.certificate_presenter.on_search(self.search_var.get())

    def clear_search(self):
        self.certificate_presenter.clear_search()

    def refresh_current_view(self):
        self.certificate_presenter.display_current_data()

    def display_current_data(self):
        self.certificate_presenter.display_current_data()

    def check_for_expired_certificates(self):
        self.certificate_presenter.check_for_expired_certificates()

    def on_item_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        values = self.tree.item(item)["values"]
        if not values or len(values) < 2:
            return
        file_name = values[1]
        self.certificate_presenter.open_certificate_file(file_name)

    def delete_selected(self):
        selection = self.tree.selection()
        if not selection:
            self.show_warning("Внимание", "Выберите записи для удаления")
            return
        items = [
            (item, self.tree.item(item)["values"][1])
            for item in selection
            if self.tree.item(item).get("values") and len(self.tree.item(item)["values"]) > 1
        ]
        if self.certificate_presenter.delete_selected_certificates(items):
            self.refresh_all()

    def copy_to_clipboard(self):
        selection = self.tree.selection()
        if not selection:
            self.show_error("Ошибка", "Нет выделенных строк!")
            return
        rows_data = [
            self.tree.item(item)["values"]
            for item in selection
            if self.tree.item(item).get("values")
        ]
        self.certificate_presenter.copy_to_clipboard(rows_data)

    def sort_column(self, col):
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children("")]
        reverse = getattr(self, "sort_reverse", {}).get(col, False)
        if col in ("С", "По"):
            try:
                data.sort(
                    key=lambda x: (
                        datetime.strptime(x[0], "%d.%m.%Y")
                        if x[0] and x[0] not in ("—", "Не найдена", "Не найден")
                        else datetime.min
                    ),
                    reverse=reverse,
                )
            except Exception:
                data.sort(key=lambda x: x[0], reverse=reverse)
        elif col == "ФИО":
            data.sort(key=lambda x: x[0].lower(), reverse=reverse)
        else:
            data.sort(key=lambda x: x[0], reverse=reverse)

        for index, (val, child) in enumerate(data):
            self.tree.move(child, "", index)
        if hasattr(self, "sort_reverse"):
            self.sort_reverse[col] = not reverse

    def _insert_certificates_into_tree(self, data_list):
        from collections import Counter

        names = [
            item.get("subject_cn", "")
            for item in data_list
            if item.get("subject_cn") and item.get("subject_cn") not in ("Не найдено", "Ошибка")
        ]
        duplicates = {name for name, count in Counter(names).items() if count > 1}

        for item in data_list:
            tag_list = []
            status = item.get("status", "")
            if status == "Просрочен":
                tag_list.append("expired")
            elif "Истекает" in status:
                tag_list.append("warning")
            else:
                tag_list.append("normal")

            name = item.get("subject_cn", "")
            if name in duplicates:
                tag_list.append("duplicate")

            self.tree.insert(
                "",
                tk.END,
                values=(
                    item.get("file_type", "Серт"),
                    os.path.basename(item.get("file_name", "")),
                    item.get("valid_from", ""),
                    item.get("valid_to", ""),
                    item.get("subject_cn", ""),
                    item.get("serial_number", ""),
                    item.get("email", "—"),
                    item.get("office_number", "—"),
                    item.get("department", "—"),
                    item.get("phone", "—"),
                    item.get("status", ""),
                ),
                tags=tuple(tag_list),
            )

    def get_report_title(self):
        if "Сотрудники" in self.current_folder_key:
            return "Отчет по сертификатам сотрудников"
        elif "Руководство" in self.current_folder_key:
            return "Отчет по сертификатам руководства"
        else:
            folder_name = (
                os.path.basename(self.folder_path.get())
                if self.folder_path.get()
                else "сертификатам"
            )
            return f"Отчет по сертификатам ({folder_name})"

    def export_to_excel_gui(self):
        if not self.cert_data_cache:
            messagebox.showerror("Ошибка", "Нет данных для экспорта!")
            return
        try:
            report_title = self.get_report_title()
            default_name = f"cert_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            save_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel файлы", "*.xlsx"), ("Все файлы", "*.*")],
                initialdir=self.core.export_folder,
                initialfile=default_name,
                title=f"Сохранить Excel отчет - {report_title}",
            )
            if not save_path:
                return
            saved_path = self.certificate_presenter.export_to_excel(save_path, report_title)
            if saved_path and os.path.exists(saved_path):
                self.show_notification(
                    f"Excel отчет успешно сохранен!\n{os.path.basename(saved_path)}",
                    "success",
                    4000,
                )
                if messagebox.askyesno("Открыть папку", "Открыть папку с отчетом?"):
                    open_path(os.path.dirname(saved_path))
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить файл")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать в Excel:\n{e!s}")

    def export_to_pdf_gui(self):
        if not self.cert_data_cache:
            messagebox.showerror("Ошибка", "Нет данных для экспорта!")
            return
        try:
            report_title = self.get_report_title()
            include_chart = self.include_chart_var.get()
            default_name = f"cert_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            save_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF файлы", "*.pdf"), ("Все файлы", "*.*")],
                initialdir=self.core.export_folder,
                initialfile=default_name,
                title=f"Сохранить PDF отчет - {report_title}",
            )
            if not save_path:
                return
            if not save_path.lower().endswith(".pdf"):
                save_path += ".pdf"
            if os.path.exists(save_path):
                if not messagebox.askyesno("Подтверждение", "Файл уже существует. Перезаписать?"):
                    return
            saved_path = self.certificate_presenter.export_to_pdf(
                save_path,
                self.figure_status,
                report_title,
                include_chart,
            )
            if saved_path and os.path.exists(saved_path):
                self.show_notification(
                    f"PDF отчет успешно сохранен!\n{os.path.basename(saved_path)}",
                    "success",
                    4000,
                )
                if messagebox.askyesno("Открыть файл", "Открыть PDF отчет?"):
                    open_path(saved_path)
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить PDF файл")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать в PDF:\n{e!s}")

    def refresh_all(self):
        self.scan_folder()
