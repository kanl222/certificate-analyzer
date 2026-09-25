"""Run explicitly with CERTIFICATE_ANALYZER_GUI_TEST=1 and a display."""

import os
import sys
import time
from pathlib import Path
import pytest

_tcl_dir = Path(sys.base_prefix) / "tcl"
if (_tcl_dir / "tcl8.6").is_dir():
    os.environ["TCL_LIBRARY"] = (_tcl_dir / "tcl8.6").as_posix()
if (_tcl_dir / "tk8.6").is_dir():
    os.environ["TK_LIBRARY"] = (_tcl_dir / "tk8.6").as_posix()

pytestmark = pytest.mark.skipif(
    os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST") != "1",
    reason="GUI requires an explicitly enabled desktop session",
)


@pytest.fixture(scope="module")
def shared_tk_root():
    from tkinter import Tk
    root = Tk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


@pytest.fixture
def tk_root(shared_tk_root):
    yield shared_tk_root
    for child in shared_tk_root.winfo_children():
        try:
            child.destroy()
        except Exception:
            pass


def test_desktop_database_and_import(
    tmp_path, application, certificate_file, monkeypatch, tk_root
):
    from tkinter import messagebox
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
    root = tk_root
    root.report_callback_exception = lambda *args: errors.append(args)
    config = tmp_path / "gui-settings.json"
    app = CertificateAnalyzerApp(root, application, config_path=config, destroy_root=False)
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
            if root.winfo_exists():
                root.update()
            time.sleep(0.01)


def test_hierarchical_menu(tmp_path, application, monkeypatch, tk_root):
    """Проверяет корректность создания и структуру иерархического меню интерфейса.

    Args:
        tmp_path: Временная директория для тестовой конфигурации.
        application: Экземпляр контейнера сервисов приложения.
        monkeypatch: Фикстура pytest для подмены методов.
        tk_root: Фикстура корневого виджета Tkinter.

    Returns:
        None
    """
    from tkinter import Menu, messagebox
    from certificate_analyzer.presentation.gui.main_window import CertificateAnalyzerApp

    errors = []
    infos = []
    monkeypatch.setattr(
        messagebox, "showinfo", lambda *args, **kwargs: infos.append(args)
    )
    monkeypatch.setattr(
        messagebox, "showerror", lambda *args, **kwargs: errors.append(args)
    )
    monkeypatch.setattr(
        messagebox, "showwarning", lambda *args, **kwargs: errors.append(args)
    )
    monkeypatch.setattr(messagebox, "askyesno", lambda *args, **kwargs: True)

    root = tk_root
    config = tmp_path / "gui-menu-settings.json"
    app = CertificateAnalyzerApp(root, application, config_path=config, destroy_root=False)
    try:
        assert isinstance(app.menubar, Menu)

        top_labels = [
            app.menubar.entrycget(i, "label")
            for i in range(app.menubar.index("end") + 1)
        ]
        assert "Файл" in top_labels
        assert "Правка" in top_labels
        assert "Вид" in top_labels
        assert "Инструменты" in top_labels
        assert "Справка" in top_labels

        app.show_about()
        assert len(infos) == 1
        assert "Хранилище сертификатов" in infos[0][1]

        app.status_var.set("Просроченные")
        app.clear_filters()
        assert app.status_var.get() == "Все статусы"
        assert not errors
    finally:
        app.close()
        deadline = time.monotonic() + 5
        while app.future and time.monotonic() < deadline:
            if root.winfo_exists():
                root.update()
            time.sleep(0.01)


def test_requests_tab(tmp_path, application, monkeypatch, tk_root):
    """Проверяет корректность работы вкладки «Заявки» в главном окне приложения.

    Args:
        tmp_path: Временная директория для тестовой конфигурации.
        application: Экземпляр контейнера сервисов приложения.
        monkeypatch: Фикстура pytest для подмены методов.
        tk_root: Фикстура корневого виджета Tkinter.

    Returns:
        None
    """
    from tkinter import messagebox
    from certificate_analyzer.presentation.gui.main_window import CertificateAnalyzerApp

    errors = []
    monkeypatch.setattr(
        messagebox, "showerror", lambda *args, **kwargs: errors.append(args)
    )
    monkeypatch.setattr(
        messagebox, "showwarning", lambda *args, **kwargs: errors.append(args)
    )
    monkeypatch.setattr(messagebox, "askyesno", lambda *args, **kwargs: True)

    root = tk_root
    config = tmp_path / "gui-requests-settings.json"
    app = CertificateAnalyzerApp(root, application, config_path=config, destroy_root=False)
    try:
        assert hasattr(app, "requests_view")
        assert not app.requests_view.tree.get_children()

        # Создаем сотрудника и тестовую заявку через сервис
        emp = application.employees.get_or_create("Петров Петр Петрович", department="Бухгалтерия")
        req = application.certificate_requests.create_request(
            employee_id=emp.id,
            department="Бухгалтерия",
            needs_signature=True,
            comment="Срочная заявка",
        )
        assert req.request_number is not None

        # Переключаемся на вкладку заявок и обновляем
        app.show_requests_tab()
        app.requests_view.refresh()
        assert len(app.requests_view.tree.get_children()) == 1

        # Проверяем фильтрацию по поисковой строке
        app.requests_view.search_var.set("Петров")
        assert len(app.requests_view.tree.get_children()) == 1

        app.requests_view.search_var.set("Несуществующий")
        assert len(app.requests_view.tree.get_children()) == 0

        app.requests_view.clear_filters()
        assert len(app.requests_view.tree.get_children()) == 1

        # Возвращаемся на вкладку сертификатов
        app.show_certificates_tab()
        assert not errors
    finally:
        app.close()
        deadline = time.monotonic() + 5
        while app.future and time.monotonic() < deadline:
            if root.winfo_exists():
                root.update()
            time.sleep(0.01)


