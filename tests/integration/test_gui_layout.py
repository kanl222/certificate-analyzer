"""Проверки геометрии, сохранения контекста и ошибок фильтрации в GUI."""

import os
import tkinter as tk
from tkinter import ttk

import pytest

from certificate_analyzer.presentation.gui.main_window import CertificateAnalyzerApp
from certificate_analyzer.presentation.gui.views.employees_view import EmployeeDialog
from certificate_analyzer.presentation.gui.views.settings_view import SettingsDialog
from certificate_analyzer.presentation.gui.views.archive_view import ExportArchiveWizard
from certificate_analyzer.presentation.gui.widgets.responsive_bar import ResponsiveBar
from certificate_analyzer.presentation.gui.widgets.table_state import TableState


pytestmark = pytest.mark.skipif(
    os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST") != "1",
    reason="GUI requires an explicitly enabled desktop session",
)


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def assert_inside(widget, container, *, requested=False):
    """Проверяет обе координаты, размеры и фактическую видимость элемента."""
    assert widget.winfo_ismapped(), str(widget)
    x, y = widget.winfo_rootx(), widget.winfo_rooty()
    assert x >= container.winfo_rootx(), str(widget)
    assert y >= container.winfo_rooty(), str(widget)
    assert x + widget.winfo_width() <= container.winfo_rootx() + container.winfo_width(), str(widget)
    assert y + widget.winfo_height() <= container.winfo_rooty() + container.winfo_height(), str(widget)
    if requested:
        assert widget.winfo_width() >= widget.winfo_reqwidth(), str(widget)
        assert widget.winfo_height() >= widget.winfo_reqheight(), str(widget)


@pytest.fixture
def gui(application, tk_runtime):
    root = tk.Toplevel(tk_runtime)
    root.tk.call("tk", "scaling", 96 / 72)
    app = CertificateAnalyzerApp(root, application=application)
    root.geometry("1000x650")
    root.update()
    yield app
    app.close()


@pytest.fixture(scope="module")
def tk_runtime():
    """Использует один Tcl/Tk на модуль и отдельное окно для каждого сценария."""
    root = tk.Tk()
    root.withdraw()
    root.update()
    yield root
    root.destroy()


@pytest.mark.parametrize("scale", [96 / 72, 120 / 72, 144 / 72])
def test_main_layout_at_supported_sizes_and_scales(application, tk_runtime, scale):
    """Панели переносятся без перекрытий при масштабе Windows 100–150%."""
    root = tk.Toplevel(tk_runtime)
    root.tk.call("tk", "scaling", scale)
    root.update()
    app = CertificateAnalyzerApp(root, application=application)
    try:
        for width, height in ((1000, 650), (1366, 768), (1920, 1080)):
            root.geometry(f"{width}x{height}")
            for tab in (app.certs_tab, app.requests_tab, app.employees_tab, app.mchd_tab):
                app.notebook.select(tab)
                root.update()
                assert_inside(app.message, root)
                assert_inside(app.monitor_status, root, requested=True)
                for bar in (item for item in descendants(tab) if isinstance(item, ResponsiveBar)):
                    items = [widget for widget, _ in bar._items]
                    for item in items:
                        assert_inside(item, bar, requested=True)
                        for control in descendants(item):
                            if isinstance(control, (ttk.Entry, ttk.Combobox)):
                                assert_inside(control, item, requested=True)
                    for index, first in enumerate(items):
                        for second in items[index + 1:]:
                            assert (first.winfo_x() + first.winfo_width() <= second.winfo_x()
                                    or first.winfo_y() + first.winfo_height() <= second.winfo_y()
                                    or second.winfo_y() + second.winfo_height() <= first.winfo_y())
                if tab is app.certs_tab:
                    assert_inside(app.certs_tab.previous_button, root, requested=True)
                    assert_inside(app.certs_tab.next_button, root, requested=True)
                    actions = app.certs_tab.detail_action_buttons
                elif tab is app.mchd_tab:
                    actions = app.mchd_view.detail_action_buttons
                else:
                    actions = ()
                for button in actions:
                    assert_inside(button, root, requested=True)
                tree = next(widget for widget in descendants(tab) if isinstance(widget, ttk.Treeview))
                assert tree.winfo_height() >= 100
    finally:
        app.close()


def test_invalid_dates_keep_current_table_and_explain_recovery(gui):
    view = gui.certs_tab
    view.tree.insert("", "end", iid="existing", values=("Запись до фильтрации",))
    for start, end, expected in (
        ("21.10.2026", "", "ГГГГ-ММ-ДД"),
        ("2026-02-30", "", "ГГГГ-ММ-ДД"),
        ("20261021", "", "ГГГГ-ММ-ДД"),
        ("2026-12-01", "2026-01-01", "Начало периода"),
    ):
        view.date_from_var.set(start)
        view.date_to_var.set(end)
        view.refresh(reset=True)
        gui.root.update()
        assert expected in view.filter_error.cget("text")
        assert view.date_from_entry.instate(["invalid"])
        assert view.tree.exists("existing")
    view.clear_filters()
    gui.root.update()
    assert not view.filter_error.winfo_ismapped()
    assert not view.date_from_entry.instate(["invalid"])
    assert not view.date_to_entry.instate(["invalid"])


def test_selection_actions_and_refresh_keep_employee_and_request(gui, application):
    employee = application.employees.get_or_create("Иванов Иван Иванович")
    request = application.certificate_requests.create_request(employee_id=employee.id)
    for view, row, tab in (
        (gui.employees_view, str(employee.id), gui.employees_tab),
        (gui.requests_view, str(request.id), gui.requests_tab),
    ):
        gui.notebook.select(tab)
        view.refresh()
        gui.root.update()
        assert all(button.instate(["disabled"]) for button in view.selection_buttons)
        view.tree.selection_set(row)
        view.tree.focus(row)
        view.tree.xview_moveto(0.2)
        gui.root.update()
        position = view.tree.xview()[0]
        assert all(button.instate(["!disabled"]) for button in view.selection_buttons)
        view.refresh()
        gui.root.update()
        assert view.tree.selection() == (row,)
        assert view.tree.focus() == row
        assert view.tree.xview()[0] == pytest.approx(position, abs=0.01)
        view.search_var.set("Нет такого сотрудника")
        view.refresh()
        gui.root.update()
        assert not view.tree.selection()
        assert all(button.instate(["disabled"]) for button in view.selection_buttons)


def test_certificate_refresh_preserves_selection_and_details(gui, application, certificate_file):
    certificate = application.certificates.import_files([certificate_file()]).certificates[0]
    view = gui.certs_tab
    view.refresh()
    view.tree.selection_set(certificate.fingerprint_sha256)
    view.tree.focus(certificate.fingerprint_sha256)
    view.refresh()
    gui.root.update()
    assert view.tree.selection() == (certificate.fingerprint_sha256,)
    assert view.details.fields["Subject"].cget("text") == certificate.subject
    assert view.details.fields["SHA-256"].cget("text") == certificate.fingerprint_sha256


def test_mchd_refresh_preserves_selection_across_recreated_records(gui):
    view = gui.mchd_view
    record = dict(file_name="example.xml", doc_number="МЧД-1", full_name="Иванов Иван",
                  inn="123", status="Действует", authority_codes=["SIGN"])
    view.mchd_data = [record]
    view.apply_filters()
    row = view.tree.get_children()[0]
    view.tree.selection_set(row)
    view.tree.focus(row)
    view.mchd_data = [dict(record)]
    view.apply_filters()
    assert view.tree.selection() == (row,)
    assert view.tree.focus() == row
    assert view.mchd_detail_fields["doc_number"].cget("text") == "МЧД-1"


def test_table_refresh_keeps_scroll_and_does_not_select_replacement(gui):
    tree = gui.requests_view.tree
    gui.notebook.select(gui.requests_tab)
    gui.root.update()
    for index in range(100):
        tree.insert("", "end", iid=f"row-{index}", values=(f"Заявка {index}",))
    tree.selection_set(("row-40", "row-41"))
    tree.focus("row-40")
    tree.yview_moveto(0.4)
    tree.xview_moveto(0.2)
    gui.root.update()
    state = TableState.capture(tree)
    tree.delete(*tree.get_children())
    for index in range(100):
        tree.insert("", "end", iid=f"row-{index}", values=(f"Заявка {index}",))
    state.restore(tree)
    assert tree.selection() == ("row-40", "row-41")
    assert tree.yview()[0] == pytest.approx(state.vertical, abs=0.01)
    assert tree.xview()[0] == pytest.approx(state.horizontal, abs=0.01)
    tree.delete("row-40", "row-41")
    state.restore(tree)
    assert tree.selection() == ()
    assert tree.focus() == ""


@pytest.mark.parametrize("scale", [96 / 72, 144 / 72])
def test_dialog_buttons_and_fields_fit_their_windows(application, tk_runtime, scale):
    root = tk.Toplevel(tk_runtime)
    root.tk.call("tk", "scaling", scale)
    app = CertificateAnalyzerApp(root, application=application)
    dialogs = []
    try:
        employee = application.employees.get_or_create("Иванов Иван")
        request = application.certificate_requests.create_request(employee_id=employee.id)
        app.requests_view.refresh()
        app.requests_view.tree.selection_set(str(request.id))
        dialogs.append(EmployeeDialog(root))
        dialogs.append(SettingsDialog(root, application))
        app.requests_view.show_create_dialog()
        app.requests_view.show_status_dialog()
        dialogs.extend(child for child in descendants(root)
                       if isinstance(child, tk.Toplevel) and child not in dialogs)
        for dialog in dialogs:
            root.update()
            for widget in descendants(dialog):
                if isinstance(widget, (ttk.Button, ttk.Entry, ttk.Combobox)) and widget.winfo_ismapped():
                    assert_inside(widget, dialog)
            dialog.destroy()
        wizard = ExportArchiveWizard(app, {})
        wizard.geometry("600x420")
        root.update()
        for button in (child for child in descendants(wizard) if isinstance(child, ttk.Button)):
            assert_inside(button, wizard, requested=True)
        wizard.step = 4
        wizard.render()
        root.update()
        for button in (child for child in descendants(wizard) if isinstance(child, ttk.Button)):
            assert_inside(button, wizard, requested=True)
        entries = [child for child in descendants(wizard) if isinstance(child, ttk.Entry)]
        entries[-1].focus_force()
        root.update()
        assert_inside(entries[-1], wizard, requested=True)
        wizard.destroy()
    finally:
        for dialog in dialogs:
            if dialog.winfo_exists():
                dialog.destroy()
        app.close()
