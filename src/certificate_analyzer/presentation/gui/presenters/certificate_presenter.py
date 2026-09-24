import datetime
import os
from datetime import datetime
from typing import Any

import pyperclip

from certificate_analyzer.infrastructure.config.config_loader import load_settings
from certificate_analyzer.infrastructure.config.config_loader import (
    save_settings as persist_settings,
)
from certificate_analyzer.infrastructure.platform.base import open_path
from certificate_analyzer.presentation.gui.view_models.certificate_view_model import (
    create_certificate_view_model,
)


class CertificatePresenter:
    """Presenter coordinating between CertificateAnalyzerCore (Model) and ICertificateView (View)."""

    def __init__(self, view, model):
        self.view = view
        self.model = model
        self.cert_data_cache: list[dict[str, Any]] = []
        self.current_search_query: str = ""
        self.search_active: bool = False
        self.date_filter_active: bool = False
        self.date_from: datetime.date | None = None
        self.date_to: datetime.date | None = None
        self.sort_reverse: dict[str, bool] = {
            "Тип": False,
            "Имя файла": False,
            "С": False,
            "По": False,
            "ФИО": False,
            "Серийный номер": False,
            "Email": False,
            "Кабинет": False,
            "Отдел": False,
            "Телефон": False,
            "Статус": False,
        }
        self._expired_notification_shown = False
        self._warning_notification_shown = False

    def load_phonebook(self, file_path: str) -> bool:
        """Load phonebook into the core model and update settings."""
        if not file_path:
            return False
        success = self.model.load_phonebook(file_path)
        if success:
            settings = load_settings()
            settings.phonebook_path = file_path
            persist_settings(settings)
            count = len(self.model.phonebook.data)
            self.view.show_notification(
                f"Справочник успешно загружен! Найдено {count} записей",
                "success",
                4000,
            )
            return True
        else:
            self.view.show_notification(
                "Ошибка при загрузке справочника. Проверьте формат файла.",
                "error",
                4000,
            )
            return False

    def scan_folder(self, folder_path: str) -> None:
        """Scan folder for certificate files and process them."""
        if not folder_path:
            self.view.show_warning("Внимание", "Выберите папку!")
            return
        try:
            self.model.scan_certificates(folder_path)
            self.view.set_loaded_files([os.path.basename(f) for f in self.model.loaded_files])
            self.parse_certificates()
            self.clear_search()
        except Exception as e:
            self.view.show_error("Ошибка", str(e))

    def parse_certificates(self) -> list[dict[str, Any]]:
        """Parse certificates using the Model and map them to ViewModels for the View."""
        try:
            # Parse certificates in the core model
            self.model.parse_certificates()
            
            # Map domain models to presentation ViewModels
            view_models = []
            for cert in self.model.certificates:
                vm = create_certificate_view_model(cert).to_dict()
                view_models.append(vm)
            
            self.cert_data_cache = view_models
            self.display_current_data()

            if self.model.errors:
                self.view.show_warning(
                    "Ошибки файлов",
                    "\n".join(f"{path}: {error}" for path, error in self.model.errors.items()),
                )

            self.check_for_expired_certificates()
            return self.cert_data_cache
        except Exception as e:
            self.view.show_error("Ошибка", str(e))
            return []

    def display_current_data(self) -> None:
        """Send current cached data to View and update statistics."""
        data_to_display = self.get_filtered_data()
        self.view.display_certificates(data_to_display)
        self.update_stats()

    def get_filtered_data(self) -> list[dict[str, Any]]:
        """Apply active search and date filters to the cached data."""
        data = self.cert_data_cache

        # Date filter
        if self.date_filter_active and self.date_from and self.date_to:
            filtered = []
            for item in data:
                try:
                    date_str = item.get("valid_to", "")
                    if date_str and date_str not in ("—", "Не найден", "Ошибка"):
                        item_date = datetime.strptime(date_str, "%d.%m.%Y").date()
                        if self.date_from <= item_date <= self.date_to:
                            filtered.append(item)
                except Exception:
                    continue
            data = filtered

        # Search filter
        if self.search_active and self.current_search_query:
            query = self.current_search_query.lower()
            filtered = []
            for item in data:
                values_to_check = [
                    os.path.basename(item.get("file_name", "")).lower(),
                    item.get("subject_cn", "").lower(),
                    item.get("serial_number", "").lower(),
                    item.get("email", "").lower(),
                    item.get("office_number", "—").lower(),
                    item.get("department", "—").lower(),
                    item.get("phone", "—").lower(),
                    item.get("status", "").lower(),
                ]
                if any(query in value for value in values_to_check):
                    filtered.append(item)
            data = filtered

        return data

    def on_search(self, query: str) -> None:
        """Handle search query update."""
        query = query.strip().lower()
        self.current_search_query = query
        if not query:
            self.search_active = False
            self.view.set_search_result_text("")
            self.display_current_data()
            return

        self.search_active = True
        filtered = self.get_filtered_data()
        self.view.display_certificates(filtered)
        total = len(self.cert_data_cache)
        self.view.set_search_result_text(f"Найдено: {len(filtered)} из {total}")

    def clear_search(self) -> None:
        """Reset search state."""
        self.search_active = False
        self.current_search_query = ""
        self.view.clear_search_input()
        self.view.set_search_result_text("")
        self.display_current_data()

    def apply_date_filter(self, date_from, date_to) -> None:
        """Apply date range filter."""
        self.date_from = date_from
        self.date_to = date_to
        self.date_filter_active = True
        filtered = self.get_filtered_data()
        self.view.display_certificates(filtered)
        self.view.set_search_result_text(f"Фильтр: {len(filtered)} записей")

    def clear_date_filter(self) -> None:
        """Clear date range filter."""
        self.date_filter_active = False
        self.date_from = None
        self.date_to = None
        self.display_current_data()

    def update_stats(self) -> dict[str, int]:
        """Calculate statistics from current dataset and command View to render them."""
        data = self.cert_data_cache
        total = len(data)
        expired = sum(1 for cert in data if cert.get("status") == "Просрочен")
        warning = sum(1 for cert in data if "Истекает" in cert.get("status", ""))
        normal = total - expired - warning

        self.view.update_stats_view(total, expired, warning, normal)
        return {"total": total, "expired": expired, "warning": warning, "normal": normal}

    def check_for_expired_certificates(self) -> None:
        """Inspect cached certificates and issue notifications if needed."""
        expired_count = sum(1 for cert in self.cert_data_cache if cert.get("status") == "Просрочен")
        warning_count = sum(1 for cert in self.cert_data_cache if "Истекает" in cert.get("status", ""))

        if expired_count > 0 and not self._expired_notification_shown:
            self.view.show_notification(
                f"⚠️ Обнаружено {expired_count} просроченных сертификатов! Требуется внимание.",
                "error",
                5000,
            )
            self._expired_notification_shown = True
        elif warning_count > 0 and not self._warning_notification_shown:
            self.view.show_notification(
                f"⚡ {warning_count} сертификатов истекают в ближайшее время.",
                "warning",
                4000,
            )
            self._warning_notification_shown = True

    def open_certificate_file(self, file_name: str) -> None:
        """Open local certificate file in the system default viewer."""
        for path in self.model.loaded_files:
            if os.path.basename(path) == file_name:
                if os.path.exists(path):
                    try:
                        open_path(path)
                    except Exception as e:
                        self.view.show_error("Ошибка", f"Не удалось открыть файл: {e}")
                break

    def delete_selected_certificates(self, selected_items: list[tuple]) -> int:
        """Delete physical certificate files for selected rows."""
        if not selected_items:
            self.view.show_warning("Внимание", "Выберите записи для удаления")
            return 0

        if not self.view.ask_yes_no("Подтверждение", "Вы уверены, что хотите удалить выбранные файлы?"):
            return 0

        deleted_count = 0
        items_to_remove = []
        for item_id, file_name in selected_items:
            for full_path in self.model.loaded_files:
                if os.path.basename(full_path) == file_name:
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                            deleted_count += 1
                            items_to_remove.append(item_id)
                        except Exception as e:
                            self.view.show_error("Ошибка", f"Не удалось удалить {file_name}: {e}")
                    break

        if items_to_remove:
            self.view.remove_tree_items(items_to_remove)

        if deleted_count > 0:
            self.view.show_message("Успех", f"Удалено файлов: {deleted_count}")
        return deleted_count

    def copy_to_clipboard(self, rows_data: list[list[Any]]) -> None:
        """Copy selected rows to system clipboard as tab-separated values."""
        if not rows_data:
            self.view.show_error("Ошибка", "Нет выделенных строк!")
            return
        lines = ["\t".join(str(v) for v in row) for row in rows_data]
        pyperclip.copy("\n".join(lines))
        self.view.show_message("Успех", "Скопировано!")

    def export_to_excel(self, save_path: str, report_title: str) -> str | None:
        """Export current certificate view models to Excel via model."""
        if not self.cert_data_cache:
            self.view.show_error("Ошибка", "Нет данных для экспорта!")
            return None
        return self.model.export_to_excel(self.cert_data_cache, save_path, report_title)

    def export_to_pdf(
        self,
        save_path: str,
        figure: Any,
        report_title: str,
        include_chart: bool = True,
    ) -> str | None:
        """Export current certificate view models to PDF via model."""
        if not self.cert_data_cache:
            self.view.show_error("Ошибка", "Нет данных для экспорта!")
            return None
        return self.model.export_to_pdf(
            self.cert_data_cache,
            save_path,
            figure,
            report_title,
            include_chart,
        )

