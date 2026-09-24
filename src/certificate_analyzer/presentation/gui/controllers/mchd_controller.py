import os
import tkinter as tk
from tkinter import messagebox

from certificate_analyzer.presentation.gui.views.mchd_view import MCHDTableWindow


class MchdController:
    def scan_mchd_folder(self):
        self.current_folder_key = "📁 МЧД"
        path = self.core.mchd_folder
        if not os.path.exists(path):
            response = messagebox.askyesno(
                "Создать папку", f"Папка МЧД не существует. Создать?\n{path}"
            )
            if response:
                os.makedirs(path)
                messagebox.showinfo(
                    "Информация",
                    f"Папка создана:\n{path}\n\nПоместите в нее XML файлы МЧД",
                )
                return
            else:
                return
        self.folder_path.set(path)
        self.current_folder_label.config(text="Текущая: МЧД")
        self.folder_history.append(path)
        try:
            mchd_files = self.core.scan_mchd_files()
            self.listbox_mchd.delete(0, tk.END)
            self.mchd_data_cache = []
            if not mchd_files:
                messagebox.showinfo(
                    "Информация", f"В папке {path} не найдено XML файлов"
                )
                return
            for f in mchd_files:
                self.listbox_mchd.insert(tk.END, os.path.basename(f))
                mchd_info = self.mchd_parser.parse_file(f)
                self.mchd_data_cache.append(mchd_info)
            messagebox.showinfo(
                "Успех", f"Найдено и проанализировано {len(mchd_files)} МЧД"
            )
            self.analyze_mchd()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сканировании МЧД:\n{e!s}")

    def analyze_mchd(self):
        if not self.mchd_data_cache:
            self.scan_mchd_folder()
            if not self.mchd_data_cache:
                messagebox.showwarning("Внимание", "Нет данных МЧД для анализа")
                return
        if (
            "mchd_table" in self.open_windows
            and self.open_windows["mchd_table"] is not None
        ):
            try:
                if (
                    hasattr(self.open_windows["mchd_table"], "window")
                    and self.open_windows["mchd_table"].window
                ):
                    if self.open_windows["mchd_table"].window.winfo_exists():
                        self.open_windows["mchd_table"].window.lift()
                        self.open_windows["mchd_table"].window.focus_force()
                        return
            except:
                pass
        window = MCHDTableWindow(self.root, self.mchd_data_cache)
        self.open_windows["mchd_table"] = window
