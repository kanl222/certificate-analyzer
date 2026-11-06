import os
import pytest
from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.application.dto.certificate_query import CertificateQuery


def test_comments_survive_reimport_and_clear(application, certificate_file):
    emp = application.employees.save_employee(Employee(full_name="Иванов", comment="Комментарий\nСтрока 2"))
    assert application.employees.get_employee(emp.id).comment == emp.comment
    result = application.certificates.import_files([certificate_file()])
    assert not result.errors
    fingerprint = result.certificates[0].fingerprint_sha256
    application.certificates.update_comment(fingerprint, "Длинный комментарий " * 100)
    application.certificates.import_files([certificate_file(name="another.pem")])
    assert application.certificates.get(fingerprint).comment == "Длинный комментарий " * 100
    application.certificates.update_comment(fingerprint, "")
    assert application.certificates.get(fingerprint).comment == ""


def test_expiry_sort_across_pages(application, certificate_file):
    for index, days in enumerate((100, 10, 50)):
        result = application.certificates.import_files([certificate_file(name=f"{index}.pem", days=days)])
        assert not result.errors
    dates = [application.certificates.list(CertificateQuery(sort="valid_to", limit=1, offset=i))[0].valid_to for i in range(3)]
    assert dates == sorted(dates)


@pytest.mark.skipif(not os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST"), reason="GUI disabled")
def test_autocomplete_identity_and_keyboard():
    import tkinter as tk
    from certificate_analyzer.presentation.gui.widgets.employee_autocomplete import EmployeeAutocomplete
    root = tk.Tk()
    try:
        chosen = []
        employees = [Employee(id=1, full_name="Иванов Иван", department="ИТ"), Employee(id=2, full_name="Иванов Иван", department="Кадры")]
        entry = EmployeeAutocomplete(root, employees=employees, on_select=chosen.append)
        entry.pack()
        root.update()
        entry.set("ив")
        entry.suggest()
        assert len(entry.matches) == 2
        assert "Кадры" in entry.listbox.get(1)
        entry.move()
        entry.move()
        entry.choose()
        assert chosen[0].id == 2
        entry.set("нет совпадений")
        entry.suggest()
        assert entry.popup.state() == "withdrawn"
    finally:
        root.destroy()
