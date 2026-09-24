"""Run explicitly with CERTIFICATE_ANALYZER_GUI_TEST=1 and a working display."""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST") != "1",
    reason="GUI requires an explicitly enabled desktop session",
)


def test_desktop_workflows(tmp_path, monkeypatch, certificate_file, mchd_file):
    monkeypatch.setenv("CERTIFICATE_ANALYZER_HOME", str(tmp_path / "settings"))
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp_path / "matplotlib"))
    from tkinter import Tk, messagebox

    from certificate_analyzer.infrastructure.config.config_loader import save_settings
    from certificate_analyzer.infrastructure.config.settings import Settings
    from certificate_analyzer.infrastructure.mchd.xml_parser import MCHDParser
    from certificate_analyzer.presentation.gui.main_window import CertificateAnalyzerApp
    from certificate_analyzer.presentation.gui.views.mchd_view import (
        AuthoritiesViewWindow,
        MCHDTableWindow,
    )

    certificate_file()
    document = mchd_file()
    save_settings(
        Settings(
            folders={"📁 Сотрудники": str(tmp_path), "📁 Руководство": str(tmp_path)},
            mchd_folder=str(tmp_path),
            export_folder=str(tmp_path / "reports"),
        )
    )
    errors = []
    monkeypatch.setattr(messagebox, "showerror", lambda *a, **kw: errors.append(a))
    for name in ("showinfo", "showwarning"):
        monkeypatch.setattr(messagebox, name, lambda *a, **kw: None)
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **kw: False)
    monkeypatch.setattr(messagebox, "askyesnocancel", lambda *a, **kw: None)
    root = Tk()
    root.withdraw()
    root.report_callback_exception = lambda *args: errors.append(args)
    app = None
    try:
        app = CertificateAnalyzerApp(root)
        # Do not emit OS notifications from the test.
        app.notification_manager.stop_monitoring()
        root.update()
        assert len(app.cert_data_cache) == 1
        app.search_var.set("Иванов")
        app.clear_search()
        for chart_type in (
            "pie",
            "bar",
            "line",
            "area",
            "doughnut",
            "scatter",
            "bubble",
            "stacked_bar",
        ):
            app.chart_type = chart_type
            app.update_stats()
        app.show_folder_settings()

        def buttons(widget):
            for child in widget.winfo_children():
                if (
                    child.winfo_class() == "TButton"
                    and child.cget("text") == "Сохранить"
                ):
                    yield child
                yield from buttons(child)

        next(iter(buttons(app.open_windows["folder_settings"]))).invoke()
        app.show_notification_settings()
        app.show_notification_history()
        app.show_normative()
        app.show_date_filter()
        data = MCHDParser.parse_file(document)
        MCHDTableWindow(root, [data])
        AuthoritiesViewWindow(
            root,
            {
                "person_name": "Тест",
                "total_files": 2,
                "unique_codes_count": 1,
                "codes": ["A"],
                "file_names": ["a", "b"],
            },
        )
        root.update()
        assert not errors, errors
    finally:
        if app:
            app.close()
        else:
            root.destroy()
