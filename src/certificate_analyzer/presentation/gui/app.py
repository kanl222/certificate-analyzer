import sys


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

    _enable_dpi_awareness()
    root = tk.Tk()
    CertificateAnalyzerApp(root, application, config_path=config_path)
    root.mainloop()
