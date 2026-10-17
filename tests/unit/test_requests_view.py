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


@pytest.mark.skipif(
    not os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST"),
    reason="GUI-тест отключен без флага окружения",
)
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


@pytest.mark.skipif(
    not os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST"),
    reason="GUI-тест отключен без флага окружения",
)
def test_create_employee_from_request(application):
    """Новый сотрудник выбирается в заявке и сохраняется вместе со связью."""
    import tkinter as tk
    from tkinter import ttk

    from certificate_analyzer.domain.enums.certificate_request_status import CertificateRequestStatus
    from certificate_analyzer.presentation.gui.views.employees_view import EmployeeDialog
    from certificate_analyzer.presentation.gui.views.requests_view import RequestsView

    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)

    def button(widget, text):
        return next(
            child for child in descendants(widget)
            if isinstance(child, ttk.Button) and child.cget("text") == text
        )

    root = tk.Tk()
    root.withdraw()
    try:
        view = RequestsView(root, application=application)
        view.show_create_dialog()
        dialog = next(child for child in view.winfo_children() if isinstance(child, tk.Toplevel))
        errors = []

        def fill_employee():
            try:
                editor = next(child for child in dialog.winfo_children() if isinstance(child, EmployeeDialog))
                editor.entries["full_name"].set("Новый сотрудник")
                editor.entries["department"].set("ИТ")
                editor.entries["position"].set("Инженер")
                editor._save()
            except Exception as exc:
                errors.append(exc)
                for child in dialog.winfo_children():
                    if isinstance(child, EmployeeDialog):
                        child.destroy()

        root.after(50, fill_employee)
        button(dialog, "Создать сотрудника…").invoke()
        assert not errors
        assert dialog.grab_current() == dialog
        combo = next(child for child in descendants(dialog) if isinstance(child, ttk.Combobox))
        assert combo.get() == "Новый сотрудник"
        assert "Новый сотрудник" in combo.cget("values")
        button(dialog, "Создать заявку").invoke()

        employee = application.employees.find_by_name("Новый сотрудник")
        assert employee.position == "Инженер"
        request = application.certificate_requests.list_requests()[0]
        assert request.employee_id == employee.id
        assert request.department == "ИТ"
        assert request.status == CertificateRequestStatus.NOT_SUBMITTED
        assert request.submitted_at is None
    finally:
        root.destroy()


@pytest.mark.skipif(
    not os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST"),
    reason="GUI-тест отключен без флага окружения",
)
@pytest.mark.parametrize("use_picker", [False, True])
def test_request_keeps_selected_employee_id(application, monkeypatch, use_picker):
    import tkinter as tk
    from tkinter import ttk
    from certificate_analyzer.presentation.gui.views import requests_view as module

    first = application.employees.save_employee(Employee(full_name="Одинаковое ФИО", department="ИТ"))
    application.employees.save_employee(Employee(full_name="Одинаковое ФИО", department="ИТ"))

    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)

    def button(widget, text):
        return next(child for child in descendants(widget) if isinstance(child, ttk.Button) and child.cget("text") == text)

    def pick(picker):
        picker.destroy()
        return first

    monkeypatch.setattr(module.EmployeePickerDialog, "show", pick)
    errors = []
    monkeypatch.setattr(module.messagebox, "showerror", lambda *args, **kwargs: errors.append(args))
    root = tk.Tk()
    root.withdraw()
    try:
        view = module.RequestsView(root, application=application)
        view.show_create_dialog_for(first.full_name, first.department, employee_id=first.id)
        dialog = next(child for child in view.winfo_children() if isinstance(child, tk.Toplevel))
        combo = next(child for child in descendants(dialog) if isinstance(child, ttk.Combobox))
        if use_picker:
            combo.set("Неизвестный сотрудник")
            button(dialog, "Создать заявку").invoke()
            assert errors
            assert application.certificate_requests.list_requests() == []
            errors.clear()
            combo.set(first.full_name)
            button(dialog, "Создать заявку").invoke()
            assert errors
            assert application.certificate_requests.list_requests() == []
            errors.clear()
            button(dialog, "Выбрать…").invoke()
        button(dialog, "Создать заявку").invoke()
        assert not errors
        assert application.certificate_requests.list_requests()[0].employee_id == first.id
    finally:
        root.destroy()
