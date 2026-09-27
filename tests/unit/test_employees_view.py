"""Тесты для справочника сотрудников, сервиса и графического представления EmployeesView."""

import os
from unittest.mock import MagicMock
import pytest

from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.infrastructure.repositories.employee_repository import (
    EmployeeRepository,
)


def test_employee_repository_crud(application):
    """Проверяет сохранение, поиск и удаление сотрудника в EmployeeRepository."""
    repo = EmployeeRepository(application.database.sessions)

    emp = Employee(
        full_name="Сидоров Сидор Сидорович",
        department="ИТ",
        office="101",
        phones=["11-22", "33-44"],
        email="sidorov@example.com",
        position="Инженер",
        inn="7701234567",
        snils="12345678901",
    )
    saved = repo.save(emp)
    assert saved.id is not None
    assert saved.full_name == "Сидоров Сидор Сидорович"
    assert saved.phones == ["11-22", "33-44"]

    found = repo.get_by_id(saved.id)
    assert found is not None
    assert found.full_name == "Сидоров Сидор Сидорович"
    assert found.email == "sidorov@example.com"

    # Регистронезависимый поиск по подстроке
    search_res = repo.list_all(search="сидор")
    assert len(search_res) == 1

    search_upper = repo.list_all(search="СИДОРОВ")
    assert len(search_upper) == 1

    # Удаление
    assert repo.delete(saved.id) is True
    assert repo.get_by_id(saved.id) is None
    assert repo.delete(99999) is False


def test_employee_service_delete(application):
    """Проверяет метод delete_employee в EmployeeService."""
    service = application.employees

    emp = service.save_employee(Employee(full_name="Козлов Козел Козлович", department="Бухгалтерия"))
    assert emp.id is not None

    deleted = service.delete_employee(emp.id)
    assert deleted is True
    assert service.get_employee(emp.id) is None


@pytest.mark.skipif(not os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST"), reason="GUI-тест отключен")
def test_employees_view_ui(application):
    """Проверяет инициализацию и наполнение таблицы EmployeesView."""
    import tkinter as tk
    from certificate_analyzer.presentation.gui.views.employees_view import EmployeesView

    root = tk.Tk()
    root.withdraw()
    try:
        application.employees.save_employee(
            Employee(
                full_name="Алексеев Алексей",
                position="Аналитик",
                department="Отдел аналитики",
                office="205",
                phones=["55-66"],
                email="alex@corp.local",
            )
        )

        messages = []
        view = EmployeesView(root, application=application, on_message=messages.append)
        view.pack()

        assert len(view.employees) >= 1
        assert any(e.full_name == "Алексеев Алексей" for e in view.employees)
        assert len(view.tree.get_children()) >= 1

        # Проверка поиска
        view.search_var.set("Алексеев")
        view.refresh()
        assert len(view.employees) == 1

        view.search_var.set("Несуществующий")
        view.refresh()
        assert len(view.employees) == 0

        view._clear_search()
        assert len(view.employees) >= 1
    finally:
        root.destroy()


@pytest.mark.skipif(not os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST"), reason="GUI-тест отключен")
def test_employee_dialog_validation(monkeypatch):
    """Проверяет валидацию полей в EmployeeDialog."""
    import tkinter as tk
    from tkinter import messagebox
    from certificate_analyzer.presentation.gui.views.employees_view import EmployeeDialog

    errors = []
    monkeypatch.setattr(messagebox, "showerror", lambda *args, **kwargs: errors.append(args))
    monkeypatch.setattr(messagebox, "showinfo", lambda *args, **kwargs: None)
    monkeypatch.setattr(messagebox, "askyesno", lambda *args, **kwargs: True)

    root = tk.Tk()
    root.withdraw()
    try:
        saved_callback = MagicMock()
        dialog = EmployeeDialog(root, employee=None, on_save=saved_callback)


        # 1. Пустое ФИО
        dialog.entries["full_name"].set("")
        dialog._save()
        saved_callback.assert_not_called()

        # 2. Некорректный ИНН
        dialog.entries["full_name"].set("Петров Петр")
        dialog.entries["inn"].set("12345")
        dialog._save()
        saved_callback.assert_not_called()

        # 3. Некорректный СНИЛС
        dialog.entries["inn"].set("7701234567")
        dialog.entries["snils"].set("123")
        dialog._save()
        saved_callback.assert_not_called()

        # 4. Корректные данные
        dialog.entries["snils"].set("12345678901")
        dialog.entries["phones"].set("11-22, 33-44")
        dialog._save()
        saved_callback.assert_called_once()
        saved_emp = saved_callback.call_args[0][0]
        assert saved_emp.full_name == "Петров Петр"
        assert saved_emp.phones == ["11-22", "33-44"]
    finally:
        root.destroy()
