import sys
import logging

WINDOWS_APP_ID = "kanl.CertificateAnalyzer"
WINDOW_CLASS = "CertificateAnalyzer"


def _enable_windows_identity() -> None:
    """Separate the GUI from Python's taskbar group before creating windows."""
    if sys.platform != "win32":
        return
    import ctypes
    try:
        set_app_id = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
        set_app_id.argtypes = [ctypes.c_wchar_p]
        set_app_id.restype = ctypes.c_long
        result = set_app_id(WINDOWS_APP_ID)
        if result != 0:
            logging.getLogger(__name__).warning("Не удалось задать идентификатор приложения Windows: %s", result)
    except (AttributeError, OSError):
        logging.getLogger(__name__).warning("Не удалось настроить значок панели задач", exc_info=True)


def _enable_dpi_awareness() -> None:
    """Включает корректное масштабирование интерфейса на Windows с HiDPI."""
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass


def run_as_gui(application, config_path=None):
    import tkinter as tk
    from certificate_analyzer.presentation.gui.main_window import CertificateAnalyzerApp

    if not application.database.read_only:
        from certificate_analyzer.bootstrap import create_application
        from certificate_analyzer.runtime.user_daemon import ensure_writer
        settings = application.settings
        application.close()
        ensure_writer(settings)
        application = create_application(settings=settings, read_only=True)

    _enable_dpi_awareness()
    _enable_windows_identity()
    root = tk.Tk(className=WINDOW_CLASS)
    def report_callback_error(error_type, error, traceback):
        from certificate_analyzer.runtime.ipc import WriterUnavailable, WriteCommandError
        if isinstance(error, (WriterUnavailable, WriteCommandError)):
            from tkinter import messagebox
            messagebox.showerror("Ошибка фонового процесса", str(error), parent=root)
        else:
            tk.Tk.report_callback_exception(root, error_type, error, traceback)
    root.report_callback_exception = report_callback_error
    CertificateAnalyzerApp(root, application, config_path=config_path)
    root.mainloop()
