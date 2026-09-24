def run_as_gui():
    import tkinter as tk
    from certificate_analyzer.presentation.gui.main_window import CertificateAnalyzerApp

    root = tk.Tk()
    CertificateAnalyzerApp(root)
    root.mainloop()
