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
    wizard = ExportArchiveWizard(SimpleNamespace(root=root, _submit=Mock()), records)
    wizard.withdraw()
    try:
        assert not wizard.variables["certificates"]["ABC"].get()
        wizard.toggle_all("certificates", True)
        wizard.move(1)
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
    finally:
        wizard.destroy()
        root.destroy()
