"""Exercise the real heading commands on all four desktop tabs."""

import os
from dataclasses import replace

import pytest


@pytest.mark.skipif(
    os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST") != "1", reason="Requires desktop Tk"
)
def test_heading_sorting_and_refresh_on_all_tabs(
    application, certificate_file, mchd_file
):
    import tkinter as tk
    from certificate_analyzer.domain.models.employee import Employee
    from certificate_analyzer.infrastructure.mchd.xml_parser import MchdXmlParser
    from certificate_analyzer.presentation.gui.views.certificates_view import (
        CertificatesView,
    )
    from certificate_analyzer.presentation.gui.views.employees_view import EmployeesView
    from certificate_analyzer.presentation.gui.views.requests_view import RequestsView
    from certificate_analyzer.presentation.gui.views.mchd_view import MchdView

    result = application.certificates.import_files(
        [certificate_file("z.pem", days=30), certificate_file("a.pem", days=365)]
    )
    assert not result.errors
    for name in ("Яков", "Анна"):
        application.employees.save_employee(Employee(full_name=name))
    for number in ("Z-2", "A-1"):
        application.certificate_requests.create_request(request_number=number)
    document = MchdXmlParser().parse(mchd_file())
    for number in ("Z-2", "A-1"):
        application.mchds.save(replace(document, unified_number=number))

    root = tk.Tk()
    root.withdraw()
    try:
        cases = (
            (CertificatesView(root, application), "original_name"),
            (EmployeesView(root, application), "full_name"),
            (RequestsView(root, application), "request_number"),
            (MchdView(root, application), "doc_number"),
        )
        for view, column in cases:
            for heading in view.tree["columns"]:
                assert view.tree.heading(heading, "command"), (
                    type(view).__name__,
                    heading,
                )

            def values():
                return [view.tree.set(row, column) for row in view.tree.get_children()]

            root.tk.call(view.tree.heading(column, "command"))
            assert values() == sorted(values())
            root.tk.call(view.tree.heading(column, "command"))
            assert values() == sorted(values(), reverse=True)
            expected = values()
            view.refresh()
            assert values() == expected
    finally:
        root.destroy()
