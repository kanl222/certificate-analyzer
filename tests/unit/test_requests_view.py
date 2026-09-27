"""Тесты для представления заявок RequestsView и диалога выбора сотрудника EmployeePickerDialog."""

import os
import pytest

from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.presentation.gui.views.requests_view import (
    EmployeePickerDialog,
    REQUEST_COLUMNS,
)


def test_request_table_omits_redundant_signature_column() -> None:
    """Все заявки относятся к выпуску сертификата ЭП, отдельная колонка не нужна."""
    assert "needs_signature" not in REQUEST_COLUMNS


def test_employee_picker_dialog_filter(monkeypatch):
    """Проверяет фильтрацию сотрудников в таблице диалога EmployeePickerDialog."""
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    try:
        employees = [
            Employee(
                full_name="Иванов Иван Иванович",
                department="Бухгалтерия",
                position="Главный бухгалтер",
                email="ivanov@corp.test",
            ),
            Employee(
                full_name="Петров Петр Петрович",
                department="Отдел ИТ",
                position="Системный администратор",
                email="petrov@corp.test",
            ),
            Employee(
                full_name="Сидоров Сидор",
                department="Отдел кадров",
                position="HR-специалист",
                email="sidorov@corp.test",
            ),
        ]

        picker = EmployeePickerDialog(root, employees=employees)
        assert len(picker.tree.get_children()) == 3

        # Фильтрация по фамилии
        picker.search_var.set("Петров")
        filtered_items = picker.tree.get_children()
        assert len(filtered_items) == 1
        item_vals = picker.tree.item(filtered_items[0], "values")
        assert item_vals[0] == "Петров Петр Петрович"
        assert item_vals[1] == "Отдел ИТ"

        # Фильтрация по подразделению
        picker.search_var.set("кадров")
        assert len(picker.tree.get_children()) == 1

        # Очистка фильтра
        picker.search_var.set("")
        assert len(picker.tree.get_children()) == 3

        # Имитируем выбор первого сотрудника
        first_id = picker.tree.get_children()[0]
        picker.tree.selection_set(first_id)
        picker._select()

        assert picker.selected_employee is not None
        assert picker.selected_employee.full_name == "Иванов Иван Иванович"
    finally:
        root.destroy()


@pytest.mark.skipif(
    not os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST"),
    reason="GUI-тест отключен без флага окружения",
)
def test_requests_view_create_dialog_autofill(application, monkeypatch):
    """Проверяет выпадающий список сотрудников и автозаполнение подразделения в диалоге создания заявки."""
    import tkinter as tk
    from certificate_analyzer.presentation.gui.views.requests_view import RequestsView

    # Добавляем тестового сотрудника
    emp = Employee(
        full_name="Семенов Семен",
        department="Финансовый отдел",
        position="Аналитик",
    )
    application.employees.save_employee(emp)

    root = tk.Tk()
    root.withdraw()
    try:
        view = RequestsView(root, application=application)
        view.pack()

        # Проверяем метод show_create_dialog_for
        view.show_create_dialog_for(full_name="Семенов Семен")
    finally:
        root.destroy()
