"""Регрессионные проверки удобства основных GUI-сценариев."""

import os
from pathlib import Path
import sys


_tcl_dir = Path(sys.base_prefix) / "tcl"
if (_tcl_dir / "tcl8.6").is_dir():
    os.environ["TCL_LIBRARY"] = (_tcl_dir / "tcl8.6").as_posix()
if (_tcl_dir / "tk8.6").is_dir():
    os.environ["TK_LIBRARY"] = (_tcl_dir / "tk8.6").as_posix()

import tkinter as tk  # noqa: E402
from tkinter import ttk  # noqa: E402

import pytest  # noqa: E402

from certificate_analyzer.domain.enums.certificate_request_status import (  # noqa: E402
    CertificateRequestStatus,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST") != "1",
    reason="GUI requires an explicitly enabled desktop session",
)


def _descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from _descendants(child)


def _fully_visible(widget, window):
    window.update_idletasks()
    assert widget.winfo_ismapped()
    assert widget.winfo_height() >= widget.winfo_reqheight()
    assert widget.winfo_rooty() + widget.winfo_height() <= window.winfo_rooty() + window.winfo_height()


def test_normative_bottom_buttons_visible_at_open_and_resize(tk_root):
    from certificate_analyzer.presentation.gui.views.normative_view import NormativeWindow
    view = NormativeWindow(tk_root)
    try:
        for height in (590, 420):
            view.window.geometry(f"940x{height}")
            view.window.update()
            for button in (view.add_btn, view.copy_btn, view.open_btn):
                _fully_visible(button, view.window)
    finally:
        view._on_close()


def test_main_status_and_paging_visible_at_small_height(application, tk_root):
    from certificate_analyzer.presentation.gui.main_window import CertificateAnalyzerApp
    window = tk.Toplevel(tk_root)
    view = CertificateAnalyzerApp(window, application=application)
    try:
        window.geometry("1100x650")
        window.update()
        _fully_visible(view.message, window)
        _fully_visible(view.certs_tab.previous_button, window)
        _fully_visible(view.certs_tab.next_button, window)
    finally:
        view.close()


def test_edit_menu_tracks_active_tab_and_dispatches_actions(application, tk_root, monkeypatch):
    from unittest.mock import Mock
    from certificate_analyzer.presentation.gui.main_window import CertificateAnalyzerApp
    window = tk.Toplevel(tk_root)
    view = CertificateAnalyzerApp(window, application=application)
    try:
        for tab, expected, forbidden in (
            (view.certs_tab, "Открыть сертификат", "Удалить заявку"),
            (view.requests_tab, "Изменить статус…", "Открыть сертификат"),
            (view.employees_tab, "Изменить сотрудника…", "Удалить физический файл (в корзину)..."),
            (view.mchd_tab, "Открыть XML МЧД", "Открыть сертификат"),
        ):
            view.notebook.select(tab)
            window.update()
            view.menu_bar.update_edit_menu()
            menu = view.menu_bar.edit_menu
            labels = [menu.entrycget(index, "label") for index in range(menu.index("end") + 1) if menu.type(index) == "command"]
            assert expected in labels
            assert forbidden not in labels
        change_status = Mock()
        monkeypatch.setattr(view.requests_view, "show_status_dialog", change_status)
        view.notebook.select(view.requests_tab)
        view.menu_bar.update_edit_menu()
        view.menu_bar.edit_menu.invoke(3)
        change_status.assert_called_once()
        delete_file = Mock()
        monkeypatch.setattr(view, "delete_physical_file", delete_file)
        view.menu_bar._delete_certificate_file(type("Event", (), {"widget": view.requests_view.tree})())
        delete_file.assert_not_called()
    finally:
        view.close()


@pytest.fixture(scope="module")
def shared_tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def tk_root(shared_tk_root):
    yield shared_tk_root
    for child in shared_tk_root.winfo_children():
        child.destroy()


def test_status_dialog_starts_with_current_request_status(application, tk_root):
    from certificate_analyzer.presentation.gui.views.requests_view import RequestsView

    employee = application.employees.get_or_create("Иванов Иван Иванович")
    request = application.certificate_requests.create_request(employee_id=employee.id)
    application.certificate_requests.update_status(
        request.id,
        CertificateRequestStatus.ISSUED,
    )
    view = RequestsView(tk_root, application=application)
    view.pack()
    view.tree.selection_set(str(request.id))

    view.show_status_dialog()

    dialog = next(child for child in _descendants(tk_root) if isinstance(child, tk.Toplevel))
    combo = next(child for child in _descendants(dialog) if isinstance(child, ttk.Combobox))
    assert combo.get() == CertificateRequestStatus.ISSUED.label


def test_link_dialog_offers_certificates_by_readable_fields(
    application,
    certificate_file,
    tk_root,
):
    from certificate_analyzer.presentation.gui.views.requests_view import RequestsView

    certificate = application.certificates.import_files([certificate_file()]).certificates[0]
    employee = application.employees.get_or_create("Иванов Иван Иванович")
    request = application.certificate_requests.create_request(employee_id=employee.id)
    view = RequestsView(tk_root, application=application)
    view.pack()
    view.tree.selection_set(str(request.id))

    view.show_link_dialog()

    dialog = next(child for child in _descendants(tk_root) if isinstance(child, tk.Toplevel))
    picker = next(child for child in _descendants(dialog) if isinstance(child, ttk.Treeview))
    rows = picker.get_children()
    assert len(rows) == 1
    values = picker.item(rows[0], "values")
    assert certificate.subject in values
    assert certificate.original_name in values
    assert certificate.fingerprint_sha256 not in values


def test_empty_certificate_table_has_onboarding_message(application, tk_root):
    from certificate_analyzer.presentation.gui.views.certificates_view import CertificatesView

    view = CertificatesView(tk_root, application=application)
    view.pack()
    view.refresh()

    assert view.empty_label.winfo_manager() == "place"
    assert "Добавьте сертификат" in view.empty_label.cget("text")


def test_certificate_sort_heading_shows_direction(application, tk_root):
    from certificate_analyzer.presentation.gui.views.certificates_view import CertificatesView

    view = CertificatesView(tk_root, application=application)
    view.pack()

    view.sort_by("valid_to")
    assert view.tree.heading("valid_to", "text").endswith("↑")
    view.sort_by("valid_to")
    assert view.tree.heading("valid_to", "text").endswith("↓")


def test_other_main_tables_show_empty_state(application, tk_root):
    from certificate_analyzer.presentation.gui.views.employees_view import EmployeesView
    from certificate_analyzer.presentation.gui.views.mchd_view import MchdView
    from certificate_analyzer.presentation.gui.views.requests_view import RequestsView

    requests = RequestsView(tk_root, application=application)
    employees = EmployeesView(tk_root, application=application)
    mchd = MchdView(tk_root, application=None, mchd_data=[])

    assert requests.empty_label.winfo_manager() == "place"
    assert employees.empty_label.winfo_manager() == "place"
    assert mchd.empty_label.winfo_manager() == "place"


def test_mchd_sort_heading_shows_direction(tk_root):
    from certificate_analyzer.presentation.gui.views.mchd_view import MchdView

    view = MchdView(
        tk_root,
        application=None,
        mchd_data=[
            {"doc_number": "2", "full_name": "Петров", "status": "Действует"},
            {"doc_number": "1", "full_name": "Иванов", "status": "Действует"},
        ],
    )

    view.sort_column("full_name")
    assert view.tree.heading("full_name", "text").endswith("↑")
    view.sort_column("full_name")
    assert view.tree.heading("full_name", "text").endswith("↓")
