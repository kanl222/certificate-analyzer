import os
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from certificate_analyzer.presentation.gui.views.archive_view import ExportArchiveWizard


@pytest.mark.skipif(os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST") != "1", reason="Requires desktop Tk")
def test_wizard_selection_navigation_and_related_employees():
    import sys
    from pathlib import Path
    import tkinter as tk

    tcl = Path(sys.base_prefix) / "tcl"
    if (tcl / "tcl8.6").is_dir():
        os.environ["TCL_LIBRARY"] = str(tcl / "tcl8.6")
        os.environ["TK_LIBRARY"] = str(tcl / "tk8.6")
    root = tk.Tk()
    root.withdraw()
    records = {"certificates": [{"id": "ABC", "label": "Certificate", "employee_id": 1}], "employees": [{"id": 1, "label": "Linked"}, {"id": 2, "label": "Other"}], "mchds": [{"id": "M-1", "label": "Power of attorney"}]}
    records["certificates"][0].update(subject="Иванов Иван", original_name="ivanov.cer", valid_from="2026-01-01", valid_to="2027-01-01", issuer="УЦ", serial_number="123")
    records["employees"][0].update(full_name="Иванов Иван", department="ИТ")
    records["requests"] = [{"id": 10, "request_number": "REQ-10", "employee_id": 2, "certificate_fingerprint": "ABC"}]
    wizard = ExportArchiveWizard(SimpleNamespace(root=root, _submit=Mock()), records)
    wizard.withdraw()
    try:
        assert not wizard.variables["certificates"]["ABC"].get()
        assert wizard.table.get_children() == ("ABC",)
        assert wizard.table.set("ABC", "subject") == "Иванов Иван"
        assert wizard.table.set("ABC", "original_name") == "ivanov.cer"
        assert wizard.table.set("ABC", "valid_to") == "01.01.2027"
        assert wizard.table.set("ABC", "issuer") == "УЦ"
        assert "selected" not in wizard.table["columns"]
        assert wizard.table.item("ABC", "image")[0] == str(wizard.checkbox_images["empty"])
        wizard.toggle_row("certificates", "ABC")
        assert wizard.table.item("ABC", "image")[0] == str(wizard.checkbox_images["checked"])
        wizard.toggle_all("certificates", True)
        wizard.move(1)
        assert wizard.table.set("1", "full_name") == "Иванов Иван"
        assert wizard.table.item("1", "image")[0] == str(wizard.checkbox_images["linked"])
        assert wizard.variables["employees"]["1"].get()
        assert not wizard.variables["employees"]["2"].get()
        wizard.toggle_all("employees", True)
        assert wizard.variables["employees"]["2"].get()
        wizard.toggle_all("employees", False)
        assert wizard.variables["employees"]["1"].get()
        assert not wizard.variables["employees"]["2"].get()
        wizard.move(-1)
        assert wizard.variables["certificates"]["ABC"].get()
        wizard.move(1)
        wizard.move(1)
        wizard.toggle_all("mchds", True)
        wizard.move(1)
        assert wizard.step == 3
        assert wizard.variables["mchds"]["M-1"].get()
        assert "requests" in wizard.variables
        assert wizard.table.get_children() == ("10",)
        wizard.toggle_row("requests", "10")
        assert wizard.variables["employees"]["2"].get()
        wizard.toggle_all("certificates", False)
        assert wizard.variables["certificates"]["ABC"].get()
        wizard.toggle_all("employees", False)
        assert wizard.variables["employees"]["2"].get()
        assert wizard.title() == "Экспорт хранилища сертификатов"
        wizard.move(1)
        assert wizard.step == 4
    finally:
        wizard.destroy()
        root.destroy()


def test_old_worker_is_refreshed_before_showing_export(monkeypatch):
    from certificate_analyzer.presentation.gui.main_window import CertificateAnalyzerApp
    from certificate_analyzer.runtime import user_daemon
    restart = Mock()
    monkeypatch.setattr(user_daemon, "restart_writer", restart)
    old = {"certificates": [{"id": "ABC", "label": "Old worker"}], "employees": [], "mchds": []}
    current = {"certificates": [{"id": "ABC", "subject": "Иванов Иван", "original_name": "ivanov.cer", "valid_from": "2026-01-01", "issuer": "УЦ", "serial_number": "123"}], "employees": [], "mchds": [], "requests": []}
    archive = Mock()
    archive.export_choices.side_effect = [old, current]
    view = SimpleNamespace(app=SimpleNamespace(archive=archive, settings=object()))
    assert CertificateAnalyzerApp._export_choices(view) == current
    restart.assert_called_once_with(view.app.settings)
    assert archive.export_choices.call_count == 2


def test_current_worker_is_not_restarted(monkeypatch):
    from certificate_analyzer.presentation.gui.main_window import CertificateAnalyzerApp
    from certificate_analyzer.runtime import user_daemon
    restart = Mock()
    monkeypatch.setattr(user_daemon, "restart_writer", restart)
    records = {"certificates": [], "employees": [], "mchds": [], "requests": []}
    view = SimpleNamespace(app=SimpleNamespace(archive=SimpleNamespace(export_choices=lambda: records)))
    assert CertificateAnalyzerApp._export_choices(view) == records
    restart.assert_not_called()
