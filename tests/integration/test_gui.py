"""Run explicitly with CERTIFICATE_ANALYZER_GUI_TEST=1 and a display."""

import os
import time
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST") != "1",
    reason="GUI requires an explicitly enabled desktop session",
)


def test_desktop_database_and_import(
    tmp_path, application, certificate_file, monkeypatch
):
    from tkinter import Tk, messagebox
    from certificate_analyzer.presentation.gui.main_window import CertificateAnalyzerApp
    from certificate_analyzer.infrastructure.config.config_loader import load_settings

    errors = []
    monkeypatch.setattr(
        messagebox, "showerror", lambda *args, **kwargs: errors.append(args)
    )
    monkeypatch.setattr(
        messagebox, "showwarning", lambda *args, **kwargs: errors.append(args)
    )
    monkeypatch.setattr(messagebox, "askyesno", lambda *args, **kwargs: True)
    root = Tk()
    root.withdraw()
    root.report_callback_exception = lambda *args: errors.append(args)
    config = tmp_path / "gui-settings.json"
    app = CertificateAnalyzerApp(root, application, config_path=config)
    try:
        assert not app.tree.get_children()
        source = certificate_file()
        app._submit(
            lambda: application.certificates.import_files([source]),
            app._import_finished,
        )
        deadline = time.monotonic() + 10
        while app.future and time.monotonic() < deadline:
            root.update()
            time.sleep(0.01)
        assert app.future is None
        assert len(app.tree.get_children()) == 1
        source.unlink()
        app.refresh()
        assert len(app.tree.get_children()) == 1
        app.search_var.set("несуществующий")
        app._apply_search()
        assert not app.tree.get_children()
        app.search_var.set("ИВАНОВ")
        app._apply_search()
        assert len(app.tree.get_children()) == 1
        fingerprint = app.tree.get_children()[0]
        app.tree.selection_set(fingerprint)
        app.show_details()
        assert app.details.fields["SHA-256"].cget("text") == fingerprint
        app.status_var.set("Просроченные")
        app.refresh(reset=True)
        assert not app.tree.get_children()
        app.clear_filters()
        app.sort_by("valid_to")
        app.show_settings()

        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)

        save = next(
            w
            for w in descendants(root)
            if w.winfo_class() == "TButton" and w.cget("text") == "Сохранить"
        )
        save.invoke()
        assert load_settings(config).storage_folder == str(
            application.certificates.storage.folder
        )
        assert not errors
    finally:
        app.close()
        deadline = time.monotonic() + 10
        while app.future and time.monotonic() < deadline:
            root.update()
            time.sleep(0.01)
