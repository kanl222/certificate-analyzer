def run_as_gui(application, config_path=None):
    import tkinter as tk
    from certificate_analyzer.presentation.gui.main_window import CertificateAnalyzerApp

    root = tk.Tk()
    CertificateAnalyzerApp(root, application, config_path=config_path)
    root.mainloop()
